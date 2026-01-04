"""Tests for preferences endpoints."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import User, UserPreferences
from app.routes.preferences import update_preferences
from app.schemas import PreferencesUpdate
from app.services.preferences import default_preferences


def test_update_preferences_preserves_extra_fields():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        user = User(email="user@example.com", google_sub="sub-1")
        session.add(user)
        session.flush()

        prefs = default_preferences()
        prefs["blocked_senders"] = ["blocked@example.com"]
        prefs["style_profile"] = {"profile": {"tone": "direct"}}
        session.add(UserPreferences(user_id=user.id, preferences=prefs))
        session.commit()

        payload = PreferencesUpdate(digest_time_local="09:00")
        update_preferences(payload, current_user=user, db=session)

        updated = session.execute(
            select(UserPreferences).where(UserPreferences.user_id == user.id)
        ).scalar_one()
        stored = updated.preferences or {}
        assert stored["digest_time_local"] == "09:00"
        assert stored["blocked_senders"] == ["blocked@example.com"]
        assert stored["style_profile"]["profile"]["tone"] == "direct"
