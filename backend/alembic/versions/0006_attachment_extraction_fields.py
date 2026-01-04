"""Add attachment extraction metadata fields.

Revision ID: 0006_attachment_extraction_fields
Revises: 0005_email_body_and_attachments
Create Date: 2025-02-15 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0006_attachment_extraction_fields"
down_revision = "0005_email_body_and_attachments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "attachments", sa.Column("extraction_status", sa.String(length=50), nullable=True)
    )
    op.add_column("attachments", sa.Column("sha256", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("attachments", "sha256")
    op.drop_column("attachments", "extraction_status")
