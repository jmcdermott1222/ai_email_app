"""Tests for Google OAuth helpers."""

from cryptography.fernet import Fernet
from google.auth.exceptions import RefreshError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.crypto import LocalDevCrypto
from app.db import Base
from app.models import GoogleOAuthToken, User
from app.services.google_oauth import (
    TOKEN_STATUS_NEEDS_REAUTH,
    refresh_access_token,
)


def test_refresh_access_token_marks_needs_reauth(monkeypatch) -> None:
    key = Fernet.generate_key().decode("utf-8")
    settings = Settings(
        google_oauth_client_id="client-id",
        google_oauth_client_secret="client-secret",
        encryption_key=key,
    )
    crypto = LocalDevCrypto(key)

    engine = create_engine("sqlite+pysqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    def _raise_invalid_grant(self, request):
        raise RefreshError("invalid_grant: Bad Request")

    monkeypatch.setattr(
        "app.services.google_oauth.google_credentials.Credentials.refresh",
        _raise_invalid_grant,
    )

    with SessionLocal() as session:
        user = User(email="user@example.com", google_sub="sub-123")
        session.add(user)
        session.flush()

        token_row = GoogleOAuthToken(
            user_id=user.id,
            refresh_token_enc=crypto.encrypt("bad-token"),
        )
        session.add(token_row)
        session.commit()

        result = refresh_access_token(session, token_row, crypto, settings)

        assert result.needs_reauth is True
        assert token_row.token_status == TOKEN_STATUS_NEEDS_REAUTH
        assert token_row.last_error is not None
