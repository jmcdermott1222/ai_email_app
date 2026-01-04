"""Add clean body text and Gmail attachment metadata.

Revision ID: 0005_email_body_and_attachments
Revises: 0004_email_ingest_fields
Create Date: 2025-02-15 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005_email_body_and_attachments"
down_revision = "0004_email_ingest_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("emails", sa.Column("clean_body_text", sa.Text(), nullable=True))
    op.add_column(
        "attachments",
        sa.Column("gmail_attachment_id", sa.String(length=255), nullable=True),
    )
    op.create_unique_constraint(
        "ux_attachments_email_gmail_id",
        "attachments",
        ["email_id", "gmail_attachment_id"],
    )


def downgrade() -> None:
    op.drop_constraint("ux_attachments_email_gmail_id", "attachments", type_="unique")
    op.drop_column("attachments", "gmail_attachment_id")
    op.drop_column("emails", "clean_body_text")
