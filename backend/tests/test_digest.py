"""Tests for digest generation."""

from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.db import Base
from app.models import Email, EmailTriage, User
from app.services.digest import generate_daily_digest


def test_generate_daily_digest_groups_sections():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    settings = Settings(openai_api_key="test-key")

    with SessionLocal() as session:
        user = User(email="user@example.com", google_sub="sub-1")
        session.add(user)
        session.flush()

        email_reply = Email(
            user_id=user.id,
            gmail_message_id="msg-1",
            subject="Need response",
            internal_date_ts=datetime(2099, 1, 2, tzinfo=UTC),
        )
        email_fyi = Email(
            user_id=user.id,
            gmail_message_id="msg-2",
            subject="FYI update",
            internal_date_ts=datetime(2099, 1, 3, tzinfo=UTC),
        )
        email_other = Email(
            user_id=user.id,
            gmail_message_id="msg-3",
            subject="Other",
            internal_date_ts=datetime(2099, 1, 4, tzinfo=UTC),
        )
        session.add_all([email_reply, email_fyi, email_other])
        session.flush()
        session.add(
            EmailTriage(
                user_id=user.id,
                email_id=email_reply.id,
                importance_label="HIGH",
                needs_response=True,
                reasoning={"summary_bullets": ["Reply"], "why_important": "Need reply"},
            )
        )
        session.add(
            EmailTriage(
                user_id=user.id,
                email_id=email_fyi.id,
                importance_label="MEDIUM",
                needs_response=False,
                reasoning={"summary_bullets": ["FYI"], "why_important": "FYI"},
            )
        )
        session.commit()

        since_ts = datetime(2099, 1, 1, tzinfo=UTC)
        digest = generate_daily_digest(
            session,
            settings,
            user.id,
            since_ts,
            max_triage=0,
            now=datetime(2099, 1, 5, tzinfo=UTC),
        )

        content = digest.content_json or {}
        sections = content.get("sections", {})
        assert len(sections.get("needs_reply", [])) == 1
        assert len(sections.get("important_fyi", [])) == 1
        assert len(sections.get("everything_else", [])) == 1


def test_generate_daily_digest_reports_cap_hit(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    settings = Settings(openai_api_key="test-key")

    def fake_triage(*args, **kwargs):
        return SimpleNamespace(
            importance_label="HIGH",
            needs_response=True,
            reasoning={"summary_bullets": [], "why_important": "Test"},
        )

    monkeypatch.setattr("app.services.digest.triage_email", fake_triage)

    with SessionLocal() as session:
        user = User(email="user@example.com", google_sub="sub-2")
        session.add(user)
        session.flush()

        emails = [
            Email(
                user_id=user.id,
                gmail_message_id=f"msg-{index}",
                subject=f"Email {index}",
                internal_date_ts=datetime(2099, 1, 2, tzinfo=UTC),
            )
            for index in range(3)
        ]
        session.add_all(emails)
        session.commit()

        since_ts = datetime(2099, 1, 1, tzinfo=UTC)
        digest = generate_daily_digest(
            session,
            settings,
            user.id,
            since_ts,
            max_triage=1,
            now=datetime(2099, 1, 5, tzinfo=UTC),
        )

        content = digest.content_json or {}
        assert content.get("triage_cap") == 1
        assert content.get("triage_cap_hit") is True
