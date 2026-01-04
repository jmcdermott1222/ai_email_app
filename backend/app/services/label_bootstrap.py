"""Bootstrap Copilot Gmail labels."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.crypto import CryptoProvider
from app.models import GoogleOAuthToken, UserGmailLabel
from app.services.gmail_client import GmailClient
from app.services.google_credentials import build_credentials

COPILOT_LABELS = [
    "Copilot/Action",
    "Copilot/FYI",
    "Copilot/Newsletter",
    "Copilot/Ignore",
    "Copilot/Snoozed",
    "Copilot/VIP",
]


def ensure_copilot_labels(
    db: Session,
    user_id: int,
    settings: Settings,
    crypto: CryptoProvider,
) -> dict[str, str]:
    """Ensure Copilot labels exist and return name-to-id mapping."""
    token_row = db.execute(
        select(GoogleOAuthToken).where(GoogleOAuthToken.user_id == user_id)
    ).scalar_one_or_none()
    if not token_row:
        raise ValueError("Missing OAuth token row for user")

    creds = build_credentials(db, token_row, settings, crypto).credentials
    client = GmailClient(credentials=creds)
    label_payload = client.list_labels()
    existing_labels = {
        label["name"]: label["id"] for label in label_payload.get("labels", [])
    }

    label_map: dict[str, str] = {}
    for label_name in COPILOT_LABELS:
        label_id = existing_labels.get(label_name)
        if not label_id:
            created = client.create_label(label_name)
            label_id = created.get("id")
        if not label_id:
            raise ValueError(f"Unable to create label {label_name}")
        label_map[label_name] = label_id

        record = db.execute(
            select(UserGmailLabel).where(
                UserGmailLabel.user_id == user_id,
                UserGmailLabel.label_name == label_name,
            )
        ).scalar_one_or_none()
        if record:
            record.label_id = label_id
        else:
            db.add(
                UserGmailLabel(
                    user_id=user_id,
                    label_name=label_name,
                    label_id=label_id,
                )
            )

    db.commit()
    return label_map
