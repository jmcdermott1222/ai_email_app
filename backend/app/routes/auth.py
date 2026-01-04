"""OAuth and session endpoints."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.auth import clear_session_cookie, create_session_token, set_session_cookie
from app.config import Settings, get_settings
from app.crypto import get_crypto
from app.db import get_db
from app.models import GmailSyncState, GoogleOAuthToken, User
from app.services.google_oauth import (
    GOOGLE_OAUTH_SCOPES,
    TOKEN_STATUS_OK,
    TokenExchangeError,
    build_oauth_flow,
    exchange_code_for_token,
    verify_id_token,
)

router = APIRouter()


@router.get("/auth/google/start")
def google_oauth_start(
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> RedirectResponse:
    """Redirect the user to Google's OAuth consent screen."""
    flow = build_oauth_flow(settings)
    state = secrets.token_urlsafe(32)
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
        state=state,
    )
    response = RedirectResponse(authorization_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        "oauth_state",
        state,
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path="/",
    )
    return response


@router.get("/auth/google/callback")
def google_oauth_callback(
    request: Request,
    settings: Settings = Depends(get_settings),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
) -> RedirectResponse:
    """Handle the OAuth callback and establish a session."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    stored_state = request.cookies.get("oauth_state")

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth parameters",
        )

    if not stored_state or stored_state != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        )

    try:
        token_payload = exchange_code_for_token(code, settings)
    except TokenExchangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange OAuth code",
        ) from exc

    id_token_value = token_payload.get("id_token")
    if not id_token_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing ID token",
        )

    id_info = verify_id_token(id_token_value, settings)
    email = id_info.get("email")
    google_sub = id_info.get("sub")

    if not email or not google_sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID token claims",
        )

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user:
        user = User(email=email, google_sub=google_sub)
        db.add(user)
        db.flush()
    else:
        user.google_sub = google_sub

    crypto = get_crypto(settings)
    token_row = db.execute(
        select(GoogleOAuthToken).where(GoogleOAuthToken.user_id == user.id)
    ).scalar_one_or_none()
    if not token_row:
        token_row = GoogleOAuthToken(user_id=user.id)
        db.add(token_row)

    refresh_token = token_payload.get("refresh_token")
    if refresh_token:
        token_row.refresh_token_enc = crypto.encrypt(refresh_token)
    elif not token_row.refresh_token_enc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing refresh token; reauthorize with consent",
        )

    access_token = token_payload.get("access_token")
    if access_token:
        token_row.access_token_enc = crypto.encrypt(access_token)
    token_row.token_type = token_payload.get("token_type") or "Bearer"
    expires_in = token_payload.get("expires_in")
    if isinstance(expires_in, int):
        token_row.expiry_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    scope_str = token_payload.get("scope")
    if scope_str:
        token_row.scopes = scope_str.split()
    else:
        token_row.scopes = GOOGLE_OAUTH_SCOPES
    token_row.token_status = TOKEN_STATUS_OK
    token_row.last_error = None

    sync_state = db.execute(
        select(GmailSyncState).where(GmailSyncState.user_id == user.id)
    ).scalar_one_or_none()
    if not sync_state:
        sync_state = GmailSyncState(user_id=user.id)
        db.add(sync_state)

    db.commit()

    session_token = create_session_token(user, settings)
    response = RedirectResponse(
        f"{settings.web_base_url}/dashboard", status_code=status.HTTP_302_FOUND
    )
    response.delete_cookie("oauth_state", path="/")
    set_session_cookie(response, session_token, settings)
    return response


@router.post("/auth/logout")
def logout(
    response: Response,
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> dict:
    """Clear the session cookie."""
    clear_session_cookie(response, settings)
    return {"status": "ok"}
