"""Tests for calendar candidate extraction."""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.crypto import LocalDevCrypto
from app.db import Base
from app.models import Attachment, CalendarCandidate, Email, User
from app.services.calendar_extract import detect_ics_invites, extract_in_text_candidates


def test_detect_ics_invite_from_attachment(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    fixture_path = Path(__file__).parent / "fixtures" / "invite.ics"
    ics_bytes = fixture_path.read_bytes()

    def fake_download(*args, **kwargs):
        return ics_bytes

    monkeypatch.setattr(
        "app.services.calendar_extract.download_attachment_bytes", fake_download
    )

    settings = Settings(
        google_oauth_client_id="client",
        google_oauth_client_secret="secret",
        encryption_key="unused",
    )
    crypto = LocalDevCrypto("BB0iMhzIaIMZeMACaGkNykzlCaM3Ndoth7-vBeQiJ4U=")

    with SessionLocal() as session:
        user = User(email="user@example.com", google_sub="sub-1")
        session.add(user)
        session.flush()
        email = Email(user_id=user.id, gmail_message_id="msg-1")
        session.add(email)
        session.flush()
        session.add(
            Attachment(
                user_id=user.id,
                email_id=email.id,
                filename="invite.ics",
                mime_type="text/calendar",
                gmail_attachment_id="att-1",
            )
        )
        session.commit()

        detect_ics_invites(
            session, settings, crypto, user.id, email.id, include_inline=False
        )
        candidates = session.execute(select(CalendarCandidate)).scalars().all()
        assert len(candidates) == 1
        payload = candidates[0].payload or {}
        assert payload.get("type") == "INVITE"
        assert payload.get("title") == "Test Meeting"
        assert "alice@example.com" in payload.get("attendees", [])


def test_extract_in_text_candidates_deterministic():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    settings = Settings(
        google_oauth_client_id="client",
        google_oauth_client_secret="secret",
    )

    with SessionLocal() as session:
        user = User(email="user@example.com", google_sub="sub-1")
        session.add(user)
        session.flush()
        email = Email(
            user_id=user.id,
            gmail_message_id="msg-1",
            subject="Meeting",
            clean_body_text="Can we meet on March 5 at 3pm?",
        )
        session.add(email)
        session.commit()

        now = datetime(2025, 1, 1, tzinfo=UTC)
        candidates = extract_in_text_candidates(
            session, settings, user.id, email.id, now=now
        )
        assert len(candidates) == 1
        payload = candidates[0].payload or {}
        assert payload.get("type") == "PROPOSED_TIME"
        assert str(payload.get("start", "")).startswith("2025-03-05")
