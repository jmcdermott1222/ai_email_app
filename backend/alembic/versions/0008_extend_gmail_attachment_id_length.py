"""Extend Gmail attachment ID length.

Revision ID: 0008_extend_gmail_attachment_id_length
Revises: 0007_email_snooze_fields
Create Date: 2026-01-04 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0008_extend_gmail_attachment_id_length"
down_revision = "0007_email_snooze_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "attachments",
        "gmail_attachment_id",
        existing_type=sa.String(length=255),
        type_=sa.String(length=1024),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "attachments",
        "gmail_attachment_id",
        existing_type=sa.String(length=1024),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
