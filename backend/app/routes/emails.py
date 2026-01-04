"""Email listing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.auth import get_current_user
from app.db import get_db
from app.models import Email
from app.schemas import EmailDetail, EmailRead

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
    return [EmailRead.model_validate(row) for row in result.scalars().all()]


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
    return EmailDetail.model_validate(email)
