"""Email triage service."""

from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Email, EmailTriage, UserPreferences
from app.services.llm_client import LLMClient
from app.services.llm_schemas import (
    EMAIL_TRIAGE_RESULT_SCHEMA,
    EMAIL_TRIAGE_SCHEMA_VERSION,
)

PROMPT_VERSION = "v1"


def triage_email(
    db: Session, settings: Settings, user_id: int, email_id: int
) -> EmailTriage:
    email = db.execute(
        select(Email).where(Email.id == email_id, Email.user_id == user_id)
    ).scalar_one_or_none()
    if not email:
        raise ValueError("Email not found")

    preferences = db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    ).scalar_one_or_none()
    pref_data = preferences.preferences if preferences else {}
    blocked_senders = set(pref_data.get("blocked_senders", []))
    blocked_domains = set(pref_data.get("blocked_domains", []))
    vip_senders = set(pref_data.get("vip_senders", []))

    sender = (email.from_email or "").lower()
    sender_domain = sender.split("@")[-1] if "@" in sender else ""

    if sender in blocked_senders or sender_domain in blocked_domains:
        return _store_triage(
            db,
            email,
            {
                "importance_label": "IGNORE",
                "needs_response": False,
                "summary_bullets": ["Sender is blocked."],
                "why_important": "Sender is on your block list.",
            },
            settings.openai_model,
        )

    prompt = _build_prompt(email)
    llm = LLMClient(settings)
    result = llm.call_structured(
        prompt=prompt,
        json_schema=EMAIL_TRIAGE_RESULT_SCHEMA,
        model=settings.openai_model,
        temperature=0.2,
    )

    if sender in vip_senders and result.get("importance_label") in {"LOW", "MEDIUM"}:
        result["importance_label"] = "HIGH"
        result["why_important"] = "VIP sender."

    return _store_triage(db, email, result, settings.openai_model)


def _build_prompt(email: Email) -> str:
    attachments_summary = []
    for attachment in email.attachments:
        if attachment.extracted_text:
            text_hash = hashlib.sha256(
                attachment.extracted_text.encode("utf-8")
            ).hexdigest()
            attachments_summary.append(
                f"- {attachment.filename or 'attachment'} ({attachment.mime_type}), "
                f"text_hash={text_hash}, text_len={len(attachment.extracted_text)}"
            )

    attachments_text = "\n".join(attachments_summary) if attachments_summary else "None"
    return (
        "You are an email assistant. Classify importance, determine if a response "
        "is needed, and provide short summary bullets and why it matters.\n\n"
        f"Subject: {email.subject or ''}\n"
        f"From: {email.from_email or ''}\n"
        f"Snippet: {email.snippet or ''}\n"
        f"Body:\n{email.clean_body_text or ''}\n"
        f"Attachments:\n{attachments_text}\n"
    )


def _store_triage(
    db: Session,
    email: Email,
    result: dict,
    model_id: str | None,
) -> EmailTriage:
    triage = db.execute(
        select(EmailTriage).where(EmailTriage.email_id == email.id)
    ).scalar_one_or_none()
    summary_bullets = result.get("summary_bullets", [])
    summary = "\n".join(f"- {bullet}" for bullet in summary_bullets)
    reasoning = {
        "summary_bullets": summary_bullets,
        "why_important": result.get("why_important"),
    }

    if not triage:
        triage = EmailTriage(
            user_id=email.user_id,
            email_id=email.id,
        )
        db.add(triage)

    triage.importance_label = result.get("importance_label")
    triage.needs_response = result.get("needs_response", False)
    triage.summary = summary
    triage.reasoning = reasoning
    triage.model_id = model_id
    triage.prompt_version = PROMPT_VERSION
    triage.schema_version = EMAIL_TRIAGE_SCHEMA_VERSION
    db.commit()
    return triage
