"""Calendar candidate extraction from emails."""

from __future__ import annotations

import base64
import logging
import re
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import dateparser
from dateparser.search import search_dates
from icalendar import Calendar
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.crypto import CryptoProvider
from app.models import CalendarCandidate, Email, GoogleOAuthToken, UserPreferences
from app.services.attachments import download_attachment_bytes
from app.services.gmail_client import GmailClient
from app.services.google_credentials import build_credentials
from app.services.llm_client import LLMClient
from app.services.llm_schemas import (
    CALENDAR_CANDIDATE_SCHEMA,
    CALENDAR_CANDIDATE_SCHEMA_VERSION,
)
from app.services.preferences import default_preferences

PROMPT_VERSION = "v1"
DEFAULT_WINDOW_DAYS = 7
TIME_PATTERN = re.compile(r"\b(\d{1,2}:\d{2}|\d{1,2}\s?(am|pm))\b", re.IGNORECASE)
MEETING_INTENT_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bmeet(ing)?\b",
        r"\bcall\b",
        r"\bchat\b",
        r"\btalk\b",
        r"\bsync\b",
        r"\bcatch up\b",
        r"\bschedule\b",
        r"\bcalendar\b",
        r"\binvite\b",
        r"\bappointment\b",
        r"\bavailability\b",
        r"\bavailable\b",
        r"\bare you free\b",
        r"\bfree to (meet|call|chat|talk)\b",
    ]
]
logger = logging.getLogger(__name__)


def detect_ics_invites(
    db: Session,
    settings: Settings,
    crypto: CryptoProvider,
    user_id: int,
    email_id: int,
    include_inline: bool = True,
) -> list[CalendarCandidate]:
    """Extract calendar invites from ICS attachments or inline calendar parts."""
    email = db.execute(
        select(Email).where(Email.id == email_id, Email.user_id == user_id)
    ).scalar_one_or_none()
    if not email:
        raise ValueError("Email not found")

    duration_min = _meeting_duration(db, user_id)
    candidates: list[CalendarCandidate] = []

    attachments = [
        attachment
        for attachment in email.attachments
        if _is_calendar_attachment(attachment.filename, attachment.mime_type)
        and attachment.gmail_attachment_id
    ]

    for attachment in attachments:
        content = download_attachment_bytes(
            db,
            user_id,
            email.gmail_message_id,
            attachment.gmail_attachment_id,
            settings,
            crypto,
        )
        candidates.extend(
            _store_invites_from_ics(
                db,
                user_id,
                email_id,
                content,
                duration_min,
                source="ICS_ATTACHMENT",
            )
        )

    if include_inline:
        inline_payloads = _fetch_inline_calendar_parts(
            db, settings, crypto, user_id, email.gmail_message_id
        )
        for content in inline_payloads:
            candidates.extend(
                _store_invites_from_ics(
                    db,
                    user_id,
                    email_id,
                    content,
                    duration_min,
                    source="INLINE",
                )
            )

    return candidates


def extract_in_text_candidates(
    db: Session,
    settings: Settings,
    user_id: int,
    email_id: int,
    now: datetime | None = None,
) -> list[CalendarCandidate]:
    """Extract proposed times from email text."""
    email = db.execute(
        select(Email).where(Email.id == email_id, Email.user_id == user_id)
    ).scalar_one_or_none()
    if not email:
        raise ValueError("Email not found")

    text = "\n".join(
        [segment for segment in [email.subject, email.clean_body_text] if segment]
    ).strip()
    if not text:
        return []

    base = now or datetime.now(UTC)
    settings_map = {
        "PREFER_DATES_FROM": "future",
        "RETURN_AS_TIMEZONE_AWARE": True,
        "TIMEZONE": "UTC",
        "TO_TIMEZONE": "UTC",
        "RELATIVE_BASE": base,
    }
    parsed = search_dates(text, settings=settings_map) or []
    meeting_intent = _has_meeting_intent(text)

    deterministic = len(parsed) == 1 and _contains_explicit_time(parsed[0][0])
    if deterministic:
        duration_min = _meeting_duration(db, user_id)
        match_text, match_dt = parsed[0]
        candidate = _build_candidate_payload(
            candidate_type="PROPOSED_TIME",
            title=email.subject,
            start=_ensure_datetime(match_dt),
            end=_ensure_datetime(match_dt) + timedelta(minutes=duration_min),
            attendees=_build_attendees(email),
            location=None,
            confidence=0.7,
            source="TEXT",
        )
        return _store_candidates(db, user_id, email_id, [candidate])

    if meeting_intent:
        working_hours = _working_hours(db, user_id)
        candidate_dt = _select_meeting_date(parsed, base)
        if candidate_dt:
            start_dt, end_dt = _meeting_window_for_date(
                candidate_dt.date(), working_hours
            )
            candidate = _build_candidate_payload(
                candidate_type="DATE_RANGE",
                title=email.subject,
                start=start_dt,
                end=end_dt,
                attendees=_build_attendees(email),
                location=None,
                confidence=0.6,
                source="TEXT_HEURISTIC",
            )
            return _store_candidates(db, user_id, email_id, [candidate])

        if not parsed:
            start_dt = base
            end_dt = base + timedelta(days=DEFAULT_WINDOW_DAYS)
            candidate = _build_candidate_payload(
                candidate_type="DATE_RANGE",
                title=email.subject,
                start=start_dt,
                end=end_dt,
                attendees=_build_attendees(email),
                location=None,
                confidence=0.4,
                source="TEXT_HEURISTIC",
            )
            return _store_candidates(db, user_id, email_id, [candidate])

    try:
        return _extract_with_llm(db, settings, email, user_id, email_id, text)
    except Exception as exc:  # LLM failures should not block invite detection.
        logger.warning(
            "Calendar LLM extraction failed",
            extra={"user_id": user_id, "email_id": email_id, "error": str(exc)},
        )
        return []


def generate_calendar_candidates(
    db: Session,
    settings: Settings,
    crypto: CryptoProvider,
    user_id: int,
    email_id: int,
) -> list[CalendarCandidate]:
    """Regenerate all calendar candidates for an email."""
    _clear_candidates(db, user_id, email_id)
    invites = detect_ics_invites(db, settings, crypto, user_id, email_id)
    proposed = extract_in_text_candidates(db, settings, user_id, email_id)
    return invites + proposed


def list_calendar_candidates(
    db: Session, user_id: int, email_id: int
) -> list[CalendarCandidate]:
    return (
        db.execute(
            select(CalendarCandidate)
            .where(
                CalendarCandidate.user_id == user_id,
                CalendarCandidate.email_id == email_id,
            )
            .order_by(CalendarCandidate.created_at.desc())
        )
        .scalars()
        .all()
    )


def _clear_candidates(db: Session, user_id: int, email_id: int) -> None:
    db.execute(
        delete(CalendarCandidate).where(
            CalendarCandidate.user_id == user_id,
            CalendarCandidate.email_id == email_id,
        )
    )
    db.commit()


def _meeting_duration(db: Session, user_id: int) -> int:
    preferences = db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    ).scalar_one_or_none()
    pref_data = preferences.preferences if preferences else default_preferences()
    return int(pref_data.get("meeting_default_duration_min", 30))


def _working_hours(db: Session, user_id: int) -> dict:
    preferences = db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    ).scalar_one_or_none()
    pref_data = preferences.preferences if preferences else default_preferences()
    working_hours = pref_data.get("working_hours") or default_preferences().get(
        "working_hours"
    )
    return working_hours


def _is_calendar_attachment(filename: str | None, mime_type: str | None) -> bool:
    if filename and filename.lower().endswith(".ics"):
        return True
    if mime_type and mime_type.lower() == "text/calendar":
        return True
    return False


def _fetch_inline_calendar_parts(
    db: Session,
    settings: Settings,
    crypto: CryptoProvider,
    user_id: int,
    gmail_message_id: str,
) -> list[bytes]:
    token_row = db.execute(
        select(GoogleOAuthToken).where(GoogleOAuthToken.user_id == user_id)
    ).scalar_one_or_none()
    if not token_row:
        return []
    creds = build_credentials(db, token_row, settings, crypto).credentials
    client = GmailClient(credentials=creds)
    message = client.get_message(gmail_message_id, format="full")
    payload = message.get("payload", {}) or {}
    parts = list(_walk_parts(payload))
    contents = []
    for part in parts:
        if part.get("mimeType") != "text/calendar":
            continue
        body = part.get("body", {}) or {}
        data = body.get("data")
        if not data:
            continue
        padding = "=" * (-len(data) % 4)
        contents.append(base64.urlsafe_b64decode(data + padding))
    return contents


def _walk_parts(payload: dict[str, Any]):
    yield payload
    for part in payload.get("parts", []) or []:
        yield from _walk_parts(part)


def _store_invites_from_ics(
    db: Session,
    user_id: int,
    email_id: int,
    content: bytes,
    duration_min: int,
    source: str,
) -> list[CalendarCandidate]:
    candidates_payloads = []
    calendar = Calendar.from_ical(content)
    for component in calendar.walk("VEVENT"):
        dtstart = component.get("dtstart")
        if not dtstart:
            continue
        start = _coerce_datetime(dtstart.dt)
        dtend = component.get("dtend")
        if dtend:
            end = _coerce_datetime(dtend.dt)
        else:
            duration = component.get("duration")
            if duration:
                end = start + duration.dt
            else:
                end = start + timedelta(minutes=duration_min)
        title = _string_or_none(component.get("summary"))
        location = _string_or_none(component.get("location"))
        attendees = _parse_attendees(component.get("attendee"))
        ical_uid = _string_or_none(component.get("uid"))
        candidates_payloads.append(
            _build_candidate_payload(
                candidate_type="INVITE",
                title=title,
                start=start,
                end=end,
                attendees=attendees,
                location=location,
                confidence=1.0,
                source=source,
                ical_uid=ical_uid,
            )
        )

    return _store_candidates(db, user_id, email_id, candidates_payloads)


def _extract_with_llm(
    db: Session,
    settings: Settings,
    email: Email,
    user_id: int,
    email_id: int,
    text: str,
) -> list[CalendarCandidate]:
    llm = LLMClient(settings)
    prompt = _build_llm_prompt(email, text)
    result = llm.call_structured(
        prompt=prompt,
        json_schema=CALENDAR_CANDIDATE_SCHEMA,
        model=settings.openai_model,
        temperature=0.2,
    )

    candidates_payloads = []
    for candidate in result.get("candidates", []):
        payload = _build_candidate_payload(
            candidate_type=candidate.get("type"),
            title=candidate.get("title"),
            start=_parse_dt(candidate.get("start")),
            end=_parse_dt(candidate.get("end")),
            attendees=candidate.get("attendees") or [],
            location=candidate.get("location"),
            confidence=_clamp_confidence(candidate.get("confidence")),
            source="LLM",
        )
        candidates_payloads.append(payload)

    return _store_candidates(
        db,
        user_id,
        email_id,
        candidates_payloads,
        model_id=settings.openai_model,
        prompt_version=PROMPT_VERSION,
        schema_version=CALENDAR_CANDIDATE_SCHEMA_VERSION,
    )


def _store_candidates(
    db: Session,
    user_id: int,
    email_id: int,
    payloads: list[dict[str, Any]],
    model_id: str | None = None,
    prompt_version: str | None = None,
    schema_version: str | None = None,
) -> list[CalendarCandidate]:
    if not payloads:
        return []
    existing = (
        db.execute(
            select(CalendarCandidate).where(
                CalendarCandidate.user_id == user_id,
                CalendarCandidate.email_id == email_id,
            )
        )
        .scalars()
        .all()
    )
    existing_keys = {_candidate_key(row.payload or {}) for row in existing}
    seen: set[tuple] = set()
    rows = []
    for payload in payloads:
        key = _candidate_key(payload)
        if key in existing_keys or key in seen:
            continue
        seen.add(key)
        rows.append(
            CalendarCandidate(
                user_id=user_id,
                email_id=email_id,
                payload=payload,
                status="PROPOSED",
                model_id=model_id,
                prompt_version=prompt_version,
                schema_version=schema_version,
            )
        )
    db.add_all(rows)
    db.commit()
    return rows


def _build_llm_prompt(email: Email, text: str) -> str:
    return (
        "Extract proposed meeting times from the email. "
        "Return candidates with RFC3339 start/end in UTC if timezone is missing. "
        "If multiple options exist, include them all.\n\n"
        f"Subject: {email.subject or ''}\n"
        f"From: {email.from_email or ''}\n"
        f"Body:\n{text}\n"
    )


def _build_candidate_payload(
    candidate_type: str | None,
    title: str | None,
    start: datetime,
    end: datetime,
    attendees: list[str] | None,
    location: str | None,
    confidence: float,
    source: str,
    ical_uid: str | None = None,
) -> dict[str, Any]:
    return {
        "type": candidate_type or "PROPOSED_TIME",
        "title": title,
        "start": start.astimezone(UTC).isoformat(),
        "end": end.astimezone(UTC).isoformat(),
        "attendees": attendees or [],
        "location": location,
        "confidence": confidence,
        "source": source,
        "ical_uid": ical_uid,
    }


def _parse_dt(value: str | None) -> datetime:
    if not value:
        raise ValueError("Missing datetime")
    parsed = dateparser.parse(value)
    if not parsed:
        raise ValueError(f"Unable to parse datetime: {value}")
    return _ensure_datetime(parsed)


def _ensure_datetime(value: datetime | date) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
    return datetime.combine(value, time.min, tzinfo=UTC)


def _coerce_datetime(value: datetime | date) -> datetime:
    return _ensure_datetime(value)


def _contains_explicit_time(match_text: str) -> bool:
    return bool(TIME_PATTERN.search(match_text))


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _parse_attendees(value: Any) -> list[str]:
    if not value:
        return []
    attendees = value if isinstance(value, list) else [value]
    emails = []
    for attendee in attendees:
        text = str(attendee)
        if text.lower().startswith("mailto:"):
            text = text[7:]
        if text:
            emails.append(text)
    return emails


def _build_attendees(email: Email) -> list[str]:
    attendees = []
    if email.from_email:
        attendees.append(email.from_email)
    attendees.extend(email.to_emails or [])
    attendees.extend(email.cc_emails or [])
    return sorted({item for item in attendees if item})


def _clamp_confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, number))


def _has_meeting_intent(text: str) -> bool:
    if not text:
        return False
    return any(pattern.search(text) for pattern in MEETING_INTENT_PATTERNS)


def _select_meeting_date(
    parsed: list[tuple[str, datetime]], base: datetime
) -> datetime | None:
    if not parsed:
        return None
    candidates = []
    for match_text, match_dt in parsed:
        if _contains_explicit_time(match_text):
            continue
        candidates.append(_ensure_datetime(match_dt))
    if not candidates:
        return None
    future_candidates = [item for item in candidates if item >= base]
    if future_candidates:
        return min(future_candidates)
    return min(candidates)


def _meeting_window_for_date(
    day: date, working_hours: dict
) -> tuple[datetime, datetime]:
    start_time = _parse_time_value(working_hours.get("start_time"), time(9, 0))
    end_time = _parse_time_value(working_hours.get("end_time"), time(17, 0))
    if end_time <= start_time:
        end_time = time(17, 0)
    start_dt = datetime.combine(day, start_time, tzinfo=UTC)
    end_dt = datetime.combine(day, end_time, tzinfo=UTC)
    return start_dt, end_dt


def _parse_time_value(value: str | None, fallback: time) -> time:
    if not value:
        return fallback
    try:
        hours, minutes = value.split(":")
        return time(int(hours), int(minutes))
    except (ValueError, TypeError):
        return fallback


def _candidate_key(payload: dict[str, Any]) -> tuple:
    candidate_type = str(payload.get("type") or "").strip().lower()
    start = _normalize_text(payload.get("start"))
    end = _normalize_text(payload.get("end"))
    title = _normalize_text(payload.get("title"))
    location = _normalize_text(payload.get("location"))
    ical_uid = _normalize_text(payload.get("ical_uid"))
    attendees = payload.get("attendees") or []
    normalized_attendees = tuple(
        sorted(
            {
                _normalize_text(attendee)
                for attendee in attendees
                if isinstance(attendee, str) and attendee.strip()
            }
        )
    )
    return (candidate_type, start, end, title, location, ical_uid, normalized_attendees)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()
