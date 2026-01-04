"""Polling-based Gmail full sync service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.config import Settings
from app.crypto import CryptoProvider
from app.models import Email, GoogleOAuthToken
from app.services.gmail_client import GmailClient
from app.services.google_credentials import build_credentials


@dataclass(frozen=True)
class SyncResult:
    fetched: int
    upserted: int
    errors: int


def _header_value(headers: list[dict], name: str) -> str | None:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value")
    return None


def _parse_recipients(raw_value: str | None) -> list[str] | None:
    if not raw_value:
        return None
    return [value.strip() for value in raw_value.split(",") if value.strip()]


def _parse_internal_date(internal_date_ms: str | None) -> datetime | None:
    if not internal_date_ms:
        return None
    try:
        millis = int(internal_date_ms)
    except ValueError:
        return None
    return datetime.fromtimestamp(millis / 1000.0, tz=UTC)


def full_sync_inbox(
    db: Session,
    user_id: int,
    settings: Settings,
    crypto: CryptoProvider,
    days: int = 14,
    client: GmailClient | None = None,
) -> SyncResult:
    """Fetch recent inbox messages and upsert them into the database."""
    if client is None:
        token_row = db.execute(
            select(GoogleOAuthToken).where(GoogleOAuthToken.user_id == user_id)
        ).scalar_one_or_none()
        if not token_row:
            raise ValueError("Missing OAuth token row for user")
        creds = build_credentials(db, token_row, settings, crypto).credentials
        client = GmailClient(credentials=creds)

    query = f"newer_than:{days}d"
    response = client.list_messages(q=query, label_ids=["INBOX"], max_results=500)
    messages = response.get("messages", [])
    fetched = len(messages)
    upserted = 0
    errors = 0

    def upsert_email(values: dict, error: bool = False) -> None:
        dialect = db.bind.dialect.name if db.bind else "postgresql"
        if dialect == "sqlite":
            insert_stmt = sqlite_insert(Email).values(**values)
        else:
            insert_stmt = pg_insert(Email).values(**values)
        if error:
            set_fields = {
                "ingest_status": "ERROR",
                "ingest_error": values.get("ingest_error"),
                "updated_at": datetime.now(UTC),
            }
        else:
            set_fields = {
                "gmail_thread_id": insert_stmt.excluded.gmail_thread_id,
                "internal_date_ts": insert_stmt.excluded.internal_date_ts,
                "subject": insert_stmt.excluded.subject,
                "snippet": insert_stmt.excluded.snippet,
                "from_email": insert_stmt.excluded.from_email,
                "to_emails": insert_stmt.excluded.to_emails,
                "label_ids": insert_stmt.excluded.label_ids,
                "ingest_status": insert_stmt.excluded.ingest_status,
                "ingest_error": insert_stmt.excluded.ingest_error,
                "updated_at": datetime.now(UTC),
            }
        db.execute(
            insert_stmt.on_conflict_do_update(
                index_elements=["user_id", "gmail_message_id"],
                set_=set_fields,
            )
        )

    for message in messages:
        message_id = message.get("id")
        if not message_id:
            continue
        try:
            full_message = client.get_message(message_id, format="full")
            payload = full_message.get("payload", {})
            headers = payload.get("headers", [])
            from_value = _header_value(headers, "From")
            to_value = _header_value(headers, "To")
            subject = _header_value(headers, "Subject")
            snippet = full_message.get("snippet")
            internal_date = _parse_internal_date(full_message.get("internalDate"))
            thread_id = full_message.get("threadId")
            label_ids = full_message.get("labelIds", [])

            upsert_email(
                {
                    "user_id": user_id,
                    "gmail_message_id": message_id,
                    "gmail_thread_id": thread_id,
                    "internal_date_ts": internal_date,
                    "subject": subject,
                    "snippet": snippet,
                    "from_email": from_value,
                    "to_emails": _parse_recipients(to_value),
                    "label_ids": label_ids,
                    "raw_payload": None,
                    "ingest_status": "INGESTED",
                    "ingest_error": None,
                }
            )
            upserted += 1
        except Exception as exc:
            errors += 1
            upsert_email(
                {
                    "user_id": user_id,
                    "gmail_message_id": message_id,
                    "ingest_status": "ERROR",
                    "ingest_error": str(exc),
                },
                error=True,
            )

    db.commit()
    return SyncResult(fetched=fetched, upserted=upserted, errors=errors)
