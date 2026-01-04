"""VIP alert endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.auth import get_current_user
from app.db import get_db
from app.models import Alert
from app.schemas import AlertRead

router = APIRouter(prefix="/api")


@router.get("/alerts", response_model=list[AlertRead])
def list_alerts(
    unread_only: bool = Query(default=True),
    current_user=Depends(get_current_user),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    query = select(Alert).where(Alert.user_id == current_user.id)
    if unread_only:
        query = query.where(Alert.read_at.is_(None))
    query = query.order_by(Alert.created_at.desc())
    alerts = db.execute(query).scalars().all()
    response = []
    for alert in alerts:
        email = alert.email
        payload = AlertRead.model_validate(alert).model_dump()
        payload.update(
            {
                "email_subject": email.subject if email else None,
                "email_from": email.from_email if email else None,
                "email_snippet": email.snippet if email else None,
                "email_internal_date_ts": email.internal_date_ts if email else None,
            }
        )
        response.append(AlertRead(**payload))
    return response


@router.post("/alerts/{alert_id}/mark_read", response_model=AlertRead)
def mark_alert_read(
    alert_id: int,
    current_user=Depends(get_current_user),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    alert = db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == current_user.id)
    ).scalar_one_or_none()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
        )
    alert.read_at = datetime.now(UTC)
    db.commit()
    email = alert.email
    payload = AlertRead.model_validate(alert).model_dump()
    payload.update(
        {
            "email_subject": email.subject if email else None,
            "email_from": email.from_email if email else None,
            "email_snippet": email.snippet if email else None,
            "email_internal_date_ts": email.internal_date_ts if email else None,
        }
    )
    return AlertRead(**payload)
