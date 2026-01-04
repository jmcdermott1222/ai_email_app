"""Calendar candidate extraction endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import get_current_user
from app.config import Settings, get_settings
from app.crypto import get_crypto
from app.db import get_db
from app.schemas import (
    CalendarCandidateRead,
    CalendarEventCreatedRead,
    CalendarEventCreateRequest,
    MeetingTimeSuggestionRead,
    MeetingTimeSuggestionRequest,
    MeetingTimeSuggestionResponse,
)
from app.services.calendar_events import accept_invite, create_event
from app.services.calendar_extract import (
    generate_calendar_candidates,
    list_calendar_candidates,
)
from app.services.meeting_times import suggest_times

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


@router.post(
    "/calendar/candidates/{candidate_id}/suggest_times",
    response_model=MeetingTimeSuggestionResponse,
)
def suggest_times_endpoint(
    candidate_id: int,
    payload: MeetingTimeSuggestionRequest | None = None,
    current_user=Depends(get_current_user),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    crypto = get_crypto(settings)
    try:
        suggestions = suggest_times(
            db,
            settings,
            crypto,
            current_user.id,
            candidate_id,
            duration_min=payload.duration_min if payload else None,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if detail in {"Calendar candidate not found", "Email not found"}
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return MeetingTimeSuggestionResponse(
        candidate_id=candidate_id,
        suggestions=[
            MeetingTimeSuggestionRead.model_validate(
                {"start": slot.start, "end": slot.end, "score": slot.score}
            )
            for slot in suggestions
        ],
    )


@router.post(
    "/calendar/candidates/{candidate_id}/create_event",
    response_model=CalendarEventCreatedRead,
)
def create_event_endpoint(
    candidate_id: int,
    payload: CalendarEventCreateRequest | None = None,
    current_user=Depends(get_current_user),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    crypto = get_crypto(settings)
    try:
        event = create_event(
            db,
            settings,
            crypto,
            current_user.id,
            candidate_id,
            overrides=payload.model_dump() if payload else None,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if detail in {"Calendar candidate not found", "Email not found"}
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return CalendarEventCreatedRead.model_validate(event)


@router.post(
    "/calendar/candidates/{candidate_id}/accept_invite",
    response_model=CalendarEventCreatedRead,
)
def accept_invite_endpoint(
    candidate_id: int,
    current_user=Depends(get_current_user),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    crypto = get_crypto(settings)
    try:
        event = accept_invite(
            db,
            settings,
            crypto,
            current_user.id,
            candidate_id,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if detail in {"Calendar candidate not found", "Email not found"}
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return CalendarEventCreatedRead.model_validate(event)
