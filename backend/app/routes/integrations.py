"""Integration status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.auth import get_current_user
from app.config import Settings, get_settings
from app.crypto import get_crypto
from app.db import get_db
from app.models import GoogleOAuthToken
from app.schemas import GoogleIntegrationStatus
from app.services.google_oauth import (
    TOKEN_STATUS_NEEDS_REAUTH,
    refresh_access_token,
)

router = APIRouter(prefix="/api")


@router.get("/integrations/google/status", response_model=GoogleIntegrationStatus)
def google_integration_status(
    current_user=Depends(get_current_user),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
) -> GoogleIntegrationStatus:
    token_row = db.execute(
        select(GoogleOAuthToken).where(GoogleOAuthToken.user_id == current_user.id)
    ).scalar_one_or_none()
    if not token_row:
        return GoogleIntegrationStatus(
            connected=False,
            token_status=None,
            needs_reauth=False,
            last_error=None,
        )

    crypto = get_crypto(settings)
    if token_row.token_status != TOKEN_STATUS_NEEDS_REAUTH:
        refresh_access_token(db, token_row, crypto, settings)

    return GoogleIntegrationStatus(
        connected=True,
        token_status=token_row.token_status,
        needs_reauth=token_row.token_status == TOKEN_STATUS_NEEDS_REAUTH,
        last_error=token_row.last_error,
    )
