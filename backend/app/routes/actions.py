"""Automation and action endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.auth import get_current_user
from app.config import Settings, get_settings
from app.crypto import get_crypto
from app.db import get_db
from app.models import AuditLog
from app.schemas import AuditLogRead, EmailActionsRequest
from app.services.automation import execute_actions, run_automation_for_email

router = APIRouter(prefix="/api")


@router.post("/emails/{email_id}/actions")
def run_actions(
    email_id: int,
    payload: EmailActionsRequest,
    current_user=Depends(get_current_user),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    crypto = get_crypto(settings)
    try:
        result = execute_actions(
            db, settings, crypto, current_user.id, email_id, payload.actions
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return {"status": "ok", "applied": result.applied, "skipped": result.skipped}


@router.post("/automation/run_for_email/{email_id}")
def run_automation(
    email_id: int,
    current_user=Depends(get_current_user),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    crypto = get_crypto(settings)
    try:
        result = run_automation_for_email(
            db, settings, crypto, current_user.id, email_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return {
        "status": "ok",
        "suggested": result.suggested,
        "applied": result.applied,
        "skipped": result.skipped,
    }


@router.get("/audit", response_model=list[AuditLogRead])
def list_audit(
    current_user=Depends(get_current_user),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    rows = (
        db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == current_user.id)
            .order_by(AuditLog.created_at.desc())
            .limit(50)
        )
        .scalars()
        .all()
    )
    return [AuditLogRead.model_validate(row) for row in rows]
