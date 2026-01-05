"""Webhook endpoints for external integrations."""

from __future__ import annotations

import base64
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from sqlalchemy import func, select

from app.config import Settings, get_settings
from app.crypto import get_crypto
from app.db import get_db
from app.models import User
from app.services.queueing import enqueue_incremental_sync

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/webhooks/gmail/push")
async def gmail_push(
    request: Request,
    settings: Settings = Depends(get_settings),  # noqa: B008
    db=Depends(get_db),  # noqa: B008
):
    _verify_webhook(request, settings)
    payload = await request.json()
    message = payload.get("message") or {}
    data = message.get("data")
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing message data"
        )

    try:
        decoded = base64.b64decode(data).decode("utf-8")
        notification = json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Pub/Sub payload",
        ) from exc

    email_address = notification.get("emailAddress")
    history_id = notification.get("historyId")
    if not email_address or not history_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing emailAddress or historyId",
        )

    user = db.execute(
        select(User).where(func.lower(User.email) == str(email_address).lower())
    ).scalar_one_or_none()
    if not user:
        logger.info(
            "Webhook user not found",
            extra={"email": email_address, "history_id": history_id},
        )
        return {"status": "ignored"}

    crypto = get_crypto(settings)
    enqueue_incremental_sync(
        db,
        settings,
        crypto,
        user.id,
        str(history_id),
    )
    return {"status": "ok"}


def _verify_webhook(request: Request, settings: Settings) -> None:
    auth_header = request.headers.get("Authorization")
    if auth_header:
        token = auth_header.split(" ", 1)[1] if " " in auth_header else ""
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token"
            )
        audience = f"{settings.api_base_url}/webhooks/gmail/push"
        try:
            id_token.verify_oauth2_token(token, GoogleRequest(), audience=audience)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid OIDC token",
            ) from exc
        return

    secret = request.headers.get("X-Webhook-Secret")
    if secret and settings.webhook_secret and secret == settings.webhook_secret:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Webhook verification failed",
    )
