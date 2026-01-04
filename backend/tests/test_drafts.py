import base64
from email import message_from_bytes

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.crypto import LocalDevCrypto
from app.db import Base
from app.models import Draft, Email, GoogleOAuthToken, User
from app.services.drafts import build_reply_mime, create_gmail_draft


def _decode_base64url(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def test_build_reply_mime_includes_headers():
    raw = build_reply_mime(
        to_address="alice@example.com",
        cc_addresses=["bob@example.com"],
        subject="Re: Hello",
        body="Thanks for the update.",
        in_reply_to="<msg-123>",
        references="<ref-1>",
    )

    msg = message_from_bytes(_decode_base64url(raw))
    assert msg["To"] == "alice@example.com"
    assert msg["Cc"] == "bob@example.com"
    assert msg["Subject"] == "Re: Hello"
    assert msg["In-Reply-To"] == "<msg-123>"
    assert msg["References"] == "<ref-1>"
    assert "Thanks for the update." in msg.get_payload()


def test_create_gmail_draft_persists_fallbacks(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    crypto = LocalDevCrypto("BB0iMhzIaIMZeMACaGkNykzlCaM3Ndoth7-vBeQiJ4U=")
    settings = Settings(
        google_oauth_client_id="client",
        google_oauth_client_secret="secret",
        encryption_key="unused",
    )

    class DummyResult:
        def __init__(self):
            self.credentials = object()
            self.refreshed = False

    class FakeGmailClient:
        def __init__(self, credentials):
            self.created = []

        def get_message(self, message_id, format="full"):
            return {
                "payload": {
                    "headers": [
                        {"name": "From", "value": "Sender <sender@example.com>"},
                        {"name": "Message-ID", "value": "<msg-1>"},
                    ]
                }
            }

        def create_draft(self, raw_mime_base64url, thread_id=None):
            self.created.append((raw_mime_base64url, thread_id))
            return {"id": "draft-1"}

    monkeypatch.setattr(
        "app.services.drafts.build_credentials",
        lambda *args, **kwargs: DummyResult(),
    )
    monkeypatch.setattr("app.services.drafts.GmailClient", FakeGmailClient)

    with SessionLocal() as session:
        user = User(email="user@example.com", google_sub="sub-1")
        session.add(user)
        session.flush()
        session.add(
            GoogleOAuthToken(user_id=user.id, refresh_token_enc=crypto.encrypt("x"))
        )
        email = Email(
            user_id=user.id,
            gmail_message_id="msg-1",
            gmail_thread_id="thread-1",
            from_email="sender@example.com",
            subject=None,
        )
        session.add(email)
        session.flush()

        draft = Draft(user_id=user.id, email_id=email.id, subject=None, body=None)
        session.add(draft)
        session.commit()

        updated = create_gmail_draft(
            session,
            settings,
            crypto,
            user.id,
            draft.id,
        )

        assert updated.gmail_draft_id == "draft-1"
        assert updated.subject == "Re: (no subject)"
        assert updated.body == ""
