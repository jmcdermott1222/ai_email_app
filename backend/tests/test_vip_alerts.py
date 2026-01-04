"""Tests for VIP alert matching."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Email, User, UserPreferences
from app.services.vip_alerts import create_vip_alert_if_needed


def test_create_vip_alert_sender_match():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        user = User(email="user@example.com", google_sub="sub-1")
        session.add(user)
        session.flush()
        session.add(
            UserPreferences(
                user_id=user.id,
                preferences={
                    "vip_alerts_enabled": True,
                    "vip_senders": ["vip@example.com"],
                    "vip_domains": [],
                    "vip_keywords": [],
                },
            )
        )
        email = Email(
            user_id=user.id,
            gmail_message_id="msg-1",
            subject="Hello",
            from_email="vip@example.com",
        )
        session.add(email)
        session.commit()

        alert = create_vip_alert_if_needed(session, user.id, email)
        session.commit()

        assert alert is not None
        assert alert.reason and "sender_match" in alert.reason


def test_no_alert_when_disabled():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        user = User(email="user@example.com", google_sub="sub-1")
        session.add(user)
        session.flush()
        session.add(
            UserPreferences(
                user_id=user.id,
                preferences={
                    "vip_alerts_enabled": False,
                    "vip_senders": ["vip@example.com"],
                    "vip_domains": [],
                    "vip_keywords": [],
                },
            )
        )
        email = Email(
            user_id=user.id,
            gmail_message_id="msg-1",
            subject="Hello",
            from_email="vip@example.com",
        )
        session.add(email)
        session.commit()

        alert = create_vip_alert_if_needed(session, user.id, email)
        assert alert is None
