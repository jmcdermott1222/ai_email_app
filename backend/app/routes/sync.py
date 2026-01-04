"""Manual Gmail sync endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.config import Settings, get_settings
from app.crypto import get_crypto
from app.db import get_db
from app.services.gmail_sync import full_sync_inbox

router = APIRouter(prefix="/api")


@router.post("/sync/full")
def trigger_full_sync(
    current_user=Depends(get_current_user),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    crypto = get_crypto(settings)
    result = full_sync_inbox(db, current_user.id, settings, crypto)
    return {
        "status": "ok",
        "fetched": result.fetched,
        "upserted": result.upserted,
        "errors": result.errors,
    }
