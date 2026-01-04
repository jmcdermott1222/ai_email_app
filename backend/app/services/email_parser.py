"""Gmail message parsing utilities."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import getaddresses, parsedate_to_datetime

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class AttachmentMeta:
    filename: str | None
    mime_type: str | None
    size_estimate: int | None
    attachment_id: str | None


@dataclass(frozen=True)
class ParsedEmail:
    clean_body_text: str
    subject: str | None
    from_name: str | None
    from_email: str | None
    to_emails: list[str] | None
    cc_emails: list[str] | None
    sent_at: datetime | None
    received_at: datetime | None
    headers: dict[str, str]
    attachments: list[AttachmentMeta]


def parse_message(message: dict) -> ParsedEmail:
    """Parse a Gmail message resource (format=full)."""
    payload = message.get("payload", {}) or {}
    headers = payload.get("headers", []) or []
    header_map = {
        h.get("name", ""): h.get("value", "") for h in headers if h.get("name")
    }

    subject = header_map.get("Subject")
    from_value = header_map.get("From")
    to_value = header_map.get("To")
    cc_value = header_map.get("Cc")
    date_value = header_map.get("Date")

    from_name, from_email = _parse_from(from_value)
    to_emails = _parse_address_list(to_value)
    cc_emails = _parse_address_list(cc_value)

    sent_at = _parse_date(date_value)
    received_at = _parse_internal_date(message.get("internalDate"))

    parts = list(_walk_parts(payload))
    body_text = _extract_body_text(parts)
    clean_body_text = _clean_text(body_text)

    attachments = _extract_attachments(parts)

    return ParsedEmail(
        clean_body_text=clean_body_text,
        subject=subject,
        from_name=from_name,
        from_email=from_email,
        to_emails=to_emails,
        cc_emails=cc_emails,
        sent_at=sent_at,
        received_at=received_at,
        headers={key: value for key, value in header_map.items() if key},
        attachments=attachments,
    )


def _walk_parts(payload: dict):
    yield payload
    for part in payload.get("parts", []) or []:
        yield from _walk_parts(part)


def _extract_body_text(parts: list[dict]) -> str:
    plain_chunks = []
    html_chunks = []
    for part in parts:
        mime_type = part.get("mimeType", "")
        body = part.get("body", {}) or {}
        data = body.get("data")
        if not data:
            continue
        decoded = _decode_base64url(data)
        if mime_type == "text/plain":
            plain_chunks.append(decoded)
        elif mime_type == "text/html":
            html_chunks.append(decoded)

    if plain_chunks:
        return "\n".join(plain_chunks)
    if html_chunks:
        return _html_to_text(html_chunks[0])
    return ""


def _extract_attachments(parts: list[dict]) -> list[AttachmentMeta]:
    attachments = []
    for part in parts:
        filename = part.get("filename")
        body = part.get("body", {}) or {}
        attachment_id = body.get("attachmentId")
        if not filename and not attachment_id:
            continue
        attachments.append(
            AttachmentMeta(
                filename=filename,
                mime_type=part.get("mimeType"),
                size_estimate=body.get("size"),
                attachment_id=attachment_id,
            )
        )
    return attachments


def _decode_base64url(data: str) -> str:
    padding = "=" * (-len(data) % 4)
    decoded = base64.urlsafe_b64decode(data + padding)
    return decoded.decode("utf-8", errors="replace")


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text("\n")


def _parse_from(raw_value: str | None) -> tuple[str | None, str | None]:
    if not raw_value:
        return None, None
    addresses = getaddresses([raw_value])
    if not addresses:
        return None, None
    name, email = addresses[0]
    return name or None, email or None


def _parse_address_list(raw_value: str | None) -> list[str] | None:
    if not raw_value:
        return None
    addresses = getaddresses([raw_value])
    emails = [email for _, email in addresses if email]
    return emails or None


def _parse_date(raw_value: str | None) -> datetime | None:
    if not raw_value:
        return None
    try:
        dt = parsedate_to_datetime(raw_value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except Exception:
        return None


def _parse_internal_date(internal_date_ms: str | None) -> datetime | None:
    if not internal_date_ms:
        return None
    try:
        millis = int(internal_date_ms)
    except ValueError:
        return None
    return datetime.fromtimestamp(millis / 1000.0, tz=UTC)


def _clean_text(text: str) -> str:
    stripped = _strip_reply_blocks(text)
    stripped = _strip_signature(stripped)
    return "\n".join(line.rstrip() for line in stripped.splitlines()).strip()


def _strip_reply_blocks(text: str) -> str:
    lines = text.splitlines()
    output = []
    for line in lines:
        lower = line.strip().lower()
        if lower.startswith("on ") and " wrote:" in lower:
            break
        if lower.startswith(">"):
            continue
        if "-----original message-----" in lower:
            break
        output.append(line)
    return "\n".join(output)


def _strip_signature(text: str) -> str:
    signoffs = [
        "thanks",
        "thank you",
        "best",
        "regards",
        "sincerely",
        "cheers",
    ]
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        lower = line.strip().lower()
        if any(lower.startswith(signoff) for signoff in signoffs):
            if len(lines) - idx <= 4:
                return "\n".join(lines[:idx]).strip()
    return text
