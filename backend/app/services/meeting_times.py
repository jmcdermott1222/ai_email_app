"""Meeting time suggestion logic using Calendar free/busy."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.crypto import CryptoProvider
from app.models import CalendarCandidate, Email, GoogleOAuthToken, UserPreferences
from app.services.calendar_client import CalendarClient
from app.services.google_credentials import build_credentials
from app.services.preferences import default_preferences

BUFFER_MINUTES = 10
SLOT_INCREMENT_MINUTES = 15
DEFAULT_WINDOW_DAYS = 7
DAY_TO_INDEX = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


@dataclass(frozen=True)
class MeetingTimeSuggestion:
    start: datetime
    end: datetime
    score: float | None = None


def suggest_times(
    db: Session,
    settings: Settings,
    crypto: CryptoProvider,
    user_id: int,
    candidate_id: int,
    duration_min: int | None = None,
    client: CalendarClient | None = None,
) -> list[MeetingTimeSuggestion]:
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

    preferences = db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    ).scalar_one_or_none()
    pref_data = preferences.preferences if preferences else default_preferences()
    working_hours = pref_data.get("working_hours") or default_preferences().get(
        "working_hours"
    )

    payload = dict(candidate.payload or {})
    payload_type = str(payload.get("type") or "").upper()
    proposed_start = _parse_rfc3339(payload.get("start"))
    proposed_end = _parse_rfc3339(payload.get("end"))

    duration_min = _resolve_duration_min(
        duration_min, proposed_start, proposed_end, pref_data
    )
    now = datetime.now(UTC)
    window_start, window_end, proposed_slot = _resolve_window(
        payload_type, proposed_start, proposed_end, now, working_hours
    )

    if client is None:
        token_row = db.execute(
            select(GoogleOAuthToken).where(GoogleOAuthToken.user_id == user_id)
        ).scalar_one_or_none()
        if not token_row:
            raise ValueError("Missing OAuth token row for user")
        creds = build_credentials(db, token_row, settings, crypto).credentials
        client = CalendarClient(credentials=creds)

    freebusy = client.freebusy_query(
        time_min=window_start.isoformat(),
        time_max=window_end.isoformat(),
        calendar_ids=["primary"],
    )
    busy_intervals = _parse_busy_intervals(freebusy)

    suggestions = _generate_suggestions(
        window_start,
        window_end,
        busy_intervals,
        working_hours,
        duration_min,
    )

    if proposed_slot and _slot_is_available(
        proposed_slot, busy_intervals, working_hours
    ):
        suggestions = _prepend_unique(proposed_slot, suggestions)

    suggestions = suggestions[:5]
    payload["suggested_times"] = [
        {"start": slot.start.isoformat(), "end": slot.end.isoformat()}
        for slot in suggestions
    ]
    payload["suggested_duration_min"] = duration_min
    payload["suggested_generated_at"] = datetime.now(UTC).isoformat()
    candidate.payload = payload
    db.commit()
    return suggestions


def _resolve_duration_min(
    duration_min: int | None,
    proposed_start: datetime | None,
    proposed_end: datetime | None,
    pref_data: dict,
) -> int:
    if duration_min:
        return int(duration_min)
    if proposed_start and proposed_end:
        delta = proposed_end - proposed_start
        minutes = int(delta.total_seconds() / 60)
        if minutes > 0:
            return minutes
    return int(pref_data.get("meeting_default_duration_min", 30))


def _resolve_window(
    payload_type: str,
    proposed_start: datetime | None,
    proposed_end: datetime | None,
    now: datetime,
    working_hours: dict,
) -> tuple[datetime, datetime, MeetingTimeSuggestion | None]:
    if payload_type == "DATE_RANGE" and proposed_start and proposed_end:
        window_start = _ensure_aware(proposed_start)
        window_end = _ensure_aware(proposed_end)
        if window_end > window_start:
            return window_start, window_end, None

    proposed_slot = None
    if proposed_start and proposed_end:
        proposed_slot = MeetingTimeSuggestion(
            start=_ensure_aware(proposed_start),
            end=_ensure_aware(proposed_end),
        )
        day_start = _combine_date_time(
            proposed_slot.start.date(),
            _parse_time(working_hours.get("start_time", "09:00")),
            proposed_slot.start.tzinfo or UTC,
        )
        window_start = max(day_start, now)
        window_end = window_start + timedelta(days=DEFAULT_WINDOW_DAYS)
        return window_start, window_end, proposed_slot

    window_start = now
    window_end = window_start + timedelta(days=DEFAULT_WINDOW_DAYS)
    return window_start, window_end, None


def _parse_busy_intervals(freebusy: dict) -> list[tuple[datetime, datetime]]:
    busy = freebusy.get("calendars", {}).get("primary", {}).get("busy", []) or []
    intervals = []
    for item in busy:
        start = _parse_rfc3339(item.get("start"))
        end = _parse_rfc3339(item.get("end"))
        if not start or not end:
            continue
        intervals.append((start, end))
    return intervals


def _generate_suggestions(
    window_start: datetime,
    window_end: datetime,
    busy_intervals: list[tuple[datetime, datetime]],
    working_hours: dict,
    duration_min: int,
) -> list[MeetingTimeSuggestion]:
    suggestions: list[MeetingTimeSuggestion] = []
    tzinfo = window_start.tzinfo or UTC
    working_days = _working_day_indices(working_hours.get("days", []))
    start_time = _parse_time(working_hours.get("start_time", "09:00"))
    end_time = _parse_time(working_hours.get("end_time", "17:00"))
    lunch_enabled = bool(working_hours.get("lunch_enabled", False))
    lunch_start = _parse_time(working_hours.get("lunch_start", "12:00"))
    lunch_end = _parse_time(working_hours.get("lunch_end", "13:00"))
    buffer_delta = timedelta(minutes=BUFFER_MINUTES)
    slot_delta = timedelta(minutes=duration_min)
    step_delta = timedelta(minutes=SLOT_INCREMENT_MINUTES)

    for day in _date_range(window_start.date(), window_end.date()):
        if day.weekday() not in working_days:
            continue
        day_start = _combine_date_time(day, start_time, tzinfo)
        day_end = _combine_date_time(day, end_time, tzinfo)
        day_start, day_end = _clip_range(day_start, day_end, window_start, window_end)
        if day_end <= day_start:
            continue

        day_busy = _busy_for_day(day_start, day_end, busy_intervals, buffer_delta)
        if lunch_enabled and lunch_start < lunch_end:
            lunch_interval = (
                _combine_date_time(day, lunch_start, tzinfo),
                _combine_date_time(day, lunch_end, tzinfo),
            )
            day_busy.extend(_expand_interval(lunch_interval, buffer_delta))
        day_busy = _merge_intervals(day_busy)

        for free_start, free_end in _free_intervals(day_start, day_end, day_busy):
            slot_start = free_start
            while slot_start + slot_delta <= free_end:
                suggestions.append(
                    MeetingTimeSuggestion(start=slot_start, end=slot_start + slot_delta)
                )
                slot_start += step_delta
    return suggestions


def _slot_is_available(
    slot: MeetingTimeSuggestion,
    busy_intervals: list[tuple[datetime, datetime]],
    working_hours: dict,
) -> bool:
    working_days = _working_day_indices(working_hours.get("days", []))
    if slot.start.weekday() not in working_days:
        return False
    start_time = _parse_time(working_hours.get("start_time", "09:00"))
    end_time = _parse_time(working_hours.get("end_time", "17:00"))
    lunch_enabled = bool(working_hours.get("lunch_enabled", False))
    lunch_start = _parse_time(working_hours.get("lunch_start", "12:00"))
    lunch_end = _parse_time(working_hours.get("lunch_end", "13:00"))
    tzinfo = slot.start.tzinfo or UTC
    day_start = _combine_date_time(slot.start.date(), start_time, tzinfo)
    day_end = _combine_date_time(slot.start.date(), end_time, tzinfo)
    if slot.start < day_start or slot.end > day_end:
        return False
    if lunch_enabled and lunch_start < lunch_end:
        lunch_interval = (
            _combine_date_time(slot.start.date(), lunch_start, tzinfo),
            _combine_date_time(slot.start.date(), lunch_end, tzinfo),
        )
        if _overlaps(slot.start, slot.end, lunch_interval[0], lunch_interval[1]):
            return False
    for busy_start, busy_end in busy_intervals:
        if _overlaps(slot.start, slot.end, busy_start, busy_end):
            return False
    return True


def _busy_for_day(
    day_start: datetime,
    day_end: datetime,
    busy_intervals: list[tuple[datetime, datetime]],
    buffer_delta: timedelta,
) -> list[tuple[datetime, datetime]]:
    day_busy = []
    for busy_start, busy_end in busy_intervals:
        expanded = _expand_interval((busy_start, busy_end), buffer_delta)
        for start, end in expanded:
            if end <= day_start or start >= day_end:
                continue
            day_busy.append(
                (
                    max(start, day_start),
                    min(end, day_end),
                )
            )
    return day_busy


def _expand_interval(
    interval: tuple[datetime, datetime], buffer_delta: timedelta
) -> list[tuple[datetime, datetime]]:
    start, end = interval
    return [(start - buffer_delta, end + buffer_delta)]


def _merge_intervals(
    intervals: Iterable[tuple[datetime, datetime]]
) -> list[tuple[datetime, datetime]]:
    sorted_intervals = sorted(intervals, key=lambda item: item[0])
    merged: list[tuple[datetime, datetime]] = []
    for start, end in sorted_intervals:
        if not merged:
            merged.append((start, end))
            continue
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _free_intervals(
    day_start: datetime,
    day_end: datetime,
    busy_intervals: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    free: list[tuple[datetime, datetime]] = []
    cursor = day_start
    for busy_start, busy_end in busy_intervals:
        if busy_end <= cursor:
            continue
        if busy_start > cursor:
            free.append((cursor, min(busy_start, day_end)))
        cursor = max(cursor, busy_end)
        if cursor >= day_end:
            break
    if cursor < day_end:
        free.append((cursor, day_end))
    return free


def _prepend_unique(
    slot: MeetingTimeSuggestion, suggestions: list[MeetingTimeSuggestion]
) -> list[MeetingTimeSuggestion]:
    remaining = [
        item for item in suggestions if item.start != slot.start or item.end != slot.end
    ]
    return [slot, *remaining]


def _overlaps(
    start: datetime, end: datetime, other_start: datetime, other_end: datetime
) -> bool:
    return start < other_end and end > other_start


def _working_day_indices(days: list[str]) -> set[int]:
    if not days:
        return set(DAY_TO_INDEX.values())
    return {DAY_TO_INDEX[day.lower()] for day in days if day.lower() in DAY_TO_INDEX}


def _date_range(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _parse_time(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(int(hour), int(minute))


def _parse_rfc3339(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    return _ensure_aware(parsed)


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _combine_date_time(day: date, value: time, tzinfo) -> datetime:
    return datetime.combine(day, value, tzinfo=tzinfo)


def _clip_range(
    day_start: datetime,
    day_end: datetime,
    window_start: datetime,
    window_end: datetime,
) -> tuple[datetime, datetime]:
    return max(day_start, window_start), min(day_end, window_end)
