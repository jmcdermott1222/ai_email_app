"""SQLAlchemy ORM models for core tables."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base

JSONBType = JSONB().with_variant(JSON(), "sqlite")


class TimestampMixin:
    """Mixin that adds created/updated timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(Base, TimestampMixin):
    """Application user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    google_sub: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )

    oauth_tokens: Mapped[GoogleOAuthToken] = relationship(
        back_populates="user", uselist=False
    )
    sync_state: Mapped[GmailSyncState] = relationship(
        back_populates="user", uselist=False
    )
    emails: Mapped[list[Email]] = relationship(back_populates="user")
    preferences: Mapped[UserPreferences] = relationship(
        back_populates="user", uselist=False
    )
    gmail_labels: Mapped[list[UserGmailLabel]] = relationship(back_populates="user")


class GoogleOAuthToken(Base, TimestampMixin):
    """Encrypted OAuth tokens for Google APIs."""

    __tablename__ = "google_oauth_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    access_token_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    refresh_token_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    token_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expiry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scopes: Mapped[list[str] | None] = mapped_column(JSONBType, nullable=True)
    token_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="oauth_tokens")


class GmailSyncState(Base, TimestampMixin):
    """Per-user Gmail sync bookkeeping."""

    __tablename__ = "gmail_sync_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    history_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    watch_expiration: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_full_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="sync_state")


class Email(Base, TimestampMixin):
    """Gmail message metadata."""

    __tablename__ = "emails"
    __table_args__ = (
        Index("ix_emails_user_internal_date", "user_id", "internal_date_ts"),
        Index("ux_emails_user_message", "user_id", "gmail_message_id", unique=True),
        Index("ix_emails_user_thread", "user_id", "gmail_thread_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    gmail_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    gmail_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    internal_date_ts: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    to_emails: Mapped[list[str] | None] = mapped_column(JSONBType, nullable=True)
    label_ids: Mapped[list[str] | None] = mapped_column(JSONBType, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    ingest_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ingest_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    clean_body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    snooze_until_ts: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_snoozed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="emails")
    attachments: Mapped[list[Attachment]] = relationship(back_populates="email")
    triage: Mapped[EmailTriage] = relationship(back_populates="email", uselist=False)
    drafts: Mapped[list[Draft]] = relationship(back_populates="email")
    calendar_candidates: Mapped[list[CalendarCandidate]] = relationship(
        back_populates="email"
    )


class Attachment(Base, TimestampMixin):
    """Email attachment metadata and extracted text."""

    __tablename__ = "attachments"
    __table_args__ = (
        Index("ix_attachments_email_id", "email_id"),
        UniqueConstraint("email_id", "gmail_attachment_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails.id"), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gmail_attachment_id: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    email: Mapped[Email] = relationship(back_populates="attachments")


class EmailTriage(Base, TimestampMixin):
    """LLM triage results for an email."""

    __tablename__ = "email_triage"
    __table_args__ = (
        Index("ix_email_triage_importance_needs", "importance_label", "needs_response"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails.id"), nullable=False)
    importance_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    needs_response: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasoning: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    schema_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    email: Mapped[Email] = relationship(back_populates="triage")


class Draft(Base, TimestampMixin):
    """Draft replies for emails."""

    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails.id"), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gmail_draft_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    schema_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    email: Mapped[Email] = relationship(back_populates="drafts")


class CalendarCandidate(Base, TimestampMixin):
    """Proposed calendar candidates extracted from emails."""

    __tablename__ = "calendar_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails.id"), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    schema_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    email: Mapped[Email] = relationship(back_populates="calendar_candidates")
    events_created: Mapped[list[CalendarEventCreated]] = relationship(
        back_populates="candidate"
    )


class CalendarEventCreated(Base, TimestampMixin):
    """Calendar events created from candidates."""

    __tablename__ = "calendar_events_created"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    calendar_candidate_id: Mapped[int] = mapped_column(
        ForeignKey("calendar_candidates.id"), nullable=False
    )
    event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    candidate: Mapped[CalendarCandidate] = relationship(back_populates="events_created")


class UserPreferences(Base, TimestampMixin):
    """Per-user preferences and settings."""

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, unique=True
    )
    preferences: Mapped[dict | None] = mapped_column(JSONBType, nullable=True)

    user: Mapped[User] = relationship(back_populates="preferences")


class UserGmailLabel(Base, TimestampMixin):
    """Per-user Gmail label IDs."""

    __tablename__ = "user_gmail_labels"
    __table_args__ = (UniqueConstraint("user_id", "label_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    label_name: Mapped[str] = mapped_column(String(255), nullable=False)
    label_id: Mapped[str] = mapped_column(String(255), nullable=False)

    user: Mapped[User] = relationship(back_populates="gmail_labels")


class EmailFeedback(Base, TimestampMixin):
    """User feedback on emails."""

    __tablename__ = "email_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails.id"), nullable=False)
    feedback_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditLog(Base, TimestampMixin):
    """Audit log for user actions."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(
        "metadata", JSONBType, nullable=True
    )
