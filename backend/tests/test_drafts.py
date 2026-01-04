import base64
from email import message_from_bytes

from app.services.drafts import build_reply_mime


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
