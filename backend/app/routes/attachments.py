"""Attachment processing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.config import Settings, get_settings
from app.crypto import get_crypto
from app.db import get_db
from app.services.attachments import process_attachments_for_email

router = APIRouter(prefix="/api")


@router.post("/emails/{email_id}/attachments/process")
def process_attachments(
    email_id: int,
    current_user=Depends(get_current_user),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    crypto = get_crypto(settings)
    result = process_attachments_for_email(
        db, current_user.id, email_id, settings, crypto
    )
    return {"status": "ok", **result}
