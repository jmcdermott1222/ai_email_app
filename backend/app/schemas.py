"""Pydantic schemas for API input/output."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr


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
    created_at: datetime
    updated_at: datetime


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


class GoogleIntegrationStatus(APIModel):
    connected: bool
    token_status: str | None = None
    needs_reauth: bool
    last_error: str | None = None
