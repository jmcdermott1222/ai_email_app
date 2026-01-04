"""Add snooze fields to emails.

Revision ID: 0007_email_snooze_fields
Revises: 0006_attachment_extraction_fields
Create Date: 2025-02-15 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0007_email_snooze_fields"
down_revision = "0006_attachment_extraction_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "emails",
        sa.Column("snooze_until_ts", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "emails",
        sa.Column(
            "is_snoozed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("emails", "is_snoozed")
    op.drop_column("emails", "snooze_until_ts")
