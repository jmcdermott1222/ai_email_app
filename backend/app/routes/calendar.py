"""Calendar candidate extraction endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user
from app.config import Settings, get_settings
from app.crypto import get_crypto
from app.db import get_db
from app.schemas import CalendarCandidateRead
from app.services.calendar_extract import (
    generate_calendar_candidates,
    list_calendar_candidates,
)

router = APIRouter(prefix="/api")


@router.post(
    "/emails/{email_id}/calendar/propose",
    response_model=list[CalendarCandidateRead],
)
def propose_calendar_candidates(
    email_id: int,
    current_user=Depends(get_current_user),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    crypto = get_crypto(settings)
    try:
        candidates = generate_calendar_candidates(
            db, settings, crypto, current_user.id, email_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return [CalendarCandidateRead.model_validate(row) for row in candidates]


@router.get(
    "/emails/{email_id}/calendar/candidates",
    response_model=list[CalendarCandidateRead],
)
def get_calendar_candidates(
    email_id: int,
    current_user=Depends(get_current_user),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    candidates = list_calendar_candidates(db, current_user.id, email_id)
    return [CalendarCandidateRead.model_validate(row) for row in candidates]
