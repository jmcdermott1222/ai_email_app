"""Helpers for building Google OAuth credentials from stored tokens."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2 import credentials as google_credentials
from sqlalchemy.orm import Session

from app.config import Settings
from app.crypto import CryptoProvider
from app.models import GoogleOAuthToken
from app.services.google_oauth import (
    GOOGLE_OAUTH_SCOPES,
    TOKEN_STATUS_ERROR,
    TOKEN_STATUS_NEEDS_REAUTH,
    TOKEN_STATUS_OK,
)


class CredentialsError(RuntimeError):
    """Raised when credentials cannot be constructed."""


@dataclass(frozen=True)
class CredentialsResult:
    credentials: google_credentials.Credentials
    refreshed: bool


def build_credentials(
    db: Session,
    token_row: GoogleOAuthToken,
    settings: Settings,
    crypto: CryptoProvider,
) -> CredentialsResult:
    """Build Google credentials for a token row, refreshing if needed."""
    if not token_row.refresh_token_enc:
        token_row.token_status = TOKEN_STATUS_NEEDS_REAUTH
        token_row.last_error = "missing_refresh_token"
        db.commit()
        raise CredentialsError("Refresh token missing")

    refresh_token = crypto.decrypt(token_row.refresh_token_enc)
    access_token = (
        crypto.decrypt(token_row.access_token_enc)
        if token_row.access_token_enc
        else None
    )
    creds = google_credentials.Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        scopes=token_row.scopes or GOOGLE_OAUTH_SCOPES,
    )
    if token_row.expiry_at:
        creds.expiry = token_row.expiry_at

    refreshed = False
    if not creds.valid:
        try:
            creds.refresh(Request())
            refreshed = True
        except RefreshError as exc:
            message = str(exc)
            if "invalid_grant" in message.lower():
                token_row.token_status = TOKEN_STATUS_NEEDS_REAUTH
            else:
                token_row.token_status = TOKEN_STATUS_ERROR
            token_row.last_error = message
            db.commit()
            raise CredentialsError("Failed to refresh credentials") from exc

    if refreshed and creds.token:
        token_row.access_token_enc = crypto.encrypt(creds.token)
        token_row.expiry_at = creds.expiry
        token_row.token_status = TOKEN_STATUS_OK
        token_row.last_error = None
        token_row.updated_at = datetime.now(UTC)
        db.commit()

    return CredentialsResult(credentials=creds, refreshed=refreshed)
