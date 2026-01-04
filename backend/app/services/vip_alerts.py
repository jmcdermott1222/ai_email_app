"""VIP alert detection and creation."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, Email, UserPreferences
from app.services.preferences import default_preferences


def create_vip_alert_if_needed(
    db: Session,
    user_id: int,
    email: Email,
) -> Alert | None:
    preferences = db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    ).scalar_one_or_none()
    pref_data = preferences.preferences if preferences else default_preferences()
    if not pref_data.get("vip_alerts_enabled", True):
        return None

    reasons = _match_reasons(email, pref_data)
    if not reasons:
        return None

    existing = db.execute(
        select(Alert).where(Alert.user_id == user_id, Alert.email_id == email.id)
    ).scalar_one_or_none()
    if existing:
        return existing

    alert = Alert(
        user_id=user_id,
        email_id=email.id,
        reason=", ".join(reasons),
    )
    db.add(alert)
    return alert


def _match_reasons(email: Email, pref_data: dict) -> list[str]:
    reasons: list[str] = []
    sender = (email.from_email or "").lower()
    sender_domain = sender.split("@")[-1] if "@" in sender else ""
    vip_senders = {item.lower() for item in (pref_data.get("vip_senders") or [])}
    vip_domains = {item.lower() for item in (pref_data.get("vip_domains") or [])}
    vip_keywords = [item.lower() for item in (pref_data.get("vip_keywords") or [])]

    if sender and sender in vip_senders:
        reasons.append("sender_match")
    if sender_domain and sender_domain in vip_domains:
        reasons.append("domain_match")

    if vip_keywords:
        combined_text = f"{email.subject or ''} {email.clean_body_text or ''}".lower()
        if any(keyword in combined_text for keyword in vip_keywords):
            reasons.append("keyword_match")

    return reasons
