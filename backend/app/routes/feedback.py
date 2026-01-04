"""Feedback endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.auth import get_current_user
from app.db import get_db
from app.models import Email, EmailFeedback, UserPreferences
from app.schemas import EmailFeedbackRequest
from app.services.preferences import default_preferences

router = APIRouter(prefix="/api")


@router.post("/emails/{email_id}/feedback")
def submit_feedback(
    email_id: int,
    payload: EmailFeedbackRequest,
    current_user=Depends(get_current_user),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    email = db.execute(
        select(Email).where(Email.id == email_id, Email.user_id == current_user.id)
    ).scalar_one_or_none()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Email not found"
        )

    feedback = EmailFeedback(
        user_id=current_user.id,
        email_id=email.id,
        feedback_label=payload.feedback_label,
        notes=payload.reason,
    )
    db.add(feedback)

    preferences = db.execute(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    ).scalar_one_or_none()
    if not preferences:
        preferences = UserPreferences(
            user_id=current_user.id,
            preferences=default_preferences(),
        )
        db.add(preferences)
        db.flush()

    pref_data = dict(preferences.preferences or default_preferences())
    pref_data["blocked_senders"] = list(pref_data.get("blocked_senders", []))
    pref_data["blocked_domains"] = list(pref_data.get("blocked_domains", []))
    pref_data["blocked_keywords"] = list(pref_data.get("blocked_keywords", []))

    if payload.always_ignore_sender and email.from_email:
        sender = email.from_email.lower()
        if sender not in pref_data["blocked_senders"]:
            pref_data["blocked_senders"].append(sender)
        if "@" in sender:
            domain = sender.split("@")[-1]
            if domain and domain not in pref_data["blocked_domains"]:
                pref_data["blocked_domains"].append(domain)

    if payload.always_ignore_keyword:
        keyword = payload.always_ignore_keyword.strip().lower()
        if keyword and keyword not in pref_data["blocked_keywords"]:
            pref_data["blocked_keywords"].append(keyword)

    preferences.preferences = pref_data
    db.commit()
    return {"status": "ok"}
