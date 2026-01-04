"""Digest endpoints."""

from __future__ import annotations

from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.auth import get_current_user
from app.config import Settings, get_settings
from app.crypto import get_crypto
from app.db import get_db
from app.models import Digest
from app.schemas import DigestRead
from app.services.digest import default_since_ts, generate_daily_digest
from app.services.gmail_sync import full_sync_inbox

router = APIRouter(prefix="/api")


@router.get("/digests/latest", response_model=DigestRead)
def get_latest_digest(
    current_user=Depends(get_current_user),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    digest = (
        db.execute(
            select(Digest)
            .where(Digest.user_id == current_user.id)
            .order_by(Digest.created_at.desc())
        )
        .scalars()
        .first()
    )
    if not digest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No digest")
    return DigestRead.model_validate(digest)


@router.post("/digests/run_now", response_model=DigestRead)
def run_digest_now(
    current_user=Depends(get_current_user),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    crypto = get_crypto(settings)
    full_sync_inbox(db, current_user.id, settings, crypto)
    latest = (
        db.execute(
            select(Digest)
            .where(Digest.user_id == current_user.id)
            .order_by(Digest.created_at.desc())
        )
        .scalars()
        .first()
    )
    since_ts = default_since_ts(latest)
    if since_ts.tzinfo is None:
        since_ts = since_ts.replace(tzinfo=UTC)
    digest = generate_daily_digest(db, settings, current_user.id, since_ts)
    return DigestRead.model_validate(digest)
