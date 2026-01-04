"""Session auth helpers for the API."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Request, status

from app.config import Settings, get_settings
from app.db import SessionLocal, get_db
from app.models import User


class AuthError(RuntimeError):
    """Raised when session authentication fails."""


def _session_expiry(settings: Settings) -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.session_ttl_days)


def create_session_token(user: User, settings: Settings) -> str:
    """Create a signed JWT for the session cookie."""
    if not settings.session_jwt_secret:
        raise AuthError("SESSION_JWT_SECRET is not configured")
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "exp": _session_expiry(settings),
        "iat": datetime.now(UTC),
        "iss": settings.app_name,
    }
    return jwt.encode(payload, settings.session_jwt_secret, algorithm="HS256")


def decode_session_token(token: str, settings: Settings) -> dict:
    """Decode and validate a session token."""
    if not settings.session_jwt_secret:
        raise AuthError("SESSION_JWT_SECRET is not configured")
    try:
        return jwt.decode(token, settings.session_jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Session expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Invalid session token") from exc


def set_session_cookie(response, token: str, settings: Settings) -> None:
    """Attach the session cookie to the response."""
    max_age = int(timedelta(days=settings.session_ttl_days).total_seconds())
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path="/",
    )


def clear_session_cookie(response, settings: Settings) -> None:
    """Clear the session cookie on the response."""
    response.delete_cookie(settings.session_cookie_name, path="/")


def authenticate_request(request: Request, settings: Settings) -> User:
    """Authenticate a request based on the session cookie."""
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise AuthError("Missing session cookie")

    payload = decode_session_token(token, settings)
    user_id = payload.get("sub")
    if not user_id:
        raise AuthError("Missing session subject")

    with SessionLocal() as db:
        user = db.get(User, int(user_id))
        if not user:
            raise AuthError("User not found")
        request.state.user = user
        return user


def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
) -> User:
    """Dependency that returns the authenticated user."""
    if hasattr(request.state, "user") and request.state.user:
        return request.state.user

    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session cookie",
        )

    try:
        payload = decode_session_token(token, settings)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
        )

    user = db.get(User, int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    request.state.user = user
    return user
