"""Add ingest status fields to emails.

Revision ID: 0004_email_ingest_fields
Revises: 0003_user_gmail_labels
Create Date: 2025-02-15 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_email_ingest_fields"
down_revision = "0003_user_gmail_labels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("emails", sa.Column("ingest_status", sa.String(length=50), nullable=True))
    op.add_column("emails", sa.Column("ingest_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("emails", "ingest_error")
    op.drop_column("emails", "ingest_status")
