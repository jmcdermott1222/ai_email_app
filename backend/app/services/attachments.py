"""Attachment download and extraction pipeline."""

from __future__ import annotations

import base64
import hashlib
from io import BytesIO

import fitz
from docx import Document
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.crypto import CryptoProvider
from app.models import Email, GoogleOAuthToken
from app.services.gmail_client import GmailClient
from app.services.google_credentials import build_credentials


class AttachmentProcessingError(RuntimeError):
    """Raised when attachment processing fails."""


def download_attachment_bytes(
    db: Session,
    user_id: int,
    gmail_message_id: str,
    gmail_attachment_id: str,
    settings: Settings,
    crypto: CryptoProvider,
) -> bytes:
    token_row = db.execute(
        select(GoogleOAuthToken).where(GoogleOAuthToken.user_id == user_id)
    ).scalar_one_or_none()
    if not token_row:
        raise AttachmentProcessingError("Missing OAuth token row")
    creds = build_credentials(db, token_row, settings, crypto).credentials
    client = GmailClient(credentials=creds)
    response = client.get_attachment(gmail_message_id, gmail_attachment_id)
    data = response.get("data")
    if not data:
        raise AttachmentProcessingError("Attachment data missing")
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def extract_text_from_bytes(mime_type: str | None, content: bytes) -> str:
    if not mime_type:
        raise AttachmentProcessingError("Unknown mime type")
    if mime_type == "application/pdf":
        return extract_text_from_pdf(content)
    if mime_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    }:
        return extract_text_from_docx(content)
    if mime_type.startswith("text/"):
        return extract_text_from_text(content)
    raise AttachmentProcessingError(f"Unsupported mime type: {mime_type}")


def extract_text_from_pdf(content: bytes) -> str:
    with fitz.open(stream=content, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc).strip()


def extract_text_from_docx(content: bytes) -> str:
    doc = Document(BytesIO(content))
    paragraphs = [paragraph.text for paragraph in doc.paragraphs if paragraph.text]
    return "\n".join(paragraphs).strip()


def extract_text_from_text(content: bytes) -> str:
    return content.decode("utf-8", errors="replace").strip()


def process_attachments_for_email(
    db: Session,
    user_id: int,
    email_id: int,
    settings: Settings,
    crypto: CryptoProvider,
) -> dict:
    email = db.get(Email, email_id)
    if not email or email.user_id != user_id:
        raise AttachmentProcessingError("Email not found")

    processed = 0
    failed = 0

    for attachment in email.attachments:
        if attachment.extraction_status == "OK":
            continue
        if not attachment.gmail_attachment_id:
            attachment.extraction_status = "FAILED"
            failed += 1
            continue

        try:
            content = download_attachment_bytes(
                db,
                user_id,
                email.gmail_message_id,
                attachment.gmail_attachment_id,
                settings,
                crypto,
            )
            sha256 = hashlib.sha256(content).hexdigest()
            extracted = extract_text_from_bytes(attachment.mime_type, content)
            attachment.sha256 = sha256
            attachment.extracted_text = extracted
            attachment.extraction_status = "OK"
            processed += 1
        except Exception:
            attachment.extraction_status = "FAILED"
            failed += 1

    db.commit()
    return {"processed": processed, "failed": failed}
