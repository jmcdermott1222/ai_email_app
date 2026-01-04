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
from app.models import Attachment, Email, GoogleOAuthToken
from app.services.email_parser import parse_message
from app.services.gmail_client import GmailClient
from app.services.google_credentials import build_credentials


@dataclass(frozen=True)
class SyncResult:
    fetched: int
    upserted: int
    errors: int


def _parse_internal_date(internal_date_ms: str | None) -> datetime | None:
    if not internal_date_ms:
        return None
    try:
        millis = int(internal_date_ms)
    except ValueError:
        return None
    return datetime.fromtimestamp(millis / 1000.0, tz=UTC)


def _upsert_attachment(db: Session, values: dict) -> None:
    dialect = db.bind.dialect.name if db.bind else "postgresql"
    if dialect == "sqlite":
        insert_stmt = sqlite_insert(Attachment).values(**values)
    else:
        insert_stmt = pg_insert(Attachment).values(**values)
    db.execute(
        insert_stmt.on_conflict_do_update(
            index_elements=["email_id", "gmail_attachment_id"],
            set_={
                "filename": insert_stmt.excluded.filename,
                "mime_type": insert_stmt.excluded.mime_type,
                "size_bytes": insert_stmt.excluded.size_bytes,
                "extraction_status": insert_stmt.excluded.extraction_status,
                "updated_at": datetime.now(UTC),
            },
        )
    )


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
    messages = []
    page_token = None
    while True:
        response = client.list_messages(
            q=query,
            label_ids=["INBOX"],
            max_results=500,
            page_token=page_token,
        )
        messages.extend(response.get("messages", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
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
                "cc_emails": insert_stmt.excluded.cc_emails,
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
            parsed = parse_message(full_message)
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
                    "subject": parsed.subject,
                    "snippet": snippet,
                    "from_email": parsed.from_email,
                    "to_emails": parsed.to_emails,
                    "cc_emails": parsed.cc_emails,
                    "label_ids": label_ids,
                    "raw_payload": None,
                    "ingest_status": "INGESTED",
                    "ingest_error": None,
                    "clean_body_text": parsed.clean_body_text,
                }
            )
            upserted += 1
            email_row = db.execute(
                select(Email).where(
                    Email.user_id == user_id,
                    Email.gmail_message_id == message_id,
                )
            ).scalar_one_or_none()
            if email_row:
                for attachment in parsed.attachments:
                    if not attachment.attachment_id:
                        continue
                    _upsert_attachment(
                        db,
                        {
                            "user_id": user_id,
                            "email_id": email_row.id,
                            "gmail_attachment_id": attachment.attachment_id,
                            "filename": attachment.filename,
                            "mime_type": attachment.mime_type,
                            "size_bytes": attachment.size_estimate,
                            "extraction_status": "NOT_PROCESSED",
                        },
                    )
            db.commit()
        except Exception as exc:
            db.rollback()
            errors += 1
            try:
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
            except Exception:
                db.rollback()

    return SyncResult(fetched=fetched, upserted=upserted, errors=errors)
