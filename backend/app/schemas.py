"""Pydantic schemas for API input/output."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class APIModel(BaseModel):
    """Base Pydantic model with ORM support."""

    model_config = ConfigDict(from_attributes=True)


class UserBase(APIModel):
    email: EmailStr


class UserCreate(UserBase):
    google_sub: str | None = None


class UserRead(UserBase):
    id: int
    google_sub: str | None = None
    created_at: datetime
    updated_at: datetime


class EmailRead(APIModel):
    id: int
    user_id: int
    gmail_message_id: str
    gmail_thread_id: str | None = None
    internal_date_ts: datetime | None = None
    subject: str | None = None
    snippet: str | None = None
    from_email: str | None = None
    label_ids: list[str] | None = None
    importance_label: str | None = None
    needs_response: bool | None = None
    why_important: str | None = None
    created_at: datetime
    updated_at: datetime


class EmailDetail(APIModel):
    id: int
    user_id: int
    gmail_message_id: str
    gmail_thread_id: str | None = None
    internal_date_ts: datetime | None = None
    subject: str | None = None
    snippet: str | None = None
    from_email: str | None = None
    to_emails: list[str] | None = None
    label_ids: list[str] | None = None
    ingest_status: str | None = None
    ingest_error: str | None = None
    clean_body_text: str | None = None
    attachments: list["AttachmentRead"] = []
    importance_label: str | None = None
    needs_response: bool | None = None
    why_important: str | None = None
    summary_bullets: list[str] = []
    created_at: datetime
    updated_at: datetime


class AttachmentRead(APIModel):
    id: int
    filename: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    gmail_attachment_id: str | None = None
    extraction_status: str | None = None


class EmailTriageResponse(APIModel):
    importance_label: str | None = None
    needs_response: bool
    summary_bullets: list[str]
    why_important: str | None = None


class EmailFeedbackRequest(APIModel):
    feedback_label: Literal["IMPORTANT", "NOT_IMPORTANT", "SPAM", "NEWSLETTER_OK"]
    reason: str | None = None
    always_ignore_sender: bool | None = None
    always_ignore_keyword: str | None = None


EmailDetail.model_rebuild()


class EmailTriageRead(APIModel):
    id: int
    email_id: int
    importance_label: str | None = None
    needs_response: bool
    summary: str | None = None
    reasoning: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class DraftRead(APIModel):
    id: int
    email_id: int
    subject: str | None = None
    body: str | None = None
    status: str | None = None
    gmail_draft_id: str | None = None
    created_at: datetime
    updated_at: datetime


class UserPreferencesRead(APIModel):
    id: int
    user_id: int
    preferences: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class WorkingHours(APIModel):
    days: list[str]
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    lunch_start: str = Field(pattern=r"^\d{2}:\d{2}$")
    lunch_end: str = Field(pattern=r"^\d{2}:\d{2}$")


class Preferences(APIModel):
    digest_time_local: str = Field(pattern=r"^\d{2}:\d{2}$")
    vip_alerts_enabled: bool
    working_hours: WorkingHours
    meeting_default_duration_min: int
    automation_level: Literal[
        "SUGGEST_ONLY", "AUTO_LABEL", "AUTO_ARCHIVE", "AUTO_TRASH"
    ]


class PreferencesUpdate(APIModel):
    digest_time_local: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    vip_alerts_enabled: bool | None = None
    working_hours: WorkingHours | None = None
    meeting_default_duration_min: int | None = None
    automation_level: (
        Literal["SUGGEST_ONLY", "AUTO_LABEL", "AUTO_ARCHIVE", "AUTO_TRASH"] | None
    ) = None


class GoogleIntegrationStatus(APIModel):
    connected: bool
    token_status: str | None = None
    needs_reauth: bool
    last_error: str | None = None
