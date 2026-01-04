"""User preferences endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.auth import get_current_user
from app.db import get_db
from app.models import UserPreferences
from app.schemas import Preferences, PreferencesUpdate
from app.services.preferences import default_preferences

router = APIRouter(prefix="/api")


@router.get("/preferences", response_model=Preferences)
def get_preferences(
    current_user=Depends(get_current_user),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    preferences = db.execute(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    ).scalar_one_or_none()
    if not preferences:
        preferences = UserPreferences(
            user_id=current_user.id,
            preferences=default_preferences(),
        )
        db.add(preferences)
        db.commit()

    return Preferences.model_validate(preferences.preferences or default_preferences())


@router.put("/preferences", response_model=Preferences)
def update_preferences(
    payload: PreferencesUpdate,
    current_user=Depends(get_current_user),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    preferences = db.execute(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    ).scalar_one_or_none()
    if not preferences:
        preferences = UserPreferences(
            user_id=current_user.id,
            preferences=default_preferences(),
        )
        db.add(preferences)
        db.commit()

    current = {**default_preferences(), **(preferences.preferences or {})}
    updates = payload.model_dump(exclude_none=True)
    if "working_hours" in updates and updates["working_hours"] is None:
        updates.pop("working_hours", None)
    merged = {**current, **updates}

    try:
        validated = Preferences.model_validate(merged)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    persisted = dict(current)
    persisted.update(validated.model_dump())
    preferences.preferences = persisted
    db.commit()
    return validated
