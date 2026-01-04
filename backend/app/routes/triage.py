"""Email triage endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.auth import get_current_user
from app.config import Settings, get_settings
from app.db import get_db
from app.models import EmailTriage
from app.schemas import EmailTriageResponse
from app.services.triage import triage_email

router = APIRouter(prefix="/api")


@router.post("/emails/{email_id}/triage", response_model=EmailTriageResponse)
def run_triage(
    email_id: int,
    current_user=Depends(get_current_user),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    try:
        triage = triage_email(db, settings, current_user.id, email_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    summary_bullets = []
    why_important = None
    if triage.reasoning:
        summary_bullets = triage.reasoning.get("summary_bullets", [])
        why_important = triage.reasoning.get("why_important")
    return EmailTriageResponse(
        importance_label=triage.importance_label,
        needs_response=triage.needs_response,
        summary_bullets=summary_bullets,
        why_important=why_important,
    )


@router.get("/emails/{email_id}/triage", response_model=EmailTriageResponse)
def get_triage(
    email_id: int,
    current_user=Depends(get_current_user),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    triage = db.execute(
        select(EmailTriage).where(
            EmailTriage.email_id == email_id,
            EmailTriage.user_id == current_user.id,
        )
    ).scalar_one_or_none()
    if not triage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Triage not found"
        )

    summary_bullets = []
    why_important = None
    if triage.reasoning:
        summary_bullets = triage.reasoning.get("summary_bullets", [])
        why_important = triage.reasoning.get("why_important")
    return EmailTriageResponse(
        importance_label=triage.importance_label,
        needs_response=triage.needs_response,
        summary_bullets=summary_bullets,
        why_important=why_important,
    )
