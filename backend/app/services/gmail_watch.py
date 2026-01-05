"""Gmail watch renewal service."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.crypto import CryptoProvider
from app.models import GmailSyncState, GoogleOAuthToken
from app.services.gmail_client import GmailClient
from app.services.google_credentials import build_credentials


def renew_watch(
    db: Session,
    settings: Settings,
    crypto: CryptoProvider,
    user_id: int,
    client: GmailClient | None = None,
) -> dict:
    """Renew Gmail push watch for the user's inbox."""
    if not settings.pubsub_topic:
        raise ValueError("PUBSUB_TOPIC is not configured")

    if client is None:
        token_row = db.execute(
            select(GoogleOAuthToken).where(GoogleOAuthToken.user_id == user_id)
        ).scalar_one_or_none()
        if not token_row:
            raise ValueError("Missing OAuth token row for user")
        creds = build_credentials(db, token_row, settings, crypto).credentials
        client = GmailClient(credentials=creds)

    response = client.watch(topic_name=settings.pubsub_topic, label_ids=["INBOX"])
    history_id = response.get("historyId")
    expiration = response.get("expiration")
    expiration_dt = None
    if expiration:
        expiration_dt = datetime.fromtimestamp(int(expiration) / 1000, tz=UTC)

    sync_state = db.execute(
        select(GmailSyncState).where(GmailSyncState.user_id == user_id)
    ).scalar_one_or_none()
    if not sync_state:
        sync_state = GmailSyncState(user_id=user_id)
        db.add(sync_state)
    if history_id:
        sync_state.history_id = str(history_id)
    if expiration_dt:
        sync_state.watch_expiration = expiration_dt
    db.commit()
    return response
