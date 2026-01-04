"""Automation action execution engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.crypto import CryptoProvider
from app.models import (
    AuditLog,
    Email,
    EmailTriage,
    GoogleOAuthToken,
    UserGmailLabel,
    UserPreferences,
)
from app.services.gmail_client import GmailClient
from app.services.google_credentials import build_credentials

SNOOZE_LABEL_NAME = "Copilot/Snoozed"
ACTION_LABELS = {
    "HIGH": "Copilot/Action",
    "MEDIUM": "Copilot/FYI",
    "LOW": "Copilot/Newsletter",
    "IGNORE": "Copilot/Ignore",
}
SYSTEM_LABELS = {"INBOX"}


@dataclass(frozen=True)
class ActionResult:
    applied: list[str]
    skipped: list[str]


@dataclass(frozen=True)
class AutomationResult:
    suggested: list[str]
    applied: list[str]
    skipped: list[str]


def execute_actions(
    db: Session,
    settings: Settings,
    crypto: CryptoProvider,
    user_id: int,
    email_id: int,
    actions: list[str],
    client: GmailClient | None = None,
) -> ActionResult:
    email = db.execute(
        select(Email).where(Email.id == email_id, Email.user_id == user_id)
    ).scalar_one_or_none()
    if not email:
        raise ValueError("Email not found")

    if client is None:
        token_row = db.execute(
            select(GoogleOAuthToken).where(GoogleOAuthToken.user_id == user_id)
        ).scalar_one_or_none()
        if not token_row:
            raise ValueError("Missing OAuth token row for user")
        creds = build_credentials(db, token_row, settings, crypto).credentials
        client = GmailClient(credentials=creds)

    label_map = _label_map(db, user_id)
    applied: list[str] = []
    skipped: list[str] = []

    for action in actions:
        try:
            if action.startswith("ADD_LABEL:"):
                label_name = action.split(":", 1)[1]
                label_id = _resolve_label_id(label_map, label_name)
                if not label_id:
                    skipped.append(action)
                    continue
                client.modify_message_labels(
                    email.gmail_message_id,
                    add_label_ids=[label_id],
                    remove_label_ids=[],
                )
                applied.append(action)
            elif action.startswith("REMOVE_LABEL:"):
                label_name = action.split(":", 1)[1]
                label_id = _resolve_label_id(label_map, label_name)
                if not label_id:
                    skipped.append(action)
                    continue
                client.modify_message_labels(
                    email.gmail_message_id,
                    add_label_ids=[],
                    remove_label_ids=[label_id],
                )
                applied.append(action)
            elif action == "ARCHIVE":
                client.modify_message_labels(
                    email.gmail_message_id, add_label_ids=[], remove_label_ids=["INBOX"]
                )
                applied.append(action)
            elif action == "MARK_READ":
                client.modify_message_labels(
                    email.gmail_message_id,
                    add_label_ids=[],
                    remove_label_ids=["UNREAD"],
                )
                if email.label_ids:
                    email.label_ids = [
                        label for label in email.label_ids if label != "UNREAD"
                    ]
                applied.append(action)
            elif action == "TRASH":
                client.trash_message(email.gmail_message_id)
                applied.append(action)
            elif action.startswith("SNOOZE_UNTIL:"):
                snooze_until = action.split(":", 1)[1]
                _apply_snooze(db, email, client, label_map, snooze_until)
                applied.append(action)
            else:
                skipped.append(action)
        finally:
            _log_action(db, user_id, email_id, action)

    db.commit()
    return ActionResult(applied=applied, skipped=skipped)


def run_automation_for_email(
    db: Session,
    settings: Settings,
    crypto: CryptoProvider,
    user_id: int,
    email_id: int,
) -> AutomationResult:
    email = db.execute(
        select(Email).where(Email.id == email_id, Email.user_id == user_id)
    ).scalar_one_or_none()
    if not email:
        raise ValueError("Email not found")

    triage = db.execute(
        select(EmailTriage).where(EmailTriage.email_id == email.id)
    ).scalar_one_or_none()
    if not triage:
        return AutomationResult(suggested=[], applied=[], skipped=[])

    preferences = db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    ).scalar_one_or_none()
    automation_level = (
        (preferences.preferences or {}).get("automation_level", "SUGGEST_ONLY")
        if preferences
        else "SUGGEST_ONLY"
    )

    suggested = _suggest_actions(triage)
    if automation_level == "SUGGEST_ONLY":
        return AutomationResult(suggested=suggested, applied=[], skipped=[])

    allowed = _filter_actions_by_level(suggested, automation_level)
    result = execute_actions(db, settings, crypto, user_id, email_id, allowed)
    return AutomationResult(
        suggested=suggested, applied=result.applied, skipped=result.skipped
    )


def _label_map(db: Session, user_id: int) -> dict[str, str]:
    result = db.execute(
        select(UserGmailLabel).where(UserGmailLabel.user_id == user_id)
    ).scalars()
    return {row.label_name: row.label_id for row in result}


def _resolve_label_id(label_map: dict[str, str], label_name: str) -> str | None:
    if label_name in label_map:
        return label_map[label_name]
    if label_name in SYSTEM_LABELS:
        return label_name
    return None


def _suggest_actions(triage: EmailTriage) -> list[str]:
    actions: list[str] = []
    label_name = ACTION_LABELS.get(triage.importance_label or "")
    if label_name:
        actions.append(f"ADD_LABEL:{label_name}")
    if triage.importance_label in {"LOW", "IGNORE"}:
        actions.append("ARCHIVE")
    if triage.importance_label == "IGNORE" and not triage.needs_response:
        actions.append("TRASH")
    return actions


def _filter_actions_by_level(actions: list[str], automation_level: str) -> list[str]:
    if automation_level == "AUTO_LABEL":
        return [action for action in actions if action.startswith("ADD_LABEL:")]
    if automation_level == "AUTO_ARCHIVE":
        return [
            action
            for action in actions
            if action.startswith("ADD_LABEL:") or action == "ARCHIVE"
        ]
    if automation_level == "AUTO_TRASH":
        return actions
    return []


def _apply_snooze(
    db: Session,
    email: Email,
    client: GmailClient,
    label_map: dict[str, str],
    snooze_until: str,
) -> None:
    snooze_label_id = label_map.get(SNOOZE_LABEL_NAME)
    add_labels = [snooze_label_id] if snooze_label_id else []
    client.modify_message_labels(
        email.gmail_message_id,
        add_label_ids=add_labels,
        remove_label_ids=["INBOX"],
    )
    email.snooze_until_ts = _parse_rfc3339(snooze_until)
    email.is_snoozed = True


def _parse_rfc3339(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def snooze_sweep(
    db: Session, settings: Settings, crypto: CryptoProvider
) -> dict[str, int]:
    now = datetime.now(UTC)
    due_emails = (
        db.execute(
            select(Email).where(
                Email.is_snoozed.is_(True),
                Email.snooze_until_ts.is_not(None),
                Email.snooze_until_ts <= now,
            )
        )
        .scalars()
        .all()
    )
    processed = 0
    for email in due_emails:
        token_row = db.execute(
            select(GoogleOAuthToken).where(GoogleOAuthToken.user_id == email.user_id)
        ).scalar_one_or_none()
        if not token_row:
            continue
        creds = build_credentials(db, token_row, settings, crypto).credentials
        client = GmailClient(credentials=creds)
        label_map = _label_map(db, email.user_id)
        snooze_label_id = label_map.get(SNOOZE_LABEL_NAME)
        remove_labels = [snooze_label_id] if snooze_label_id else []
        client.modify_message_labels(
            email.gmail_message_id,
            add_label_ids=["INBOX"],
            remove_label_ids=remove_labels,
        )
        email.is_snoozed = False
        email.snooze_until_ts = None
        _log_action(db, email.user_id, email.id, "SNOOZE_SWEEP")
        processed += 1

    db.commit()
    return {"processed": processed}


def _log_action(db: Session, user_id: int, email_id: int, action: str) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            target_type="email",
            target_id=str(email_id),
        )
    )
