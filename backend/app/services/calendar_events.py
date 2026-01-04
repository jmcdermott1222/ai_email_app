"""Calendar event creation helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.crypto import CryptoProvider
from app.models import CalendarCandidate, CalendarEventCreated, Email, GoogleOAuthToken
from app.services.calendar_client import CalendarClient
from app.services.google_credentials import build_credentials


def create_event(
    db: Session,
    settings: Settings,
    crypto: CryptoProvider,
    user_id: int,
    candidate_id: int,
    overrides: dict | None = None,
    client: CalendarClient | None = None,
) -> CalendarEventCreated:
    candidate = db.execute(
        select(CalendarCandidate).where(
            CalendarCandidate.id == candidate_id,
            CalendarCandidate.user_id == user_id,
        )
    ).scalar_one_or_none()
    if not candidate:
        raise ValueError("Calendar candidate not found")

    email = db.execute(
        select(Email).where(Email.id == candidate.email_id, Email.user_id == user_id)
    ).scalar_one_or_none()
    if not email:
        raise ValueError("Email not found")

    payload = candidate.payload or {}
    overrides = overrides or {}

    title = overrides.get("title") or payload.get("title") or email.subject or "Meeting"
    start_dt = _parse_datetime(overrides.get("start") or payload.get("start"))
    end_dt = _parse_datetime(overrides.get("end") or payload.get("end"))
    if not start_dt or not end_dt:
        raise ValueError("Missing start/end time")
    if end_dt <= start_dt:
        raise ValueError("End time must be after start time")

    timezone = overrides.get("timezone") or "UTC"
    location = overrides.get("location") or payload.get("location")
    attendees = overrides.get("attendees") or payload.get("attendees") or []
    attendees = [email for email in attendees if isinstance(email, str) and email]
    attendees = sorted({addr.strip() for addr in attendees if addr.strip()})

    description = overrides.get("description") or _build_description(email)
    event_body = {
        "summary": title,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": timezone},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": timezone},
        "description": description,
    }
    if location:
        event_body["location"] = location
    if attendees:
        event_body["attendees"] = [{"email": addr} for addr in attendees]

    if client is None:
        token_row = db.execute(
            select(GoogleOAuthToken).where(GoogleOAuthToken.user_id == user_id)
        ).scalar_one_or_none()
        if not token_row:
            raise ValueError("Missing OAuth token row for user")
        creds = build_credentials(db, token_row, settings, crypto).credentials
        client = CalendarClient(credentials=creds)

    response = client.create_event(
        calendar_id="primary", event_body=event_body, send_updates="all"
    )
    event = CalendarEventCreated(
        user_id=user_id,
        calendar_candidate_id=candidate.id,
        event_id=response.get("id"),
        payload=response,
        status="CREATED",
        updated_at=datetime.now(UTC),
    )
    candidate.status = "EVENT_CREATED"
    db.add(event)
    db.commit()
    return event


def _build_description(email: Email) -> str:
    email_link = (
        f"https://mail.google.com/mail/u/0/#inbox/{email.gmail_message_id}"
        if email.gmail_message_id
        else ""
    )
    parts = ["Created from AI Email Copilot."]
    if email.subject:
        parts.append(f"Email subject: {email.subject}")
    if email_link:
        parts.append(f"Email link: {email_link}")
    return "\n".join(parts)


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    if isinstance(value, datetime):
        return _ensure_aware(value)
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    return _ensure_aware(datetime.fromisoformat(normalized))


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
