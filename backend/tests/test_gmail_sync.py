"""Tests for Gmail sync service."""

import base64
from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.crypto import LocalDevCrypto
from app.db import Base
from app.models import Attachment, Email, GoogleOAuthToken, User
from app.services.gmail_sync import full_sync_inbox


class FakeGmailClient:
    def __init__(self, messages):
        self._messages = messages

    def list_messages(self, q=None, label_ids=None, max_results=50):
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
                    {"name": "Subject", "value": "Test"},
                ],
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": body_data}},
                    {
                        "filename": "report.pdf",
                        "mimeType": "application/pdf",
                        "body": {"attachmentId": "att-1", "size": 1234},
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

        attachments = session.execute(select(Attachment)).scalars().all()
        assert len(attachments) == 1
        assert attachments[0].gmail_attachment_id == "att-1"
