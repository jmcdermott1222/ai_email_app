"""Tests for Gmail sync service."""

import base64
from datetime import UTC, datetime

import httplib2
from googleapiclient.errors import HttpError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.crypto import LocalDevCrypto
from app.db import Base
from app.models import Attachment, Email, GmailSyncState, GoogleOAuthToken, User
from app.services.gmail_sync import SyncResult, full_sync_inbox, incremental_sync


class FakeGmailClient:
    def __init__(self, messages):
        self._messages = messages

    def list_messages(self, q=None, label_ids=None, max_results=50, page_token=None):
        return {
            "messages": [{"id": message_id} for message_id in self._messages.keys()]
        }

    def get_message(self, message_id, format="full"):
        return self._messages[message_id]


def test_full_sync_inbox_idempotent():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    crypto = LocalDevCrypto("BB0iMhzIaIMZeMACaGkNykzlCaM3Ndoth7-vBeQiJ4U=")
    settings = Settings(
        google_oauth_client_id="client",
        google_oauth_client_secret="secret",
        encryption_key="unused",
    )

    with SessionLocal() as session:
        user = User(email="user@example.com", google_sub="sub-1")
        session.add(user)
        session.flush()
        token = GoogleOAuthToken(user_id=user.id, refresh_token_enc=crypto.encrypt("x"))
        session.add(token)
        session.commit()

        body_text = "Hello there\n\nThanks,\nAlice"
        body_data = base64.urlsafe_b64encode(body_text.encode("utf-8")).decode("utf-8")
        message_payload = {
            "id": "msg-1",
            "threadId": "thread-1",
            "labelIds": ["INBOX"],
            "snippet": "Hello there",
            "internalDate": str(
                int(datetime(2024, 1, 1, tzinfo=UTC).timestamp() * 1000)
            ),
            "payload": {
                "mimeType": "multipart/mixed",
                "headers": [
                    {"name": "From", "value": "Alice <alice@example.com>"},
                    {"name": "To", "value": "Bob <bob@example.com>"},
                    {"name": "Cc", "value": "Carol <carol@example.com>"},
                    {"name": "Subject", "value": "Test"},
                ],
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": body_data}},
                    {
                        "filename": "report.pdf",
                        "mimeType": "application/pdf",
                        "body": {"attachmentId": "att-1", "size": 1234},
                    },
                    {
                        "filename": "inline.txt",
                        "mimeType": "text/plain",
                        "body": {"size": 10},
                    },
                ],
            },
        }

        client = FakeGmailClient({"msg-1": message_payload})
        full_sync_inbox(session, user.id, settings, crypto, client=client)
        full_sync_inbox(session, user.id, settings, crypto, client=client)

        emails = session.execute(select(Email)).scalars().all()
        assert len(emails) == 1
        assert emails[0].gmail_message_id == "msg-1"
        assert emails[0].clean_body_text.startswith("Hello there")
        assert emails[0].cc_emails == ["carol@example.com"]

        attachments = session.execute(select(Attachment)).scalars().all()
        assert len(attachments) == 1
        assert attachments[0].gmail_attachment_id == "att-1"


def test_full_sync_inbox_paginates():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    crypto = LocalDevCrypto("BB0iMhzIaIMZeMACaGkNykzlCaM3Ndoth7-vBeQiJ4U=")
    settings = Settings(
        google_oauth_client_id="client",
        google_oauth_client_secret="secret",
        encryption_key="unused",
    )

    class PagingGmailClient:
        def __init__(self, messages):
            self._messages = messages

        def list_messages(
            self, q=None, label_ids=None, max_results=50, page_token=None
        ):
            if page_token is None:
                return {"messages": [{"id": "msg-1"}], "nextPageToken": "page-2"}
            if page_token == "page-2":
                return {"messages": [{"id": "msg-2"}]}
            return {"messages": []}

        def get_message(self, message_id, format="full"):
            return self._messages[message_id]

    base_payload = {
        "threadId": "thread-1",
        "labelIds": ["INBOX"],
        "snippet": "Hello there",
        "internalDate": str(int(datetime(2024, 1, 1, tzinfo=UTC).timestamp() * 1000)),
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "Alice <alice@example.com>"},
                {"name": "To", "value": "Bob <bob@example.com>"},
                {"name": "Subject", "value": "Test"},
            ],
            "body": {"data": base64.urlsafe_b64encode(b"Hello").decode("utf-8")},
        },
    }

    with SessionLocal() as session:
        user = User(email="user@example.com", google_sub="sub-1")
        session.add(user)
        session.flush()
        token = GoogleOAuthToken(user_id=user.id, refresh_token_enc=crypto.encrypt("x"))
        session.add(token)
        session.commit()

        messages = {
            "msg-1": {"id": "msg-1", **base_payload},
            "msg-2": {"id": "msg-2", **base_payload},
        }
        client = PagingGmailClient(messages)
        full_sync_inbox(session, user.id, settings, crypto, client=client)

        emails = session.execute(select(Email)).scalars().all()
        assert len(emails) == 2


def test_incremental_sync_ingests_history_messages():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    crypto = LocalDevCrypto("BB0iMhzIaIMZeMACaGkNykzlCaM3Ndoth7-vBeQiJ4U=")
    settings = Settings(
        google_oauth_client_id="client",
        google_oauth_client_secret="secret",
        encryption_key="unused",
    )

    body_text = "Hi there"
    body_data = base64.urlsafe_b64encode(body_text.encode("utf-8")).decode("utf-8")
    message_payload = {
        "id": "msg-99",
        "threadId": "thread-99",
        "labelIds": ["INBOX"],
        "snippet": "Hi there",
        "internalDate": str(int(datetime(2024, 1, 1, tzinfo=UTC).timestamp() * 1000)),
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "Alice <alice@example.com>"},
                {"name": "To", "value": "Bob <bob@example.com>"},
                {"name": "Subject", "value": "Hello"},
            ],
            "body": {"data": body_data},
        },
    }

    class HistoryGmailClient:
        def list_history(self, start_history_id, history_types=None, page_token=None):
            return {
                "historyId": "200",
                "history": [
                    {
                        "messagesAdded": [{"message": {"id": "msg-99"}}],
                    }
                ],
            }

        def get_message(self, message_id, format="full"):
            return message_payload

    with SessionLocal() as session:
        user = User(email="user@example.com", google_sub="sub-1")
        session.add(user)
        session.flush()
        token = GoogleOAuthToken(user_id=user.id, refresh_token_enc=crypto.encrypt("x"))
        session.add(token)
        session.add(GmailSyncState(user_id=user.id, history_id="100"))
        session.commit()

        result = incremental_sync(
            session,
            user.id,
            settings,
            crypto,
            history_id="200",
            client=HistoryGmailClient(),
        )

        assert result.fetched == 1
        emails = session.execute(select(Email)).scalars().all()
        assert len(emails) == 1
        sync_state = session.execute(
            select(GmailSyncState).where(GmailSyncState.user_id == user.id)
        ).scalar_one()
        assert sync_state.history_id == "200"


def test_incremental_sync_fallback_on_invalid_history(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    crypto = LocalDevCrypto("BB0iMhzIaIMZeMACaGkNykzlCaM3Ndoth7-vBeQiJ4U=")
    settings = Settings(
        google_oauth_client_id="client",
        google_oauth_client_secret="secret",
        encryption_key="unused",
    )

    class ErrorGmailClient:
        def list_history(self, start_history_id, history_types=None, page_token=None):
            raise HttpError(httplib2.Response({"status": 404}), b"Not Found")

    called = {"fallback": False}

    def fake_full_sync(*args, **kwargs):
        called["fallback"] = True
        return SyncResult(fetched=0, upserted=0, errors=0)

    monkeypatch.setattr("app.services.gmail_sync.full_sync_inbox", fake_full_sync)

    with SessionLocal() as session:
        user = User(email="user@example.com", google_sub="sub-1")
        session.add(user)
        session.flush()
        token = GoogleOAuthToken(user_id=user.id, refresh_token_enc=crypto.encrypt("x"))
        session.add(token)
        session.add(GmailSyncState(user_id=user.id, history_id="100"))
        session.commit()

        incremental_sync(
            session,
            user.id,
            settings,
            crypto,
            history_id="222",
            client=ErrorGmailClient(),
        )

        assert called["fallback"] is True
        sync_state = session.execute(
            select(GmailSyncState).where(GmailSyncState.user_id == user.id)
        ).scalar_one()
        assert sync_state.history_id == "222"
