"""Tests for calendar event creation."""

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.crypto import LocalDevCrypto
from app.db import Base
from app.models import CalendarCandidate, CalendarEventCreated, Email, User
from app.services.calendar_events import accept_invite, create_event


class FakeCalendarClient:
    def __init__(self):
        self.calls = []
        self.list_events_response = {"items": []}
        self.patch_event_response = {"id": "evt-999"}

    def create_event(self, calendar_id, event_body, send_updates="all"):
        self.calls.append(
            {
                "create_event": True,
                "calendar_id": calendar_id,
                "event_body": event_body,
                "send_updates": send_updates,
            }
        )
        return {
            "id": "evt-123",
            "htmlLink": "https://calendar.google.com/event?eid=evt-123",
        }

    def list_events(
        self,
        calendar_id,
        ical_uid=None,
        time_min=None,
        time_max=None,
        max_results=10,
    ):
        self.calls.append(
            {
                "list_events": True,
                "calendar_id": calendar_id,
                "ical_uid": ical_uid,
                "time_min": time_min,
                "time_max": time_max,
                "max_results": max_results,
            }
        )
        return self.list_events_response

    def patch_event(self, calendar_id, event_id, event_body, send_updates="all"):
        self.calls.append(
            {
                "patch_event": True,
                "calendar_id": calendar_id,
                "event_id": event_id,
                "event_body": event_body,
                "send_updates": send_updates,
            }
        )
        return self.patch_event_response

    def get_event(self, calendar_id, event_id):
        self.calls.append(
            {
                "get_event": True,
                "calendar_id": calendar_id,
                "event_id": event_id,
            }
        )
        return {
            "id": event_id,
            "attendees": [{"email": "user@example.com", "self": True}],
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


def test_accept_invite_creates_event_and_marks_status_when_missing():
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
            gmail_message_id="msg-2",
            subject="Invite",
        )
        session.add(email)
        session.flush()
        candidate = CalendarCandidate(
            user_id=user.id,
            email_id=email.id,
            payload={
                "type": "INVITE",
                "title": "Team sync",
                "start": "2099-02-10T09:00:00+00:00",
                "end": "2099-02-10T10:00:00+00:00",
                "attendees": ["guest@example.com"],
                "ical_uid": "invite-123",
            },
            status="PROPOSED",
        )
        session.add(candidate)
        session.commit()

        event = accept_invite(
            session,
            settings,
            crypto,
            user.id,
            candidate.id,
            client=client,
        )

        stored = session.get(CalendarEventCreated, event.id)
        assert stored is not None
        assert stored.status == "ACCEPTED"
        assert stored.event_id == "evt-123"
        assert stored.candidate.status == "INVITE_ACCEPTED"
        assert any(call.get("list_events") for call in client.calls)
        assert not any(call.get("patch_event") for call in client.calls)


def test_accept_invite_updates_existing_event():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    settings = Settings()
    crypto = LocalDevCrypto("BB0iMhzIaIMZeMACaGkNykzlCaM3Ndoth7-vBeQiJ4U=")
    client = FakeCalendarClient()
    client.list_events_response = {
        "items": [
            {
                "id": "evt-existing",
                "attendees": [{"email": "user@example.com", "self": True}],
            }
        ]
    }
    client.patch_event_response = {"id": "evt-existing"}

    with SessionLocal() as session:
        user = User(email="user@example.com", google_sub="sub-2")
        session.add(user)
        session.flush()
        email = Email(
            user_id=user.id,
            gmail_message_id="msg-3",
            subject="Invite",
        )
        session.add(email)
        session.flush()
        candidate = CalendarCandidate(
            user_id=user.id,
            email_id=email.id,
            payload={
                "type": "INVITE",
                "title": "Team sync",
                "start": "2099-02-10T09:00:00+00:00",
                "end": "2099-02-10T10:00:00+00:00",
                "attendees": ["guest@example.com"],
                "ical_uid": "invite-123",
            },
            status="PROPOSED",
        )
        session.add(candidate)
        session.commit()

        event = accept_invite(
            session,
            settings,
            crypto,
            user.id,
            candidate.id,
            client=client,
        )

        stored = session.get(CalendarEventCreated, event.id)
        assert stored is not None
        assert stored.status == "ACCEPTED"
        assert stored.event_id == "evt-existing"
        assert stored.candidate.status == "INVITE_ACCEPTED"
        assert any(call.get("patch_event") for call in client.calls)
        assert not any(call.get("create_event") for call in client.calls)
