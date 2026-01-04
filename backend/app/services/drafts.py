"""Draft reply generation and Gmail draft creation."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import getaddresses

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.crypto import CryptoProvider
from app.models import Draft, Email, EmailTriage, GoogleOAuthToken, UserPreferences
from app.services.email_parser import parse_message
from app.services.gmail_client import GmailClient
from app.services.google_credentials import build_credentials
from app.services.llm_client import LLMClient
from app.services.llm_schemas import DRAFT_PROPOSAL_SCHEMA, DRAFT_PROPOSAL_SCHEMA_VERSION
from app.services.style_profile import build_style_profile

PROMPT_VERSION = "v1"


def propose_draft(
    db: Session,
    settings: Settings,
    crypto: CryptoProvider,
    user_id: int,
    email_id: int,
) -> Draft:
    """Generate a draft proposal for an email."""
    email = db.execute(
        select(Email).where(Email.id == email_id, Email.user_id == user_id)
    ).scalar_one_or_none()
    if not email:
        raise ValueError("Email not found")

    triage = db.execute(
        select(EmailTriage).where(
            EmailTriage.email_id == email.id, EmailTriage.user_id == user_id
        )
    ).scalar_one_or_none()
    if not triage or not triage.needs_response:
        raise ValueError("Email does not require a response")

    preferences = db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    ).scalar_one_or_none()
    pref_data = preferences.preferences if preferences else {}
    style_profile = pref_data.get("style_profile") if pref_data else None
    if not style_profile or not style_profile.get("profile"):
        style_profile = build_style_profile(db, settings, crypto, user_id)

    token_row = db.execute(
        select(GoogleOAuthToken).where(GoogleOAuthToken.user_id == user_id)
    ).scalar_one_or_none()
    if not token_row:
        raise ValueError("Missing OAuth token row for user")

    creds = build_credentials(db, token_row, settings, crypto).credentials
    client = GmailClient(credentials=creds)
    thread_context = _build_thread_context(client, email)

    prompt = _build_prompt(
        email=email,
        style_profile=style_profile.get("profile", {}),
        thread_context=thread_context,
    )
    llm = LLMClient(settings)
    result = llm.call_structured(
        prompt=prompt,
        json_schema=DRAFT_PROPOSAL_SCHEMA,
        model=settings.openai_model,
        temperature=0.3,
    )

    draft = _find_latest_editable_draft(db, user_id, email.id)
    if not draft:
        draft = Draft(user_id=user_id, email_id=email.id)
        db.add(draft)

    draft.subject = result.get("subject")
    draft.body = result.get("body")
    draft.status = "PROPOSED"
    draft.model_id = settings.openai_model
    draft.prompt_version = PROMPT_VERSION
    draft.schema_version = DRAFT_PROPOSAL_SCHEMA_VERSION
    draft.updated_at = datetime.now(UTC)
    db.commit()
    return draft


def create_gmail_draft(
    db: Session,
    settings: Settings,
    crypto: CryptoProvider,
    user_id: int,
    draft_id: int,
    subject_override: str | None = None,
    body_override: str | None = None,
) -> Draft:
    """Create a Gmail draft from a stored proposal."""
    draft = db.execute(
        select(Draft).where(Draft.id == draft_id, Draft.user_id == user_id)
    ).scalar_one_or_none()
    if not draft:
        raise ValueError("Draft not found")

    email = db.execute(
        select(Email).where(Email.id == draft.email_id, Email.user_id == user_id)
    ).scalar_one_or_none()
    if not email:
        raise ValueError("Email not found")

    if subject_override is not None:
        draft.subject = subject_override
    if body_override is not None:
        draft.body = body_override

    token_row = db.execute(
        select(GoogleOAuthToken).where(GoogleOAuthToken.user_id == user_id)
    ).scalar_one_or_none()
    if not token_row:
        raise ValueError("Missing OAuth token row for user")

    creds = build_credentials(db, token_row, settings, crypto).credentials
    client = GmailClient(credentials=creds)

    reply_headers = _fetch_reply_headers(client, email.gmail_message_id)
    to_address = reply_headers.get("to_address") or email.from_email
    if not to_address:
        raise ValueError("Missing reply address for draft")

    subject = draft.subject or _default_reply_subject(email.subject)
    body = draft.body or ""
    raw_mime = build_reply_mime(
        to_address=to_address,
        cc_addresses=reply_headers.get("cc_addresses"),
        subject=subject,
        body=body,
        in_reply_to=reply_headers.get("in_reply_to"),
        references=reply_headers.get("references"),
    )

    response = client.create_draft(raw_mime, thread_id=email.gmail_thread_id)
    draft.gmail_draft_id = response.get("id")
    draft.status = "CREATED"
    draft.updated_at = datetime.now(UTC)
    db.commit()
    return draft


def build_reply_mime(
    to_address: str,
    cc_addresses: list[str] | None,
    subject: str,
    body: str,
    in_reply_to: str | None,
    references: str | None,
) -> str:
    """Build a base64url-encoded RFC2822 reply payload."""
    if not to_address:
        raise ValueError("Missing To address")
    msg = EmailMessage()
    msg["To"] = to_address
    if cc_addresses:
        msg["Cc"] = ", ".join(cc_addresses)
    if subject:
        msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references
    msg.set_content(body or "")
    return _base64url_encode(msg.as_bytes())


def _base64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _build_thread_context(client: GmailClient, email: Email) -> str:
    if not email.gmail_thread_id:
        return _format_single_message(email.subject, email.from_email, email.clean_body_text)

    try:
        thread = client.get_thread(email.gmail_thread_id, format="full")
    except Exception:
        return _format_single_message(email.subject, email.from_email, email.clean_body_text)

    messages = thread.get("messages", []) or []
    if not messages:
        return _format_single_message(email.subject, email.from_email, email.clean_body_text)

    def parse_internal_date(message: dict) -> int:
        try:
            return int(message.get("internalDate", "0"))
        except ValueError:
            return 0

    sorted_messages = sorted(messages, key=parse_internal_date)[-2:]
    snippets = []
    for message in sorted_messages:
        parsed = parse_message(message)
        snippets.append(
            _format_single_message(
                parsed.subject,
                parsed.from_email,
                parsed.clean_body_text,
            )
        )
    return "\n\n".join(snippets)


def _format_single_message(
    subject: str | None,
    sender: str | None,
    body: str | None,
) -> str:
    safe_subject = subject or "(no subject)"
    safe_sender = sender or "unknown sender"
    safe_body = (body or "").strip()
    return f"Subject: {safe_subject}\nFrom: {safe_sender}\nBody:\n{safe_body}"


def _build_prompt(email: Email, style_profile: dict, thread_context: str) -> str:
    return (
        "You are a helpful email assistant. Draft a reply in the user's style.\n"
        "Return JSON only, following the schema. Keep the reply concise and polite.\n\n"
        f"Style profile:\n{style_profile}\n\n"
        f"Email subject: {email.subject or ''}\n"
        f"From: {email.from_email or ''}\n"
        f"Body:\n{email.clean_body_text or email.snippet or ''}\n\n"
        f"Thread context (most recent messages):\n{thread_context}\n"
    )


def _fetch_reply_headers(client: GmailClient, gmail_message_id: str) -> dict:
    message = client.get_message(gmail_message_id, format="full")
    payload = message.get("payload", {}) or {}
    headers = payload.get("headers", []) or []
    header_map = {
        (header.get("name") or "").lower(): header.get("value") or ""
        for header in headers
    }

    reply_to = header_map.get("reply-to") or header_map.get("from")
    to_address = _first_email(reply_to)
    cc_addresses = _parse_addresses(header_map.get("cc"))
    in_reply_to = header_map.get("message-id")
    references = header_map.get("references")
    if in_reply_to and references:
        if in_reply_to not in references:
            references = f"{references} {in_reply_to}"
    elif in_reply_to and not references:
        references = in_reply_to

    return {
        "to_address": to_address,
        "cc_addresses": cc_addresses,
        "in_reply_to": in_reply_to,
        "references": references,
    }


def _first_email(raw_value: str | None) -> str | None:
    if not raw_value:
        return None
    addresses = getaddresses([raw_value])
    for _, email in addresses:
        if email:
            return email
    return None


def _parse_addresses(raw_value: str | None) -> list[str] | None:
    if not raw_value:
        return None
    addresses = getaddresses([raw_value])
    emails = [email for _, email in addresses if email]
    return emails or None


def _default_reply_subject(subject: str | None) -> str:
    if not subject:
        return "Re: (no subject)"
    lowered = subject.lower()
    if lowered.startswith("re:"):
        return subject
    return f"Re: {subject}"


def _find_latest_editable_draft(
    db: Session, user_id: int, email_id: int
) -> Draft | None:
    draft = (
        db.execute(
            select(Draft)
            .where(Draft.user_id == user_id, Draft.email_id == email_id)
            .order_by(Draft.created_at.desc())
        )
        .scalars()
        .first()
    )
    if draft and draft.gmail_draft_id:
        return None
    return draft
