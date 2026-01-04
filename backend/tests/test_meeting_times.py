"""Tests for meeting time suggestions."""

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.crypto import LocalDevCrypto
from app.db import Base
from app.models import CalendarCandidate, Email, User, UserPreferences
from app.services.meeting_times import suggest_times


class FakeCalendarClient:
    def __init__(self, busy):
        self._busy = busy

    def freebusy_query(self, time_min, time_max, calendar_ids=None):
        return {"calendars": {"primary": {"busy": self._busy}}}


def test_suggest_times_respects_busy_and_lunch():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    settings = Settings()
    crypto = LocalDevCrypto("BB0iMhzIaIMZeMACaGkNykzlCaM3Ndoth7-vBeQiJ4U=")

    with SessionLocal() as session:
        user = User(email="user@example.com", google_sub="sub-1")
        session.add(user)
        session.flush()
        email = Email(user_id=user.id, gmail_message_id="msg-1")
        session.add(email)
        session.flush()
        session.add(
            UserPreferences(
                user_id=user.id,
                preferences={
                    "working_hours": {
                        "days": ["mon"],
                        "start_time": "09:00",
                        "end_time": "12:00",
                        "lunch_enabled": True,
                        "lunch_start": "10:30",
                        "lunch_end": "11:00",
                    },
                    "meeting_default_duration_min": 30,
                },
            )
        )
        candidate = CalendarCandidate(
            user_id=user.id,
            email_id=email.id,
            payload={
                "type": "PROPOSED_TIME",
                "start": "2099-01-05T10:00:00+00:00",
                "end": "2099-01-05T10:30:00+00:00",
            },
            status="PROPOSED",
        )
        session.add(candidate)
        session.commit()

        busy = [
            {"start": "2099-01-05T09:00:00+00:00", "end": "2099-01-05T10:30:00+00:00"}
        ]
        client = FakeCalendarClient(busy)
        suggestions = suggest_times(
            session,
            settings,
            crypto,
            user.id,
            candidate.id,
            duration_min=30,
            client=client,
        )

        assert suggestions
        assert all(
            slot.start >= datetime(2099, 1, 5, 11, 10, tzinfo=UTC)
            for slot in suggestions
        )
        assert all(slot.start < slot.end for slot in suggestions)
        stored = session.get(CalendarCandidate, candidate.id)
        payload = stored.payload or {}
        assert payload.get("suggested_times")
