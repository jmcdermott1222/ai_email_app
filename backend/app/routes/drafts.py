"""Draft generation and Gmail draft endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.auth import get_current_user
from app.config import get_settings
from app.crypto import get_crypto
from app.db import get_db
from app.models import Draft
from app.schemas import DraftCreateRequest, DraftRead
from app.services.drafts import create_gmail_draft, propose_draft

router = APIRouter(prefix="/api")


@router.post("/emails/{email_id}/draft/propose", response_model=DraftRead)
def propose_draft_endpoint(
    email_id: int,
    current_user=Depends(get_current_user),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    settings = get_settings()
    crypto = get_crypto(settings)
    try:
        draft = propose_draft(db, settings, crypto, current_user.id, email_id)
    except ValueError as exc:
        detail = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if detail == "Email not found"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return DraftRead.model_validate(draft)


@router.post("/drafts/{draft_id}/create_in_gmail", response_model=DraftRead)
def create_gmail_draft_endpoint(
    draft_id: int,
    payload: DraftCreateRequest | None = None,
    current_user=Depends(get_current_user),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    settings = get_settings()
    crypto = get_crypto(settings)
    try:
        draft = create_gmail_draft(
            db,
            settings,
            crypto,
            current_user.id,
            draft_id,
            subject_override=payload.subject if payload else None,
            body_override=payload.body if payload else None,
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if detail in {"Email not found", "Draft not found"}
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return DraftRead.model_validate(draft)


@router.get("/drafts", response_model=list[DraftRead])
def list_drafts(
    status: str | None = Query(default=None),
    email_id: int | None = Query(default=None),
    current_user=Depends(get_current_user),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    query = select(Draft).where(Draft.user_id == current_user.id)
    if status:
        query = query.where(Draft.status == status)
    if email_id:
        query = query.where(Draft.email_id == email_id)
    query = query.order_by(Draft.created_at.desc())
    drafts = db.execute(query).scalars().all()
    return [DraftRead.model_validate(draft) for draft in drafts]
