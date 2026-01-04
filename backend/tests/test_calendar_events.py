"""Tests for calendar event creation."""

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.crypto import LocalDevCrypto
from app.db import Base
from app.models import CalendarCandidate, CalendarEventCreated, Email, User
from app.services.calendar_events import create_event


class FakeCalendarClient:
    def __init__(self):
        self.calls = []

    def create_event(self, calendar_id, event_body, send_updates="all"):
        self.calls.append(
            {
                "calendar_id": calendar_id,
                "event_body": event_body,
                "send_updates": send_updates,
            }
        )
        return {
            "id": "evt-123",
            "htmlLink": "https://calendar.google.com/event?eid=evt-123",
        }


def test_create_event_uses_overrides_and_stores_record():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    settings = Settings()
    crypto = LocalDevCrypto("BB0iMhzIaIMZeMACaGkNykzlCaM3Ndoth7-vBeQiJ4U=")
    client = FakeCalendarClient()

    with SessionLocal() as session:
        user = User(email="user@example.com", google_sub="sub-1")
        session.add(user)
        session.flush()
        email = Email(
            user_id=user.id,
            gmail_message_id="msg-1",
            subject="Project kickoff",
        )
        session.add(email)
        session.flush()
        candidate = CalendarCandidate(
            user_id=user.id,
            email_id=email.id,
            payload={
                "type": "PROPOSED_TIME",
                "start": "2099-01-05T10:00:00+00:00",
                "end": "2099-01-05T10:30:00+00:00",
                "attendees": ["guest@example.com"],
            },
            status="PROPOSED",
        )
        session.add(candidate)
        session.commit()

        overrides = {
            "title": "Kickoff sync",
            "start": datetime(2099, 1, 5, 10, 15, tzinfo=UTC),
            "end": datetime(2099, 1, 5, 10, 45, tzinfo=UTC),
            "timezone": "UTC",
            "location": "Zoom",
            "attendees": ["guest@example.com", "other@example.com"],
        }
        event = create_event(
            session,
            settings,
            crypto,
            user.id,
            candidate.id,
            overrides=overrides,
            client=client,
        )

        stored = session.get(CalendarEventCreated, event.id)
        assert stored is not None
        assert stored.event_id == "evt-123"
        assert stored.status == "CREATED"
        assert client.calls
        event_body = client.calls[0]["event_body"]
        assert event_body["summary"] == "Kickoff sync"
        assert event_body["location"] == "Zoom"
        assert "Email subject: Project kickoff" in event_body["description"]
