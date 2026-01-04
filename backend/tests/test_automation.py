"""Tests for automation actions."""

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.crypto import LocalDevCrypto
from app.db import Base
from app.models import Email, EmailTriage, User, UserGmailLabel, UserPreferences
from app.services.automation import execute_actions, run_automation_for_email
from app.services.preferences import default_preferences


class FakeGmailClient:
    def __init__(self):
        self.calls = []

    def modify_message_labels(self, message_id, add_label_ids, remove_label_ids):
        self.calls.append(
            ("modify", message_id, tuple(add_label_ids), tuple(remove_label_ids))
        )

    def trash_message(self, message_id):
        self.calls.append(("trash", message_id))


def test_execute_actions_snooze():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

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
        session.add(
            UserGmailLabel(
                user_id=user.id,
                label_name="Copilot/Snoozed",
                label_id="Label_1",
            )
        )
        session.commit()

        client = FakeGmailClient()
        execute_actions(
            session,
            settings,
            crypto,
            user.id,
            email.id,
            ["SNOOZE_UNTIL:2025-02-15T10:00:00Z"],
            client=client,
        )

        updated = session.get(Email, email.id)
        assert updated.is_snoozed is True
        assert updated.snooze_until_ts is not None
        assert client.calls[0][0] == "modify"


def test_run_automation_suggest_only():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

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
        email = Email(
            user_id=user.id,
            gmail_message_id="msg-1",
            internal_date_ts=datetime.now(UTC),
        )
        session.add(email)
        session.flush()
        prefs = default_preferences()
        prefs["automation_level"] = "SUGGEST_ONLY"
        session.add(UserPreferences(user_id=user.id, preferences=prefs))
        session.add(
            EmailTriage(
                user_id=user.id,
                email_id=email.id,
                importance_label="LOW",
                needs_response=False,
            )
        )
        session.commit()

        result = run_automation_for_email(session, settings, crypto, user.id, email.id)
        assert "ARCHIVE" in result.suggested
        assert result.applied == []
