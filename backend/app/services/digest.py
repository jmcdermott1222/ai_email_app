"""Daily digest generation service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Alert, Digest, Email
from app.services.triage import triage_email


@dataclass(frozen=True)
class DigestSection:
    name: str
    title: str


SECTIONS = [
    DigestSection(name="needs_reply", title="Needs reply"),
    DigestSection(name="important_fyi", title="Important FYI"),
    DigestSection(name="newsletters", title="Newsletters"),
    DigestSection(name="everything_else", title="Everything else"),
]


def generate_daily_digest(
    db: Session,
    settings: Settings,
    user_id: int,
    since_ts: datetime,
    max_triage: int = 25,
    now: datetime | None = None,
) -> Digest:
    if since_ts.tzinfo is None:
        since_ts = since_ts.replace(tzinfo=UTC)
    now = now or datetime.now(UTC)
    digest_date = now.date()

    emails = (
        db.execute(
            select(Email)
            .where(Email.user_id == user_id, Email.internal_date_ts >= since_ts)
            .order_by(Email.internal_date_ts.desc().nullslast())
        )
        .scalars()
        .all()
    )

    alerts = (
        db.execute(
            select(Alert)
            .where(Alert.user_id == user_id, Alert.created_at >= since_ts)
            .order_by(Alert.created_at.desc())
        )
        .scalars()
        .all()
    )
    vip_senders = sorted(
        {
            alert.email.from_email
            for alert in alerts
            if alert.email and alert.email.from_email
        }
    )

    triaged = 0
    sections: dict[str, list[dict[str, Any]]] = {
        section.name: [] for section in SECTIONS
    }

    for email in emails:
        triage = email.triage
        if triage is None and triaged < max_triage:
            try:
                triage = triage_email(db, settings, user_id, email.id)
            except Exception:
                triage = None
            finally:
                triaged += 1

        entry = _digest_entry(email, triage)
        if triage and triage.needs_response:
            sections["needs_reply"].append(entry)
        elif triage and triage.importance_label in {"HIGH", "MEDIUM"}:
            sections["important_fyi"].append(entry)
        elif triage and triage.importance_label == "LOW":
            sections["newsletters"].append(entry)
        else:
            sections["everything_else"].append(entry)

    content = {
        "generated_at": now.isoformat(),
        "since_ts": since_ts.isoformat(),
        "triaged_count": triaged,
        "vip_count": len(alerts),
        "vip_senders": vip_senders,
        "counts": {name: len(items) for name, items in sections.items()},
        "sections": sections,
    }

    digest = _upsert_digest(db, user_id, digest_date, content, now)
    return digest


def _upsert_digest(
    db: Session,
    user_id: int,
    digest_date: datetime.date,
    content: dict[str, Any],
    now: datetime,
) -> Digest:
    dialect = db.bind.dialect.name if db.bind else "postgresql"
    values = {
        "user_id": user_id,
        "digest_date": digest_date,
        "content_json": content,
        "updated_at": now,
    }
    if dialect == "sqlite":
        insert_stmt = sqlite_insert(Digest).values(**values)
    else:
        insert_stmt = pg_insert(Digest).values(**values)
    db.execute(
        insert_stmt.on_conflict_do_update(
            index_elements=["user_id", "digest_date"],
            set_={
                "content_json": insert_stmt.excluded.content_json,
                "updated_at": now,
            },
        )
    )
    db.commit()
    digest = (
        db.execute(
            select(Digest).where(
                Digest.user_id == user_id, Digest.digest_date == digest_date
            )
        )
        .scalars()
        .one()
    )
    return digest


def _digest_entry(email: Email, triage) -> dict[str, Any]:
    why_important = None
    summary_bullets = []
    importance_label = None
    needs_response = None
    if triage:
        importance_label = triage.importance_label
        needs_response = triage.needs_response
        if triage.reasoning:
            why_important = triage.reasoning.get("why_important")
            summary_bullets = triage.reasoning.get("summary_bullets", [])
    return {
        "id": email.id,
        "subject": email.subject,
        "from_email": email.from_email,
        "snippet": email.snippet,
        "internal_date_ts": (
            email.internal_date_ts.isoformat() if email.internal_date_ts else None
        ),
        "importance_label": importance_label,
        "needs_response": needs_response,
        "why_important": why_important,
        "summary_bullets": summary_bullets,
    }


def default_since_ts(latest_digest: Digest | None) -> datetime:
    if latest_digest and latest_digest.created_at:
        return latest_digest.created_at.astimezone(UTC)
    return datetime.now(UTC) - timedelta(days=1)
