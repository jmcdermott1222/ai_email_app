"""Email listing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.auth import get_current_user
from app.db import get_db
from app.models import Email
from app.schemas import AttachmentRead, EmailDetail, EmailRead

router = APIRouter(prefix="/api")


@router.get("/emails", response_model=list[EmailRead])
def list_emails(
    current_user=Depends(get_current_user),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
    filter: str = Query(default="inbox"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    query = select(Email).where(Email.user_id == current_user.id)
    if filter == "inbox":
        query = query.where(Email.label_ids.contains(["INBOX"]))
    query = (
        query.order_by(Email.internal_date_ts.desc().nullslast())
        .limit(limit)
        .offset(offset)
    )
    result = db.execute(query)
    emails = []
    for email in result.scalars().all():
        triage = email.triage
        why_important = None
        if triage and triage.reasoning:
            why_important = triage.reasoning.get("why_important")
        emails.append(
            EmailRead(
                **EmailRead.model_validate(email).model_dump(),
                importance_label=triage.importance_label if triage else None,
                needs_response=triage.needs_response if triage else None,
                why_important=why_important,
            )
        )
    return emails


@router.get("/emails/{email_id}", response_model=EmailDetail)
def get_email(
    email_id: int,
    current_user=Depends(get_current_user),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    email = db.get(Email, email_id)
    if not email or email.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Email not found"
        )
    attachments = [AttachmentRead.model_validate(item) for item in email.attachments]
    triage = email.triage
    summary_bullets = []
    why_important = None
    if triage and triage.reasoning:
        summary_bullets = triage.reasoning.get("summary_bullets", [])
        why_important = triage.reasoning.get("why_important")
    data = EmailDetail.model_validate(email)
    return EmailDetail(
        **data.model_dump(),
        attachments=attachments,
        importance_label=triage.importance_label if triage else None,
        needs_response=triage.needs_response if triage else None,
        why_important=why_important,
        summary_bullets=summary_bullets,
    )
