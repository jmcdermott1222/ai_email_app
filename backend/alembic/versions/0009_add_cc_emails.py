"""Add CC emails to stored messages.

Revision ID: 0009_add_cc_emails
Revises: 0008_extend_gmail_attachment_id_length
Create Date: 2026-01-04 00:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0009_add_cc_emails"
down_revision = "0008_extend_gmail_attachment_id_length"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "emails",
        sa.Column("cc_emails", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("emails", "cc_emails")
