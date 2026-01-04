"""Tests for feedback endpoints."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Email, EmailFeedback, User, UserPreferences
from app.routes.feedback import submit_feedback
from app.schemas import EmailFeedbackRequest
from app.services.preferences import default_preferences


def test_feedback_updates_blocklists():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        user = User(email="user@example.com", google_sub="sub-1")
        session.add(user)
        session.flush()

        prefs = UserPreferences(user_id=user.id, preferences=default_preferences())
        session.add(prefs)

        email = Email(
            user_id=user.id,
            gmail_message_id="msg-1",
            from_email="sender@example.com",
        )
        session.add(email)
        session.commit()

        payload = EmailFeedbackRequest(
            feedback_label="NOT_IMPORTANT",
            reason="Not relevant",
            always_ignore_sender=True,
            always_ignore_keyword="promo",
        )

        submit_feedback(email.id, payload, current_user=user, db=session)

        feedback = session.execute(select(EmailFeedback)).scalar_one()
        assert feedback.feedback_label == "NOT_IMPORTANT"

        updated_prefs = session.execute(
            select(UserPreferences).where(UserPreferences.user_id == user.id)
        ).scalar_one()
        prefs_data = updated_prefs.preferences or {}
        assert "sender@example.com" in prefs_data["blocked_senders"]
        assert "example.com" in prefs_data["blocked_domains"]
        assert "promo" in prefs_data["blocked_keywords"]
