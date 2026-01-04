"""Calendar event creation helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.crypto import CryptoProvider
from app.models import (
    CalendarCandidate,
    CalendarEventCreated,
    Email,
    GoogleOAuthToken,
    User,
)
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
    ical_uid = payload.get("ical_uid") or None

    description = overrides.get("description") or _build_description(email)
    event_body = {
        "summary": title,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": timezone},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": timezone},
        "description": description,
    }
    if ical_uid:
        event_body["iCalUID"] = ical_uid
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


def accept_invite(
    db: Session,
    settings: Settings,
    crypto: CryptoProvider,
    user_id: int,
    candidate_id: int,
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
    existing_record = db.execute(
        select(CalendarEventCreated).where(
            CalendarEventCreated.calendar_candidate_id == candidate.id,
            CalendarEventCreated.user_id == user_id,
        )
    ).scalar_one_or_none()
    payload = candidate.payload or {}
    candidate_type = str(payload.get("type") or "").upper()
    if candidate_type != "INVITE":
        raise ValueError("Calendar candidate is not an invite")

    if client is None:
        token_row = db.execute(
            select(GoogleOAuthToken).where(GoogleOAuthToken.user_id == user_id)
        ).scalar_one_or_none()
        if not token_row:
            raise ValueError("Missing OAuth token row for user")
        creds = build_credentials(db, token_row, settings, crypto).credentials
        client = CalendarClient(credentials=creds)

    if existing_record:
        _accept_existing_event(db, client, user_id, existing_record.event_id, payload)
        existing_record.status = "ACCEPTED"
        candidate.status = "INVITE_ACCEPTED"
        db.commit()
        return existing_record

    existing_event = _find_existing_invite_event(client, payload)
    if existing_event:
        patched = _accept_invite_event(db, client, user_id, existing_event)
        record = CalendarEventCreated(
            user_id=user_id,
            calendar_candidate_id=candidate.id,
            event_id=patched.get("id"),
            payload=patched,
            status="ACCEPTED",
            updated_at=datetime.now(UTC),
        )
        candidate.status = "INVITE_ACCEPTED"
        db.add(record)
        db.commit()
        return record

    event = create_event(
        db,
        settings,
        crypto,
        user_id,
        candidate_id,
        overrides=None,
        client=client,
    )
    event.status = "ACCEPTED"
    if event.candidate:
        event.candidate.status = "INVITE_ACCEPTED"
    db.commit()
    return event


def _build_description(email: Email) -> str:
    email_link = (
        f"https://mail.google.com/mail/u/0/#inbox/{email.gmail_message_id}"
        if email.gmail_message_id
        else ""
    )
    parts = ["Created from Clearview Email."]
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


def _find_existing_invite_event(client: CalendarClient, payload: dict) -> dict | None:
    ical_uid = payload.get("ical_uid")
    if not ical_uid:
        return None
    start_dt = _parse_datetime(payload.get("start"))
    end_dt = _parse_datetime(payload.get("end"))
    if not start_dt or not end_dt:
        return None
    time_min = (start_dt - timedelta(days=1)).isoformat()
    time_max = (end_dt + timedelta(days=1)).isoformat()
    response = client.list_events(
        calendar_id="primary",
        ical_uid=ical_uid,
        time_min=time_min,
        time_max=time_max,
    )
    items = response.get("items") if isinstance(response, dict) else None
    if not items:
        return None
    return items[0]


def _accept_existing_event(
    db: Session,
    client: CalendarClient,
    user_id: int,
    event_id: str | None,
    payload: dict,
) -> None:
    if not event_id:
        return
    event = _find_existing_invite_event(client, payload)
    if not event:
        event = client.get_event(calendar_id="primary", event_id=event_id)
    _accept_invite_event(db, client, user_id, event)


def _accept_invite_event(
    db: Session,
    client: CalendarClient,
    user_id: int,
    event: dict,
) -> dict:
    event_id = event.get("id")
    if not event_id:
        raise ValueError("Calendar event id missing for invite acceptance")
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    user_email = user.email if user else None
    attendees = list(event.get("attendees") or [])
    updated_attendees = []
    matched = False
    for attendee in attendees:
        if not isinstance(attendee, dict):
            continue
        entry = dict(attendee)
        if entry.get("self") or (
            user_email and entry.get("email", "").lower() == user_email.lower()
        ):
            entry["responseStatus"] = "accepted"
            matched = True
        updated_attendees.append(entry)
    if user_email and not matched:
        updated_attendees.append({"email": user_email, "responseStatus": "accepted"})
    patch_body = {"status": "confirmed"}
    if updated_attendees:
        patch_body["attendees"] = updated_attendees
    return client.patch_event(
        calendar_id="primary",
        event_id=event_id,
        event_body=patch_body,
        send_updates="all",
    )


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
