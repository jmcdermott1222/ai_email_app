"""Tests for Gmail message parsing."""

import json
from pathlib import Path

from app.services.email_parser import parse_message

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


def test_parse_plain_text_email():
    message = _load_fixture("plain_text.json")
    parsed = parse_message(message)
    assert parsed.subject == "Plain email"
    assert parsed.from_email == "me@example.com"
    assert parsed.to_emails == ["bob@example.com"]
    assert parsed.clean_body_text == "Hello world"


def test_parse_html_email():
    message = _load_fixture("html_email.json")
    parsed = parse_message(message)
    assert parsed.subject == "HTML email"
    assert parsed.from_email == "alice@example.com"
    assert parsed.clean_body_text == "Hi there"


def test_parse_multipart_with_attachment():
    message = _load_fixture("multipart_attachment.json")
    parsed = parse_message(message)
    assert parsed.subject == "Attachment email"
    assert parsed.to_emails == ["bob@example.com"]
    assert parsed.cc_emails == ["carol@example.com"]
    assert parsed.attachments
    assert parsed.attachments[0].attachment_id == "att-123"
