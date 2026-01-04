"""Generate and store per-user writing style profiles."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.crypto import CryptoProvider
from app.models import GoogleOAuthToken, UserPreferences
from app.services.email_parser import parse_message
from app.services.gmail_client import GmailClient
from app.services.google_credentials import build_credentials
from app.services.llm_client import LLMClient
from app.services.llm_schemas import STYLE_PROFILE_SCHEMA, STYLE_PROFILE_SCHEMA_VERSION
from app.services.preferences import default_preferences

PROMPT_VERSION = "v1"
MAX_SAMPLE_EMAILS = 40
MAX_BODY_CHARS = 600
MAX_SUBJECT_CHARS = 200


def build_style_profile(
    db: Session,
    settings: Settings,
    crypto: CryptoProvider,
    user_id: int,
) -> dict:
    """Build and persist a concise writing style profile for a user."""
    token_row = db.execute(
        select(GoogleOAuthToken).where(GoogleOAuthToken.user_id == user_id)
    ).scalar_one_or_none()
    if not token_row:
        raise ValueError("Missing OAuth token row for user")

    creds = build_credentials(db, token_row, settings, crypto).credentials
    client = GmailClient(credentials=creds)

    response = client.list_messages(
        q="in:sent newer_than:180d",
        label_ids=None,
        max_results=200,
    )
    messages = response.get("messages", [])
    samples = []
    for message in messages:
        if len(samples) >= MAX_SAMPLE_EMAILS:
            break
        message_id = message.get("id")
        if not message_id:
            continue
        full_message = client.get_message(message_id, format="full")
        parsed = parse_message(full_message)
        body = (parsed.clean_body_text or "").strip()
        if not body:
            continue
        subject = (parsed.subject or "").strip()[:MAX_SUBJECT_CHARS]
        body = body[:MAX_BODY_CHARS]
        samples.append(f"Subject: {subject}\nBody:\n{body}")

    if not samples:
        raise ValueError("No sent messages available for style profile")

    prompt = _build_prompt(samples)
    llm = LLMClient(settings)
    result = llm.call_structured(
        prompt=prompt,
        json_schema=STYLE_PROFILE_SCHEMA,
        model=settings.openai_model,
        temperature=0.2,
    )

    preferences = db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    ).scalar_one_or_none()
    if not preferences:
        preferences = UserPreferences(
            user_id=user_id,
            preferences=default_preferences(),
        )
        db.add(preferences)
        db.flush()

    pref_data = dict(preferences.preferences or default_preferences())
    pref_data["style_profile"] = {
        "profile": result,
        "model_id": settings.openai_model,
        "prompt_version": PROMPT_VERSION,
        "schema_version": STYLE_PROFILE_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "sample_count": len(samples),
    }
    preferences.preferences = pref_data
    db.commit()
    return pref_data["style_profile"]


def _build_prompt(samples: list[str]) -> str:
    joined = "\n\n---\n\n".join(samples)
    return (
        "You are writing a concise style profile for a user's email replies.\n"
        "Use the samples to infer tone, formality, greeting, signoff, and habits.\n"
        "Return JSON only, following the schema.\n\n"
        f"Samples:\n{joined}\n"
    )
