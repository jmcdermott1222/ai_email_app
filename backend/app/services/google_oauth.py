"""Google OAuth helpers and token refresh handling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import requests
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2 import credentials as google_credentials
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow

from app.config import Settings
from app.crypto import CryptoProvider
from app.models import GoogleOAuthToken

GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"

GOOGLE_OAUTH_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]

TOKEN_STATUS_OK = "OK"
TOKEN_STATUS_NEEDS_REAUTH = "NEEDS_REAUTH"
TOKEN_STATUS_ERROR = "ERROR"


def build_oauth_flow(settings: Settings) -> Flow:
    """Create a configured OAuth flow."""
    client_config = {
        "web": {
            "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret,
            "auth_uri": GOOGLE_AUTH_URI,
            "token_uri": GOOGLE_TOKEN_URI,
        }
    }
    flow = Flow.from_client_config(client_config, scopes=GOOGLE_OAUTH_SCOPES)
    flow.redirect_uri = settings.google_oauth_redirect_uri
    return flow


def verify_id_token(id_token_str: str, settings: Settings) -> dict:
    """Verify the ID token and return decoded claims."""
    request = Request()
    return id_token.verify_oauth2_token(
        id_token_str, request, settings.google_oauth_client_id
    )


@dataclass(frozen=True)
class RefreshResult:
    ok: bool
    needs_reauth: bool
    error_code: str | None = None
    error_message: str | None = None


class TokenExchangeError(RuntimeError):
    """Raised when the OAuth token exchange fails."""


def exchange_code_for_token(code: str, settings: Settings) -> dict:
    """Exchange an authorization code for tokens."""
    data = {
        "code": code,
        "client_id": settings.google_oauth_client_id,
        "client_secret": settings.google_oauth_client_secret,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "grant_type": "authorization_code",
    }
    response = requests.post(GOOGLE_TOKEN_URI, data=data, timeout=10)
    if response.status_code != 200:
        raise TokenExchangeError(response.text)
    return response.json()


def refresh_access_token(
    db,
    token_row: GoogleOAuthToken,
    crypto: CryptoProvider,
    settings: Settings,
) -> RefreshResult:
    """Refresh the access token and update token status."""
    if not token_row.refresh_token_enc:
        token_row.token_status = TOKEN_STATUS_NEEDS_REAUTH
        token_row.last_error = "missing_refresh_token"
        db.commit()
        return RefreshResult(
            ok=False,
            needs_reauth=True,
            error_code="missing_refresh_token",
            error_message="Refresh token is missing",
        )

    refresh_token = crypto.decrypt(token_row.refresh_token_enc)
    creds = google_credentials.Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=GOOGLE_TOKEN_URI,
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        scopes=token_row.scopes or GOOGLE_OAUTH_SCOPES,
    )

    try:
        creds.refresh(Request())
    except RefreshError as exc:
        message = str(exc)
        if "invalid_grant" in message.lower():
            token_row.token_status = TOKEN_STATUS_NEEDS_REAUTH
            token_row.last_error = message
            db.commit()
            return RefreshResult(
                ok=False,
                needs_reauth=True,
                error_code="invalid_grant",
                error_message=message,
            )
        token_row.token_status = TOKEN_STATUS_ERROR
        token_row.last_error = message
        db.commit()
        return RefreshResult(
            ok=False,
            needs_reauth=False,
            error_code="refresh_error",
            error_message=message,
        )

    if creds.token:
        token_row.access_token_enc = crypto.encrypt(creds.token)
    token_row.expiry_at = creds.expiry
    token_row.token_status = TOKEN_STATUS_OK
    token_row.last_error = None
    token_row.token_type = token_row.token_type or "Bearer"
    if creds.scopes:
        token_row.scopes = list(creds.scopes)
    token_row.updated_at = datetime.now(UTC)
    db.commit()
    return RefreshResult(ok=True, needs_reauth=False)
