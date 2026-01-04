"""Add digests and alerts tables.

Revision ID: 0010_add_digests_alerts
Revises: 0009_add_cc_emails
Create Date: 2026-01-04 00:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0010_add_digests_alerts"
down_revision = "0009_add_cc_emails"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "digests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("digest_date", sa.Date(), nullable=False),
        sa.Column("content_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_digests_user_created", "digests", ["user_id", "created_at"])
    op.create_index(
        "ux_digests_user_date",
        "digests",
        ["user_id", "digest_date"],
        unique=True,
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("email_id", sa.Integer(), sa.ForeignKey("emails.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_alerts_user_created", "alerts", ["user_id", "created_at"])
    op.create_index("ix_alerts_user_read", "alerts", ["user_id", "read_at"])
    op.create_index(
        "ux_alerts_user_email", "alerts", ["user_id", "email_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ux_alerts_user_email", table_name="alerts")
    op.drop_index("ix_alerts_user_read", table_name="alerts")
    op.drop_index("ix_alerts_user_created", table_name="alerts")
    op.drop_table("alerts")

    op.drop_index("ux_digests_user_date", table_name="digests")
    op.drop_index("ix_digests_user_created", table_name="digests")
    op.drop_table("digests")
