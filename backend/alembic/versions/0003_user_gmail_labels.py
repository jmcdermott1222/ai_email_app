"""Add user Gmail labels table.

Revision ID: 0003_user_gmail_labels
Revises: 0002_google_oauth_token_status
Create Date: 2025-02-15 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_user_gmail_labels"
down_revision = "0002_google_oauth_token_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_gmail_labels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("label_name", sa.String(length=255), nullable=False),
        sa.Column("label_id", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "label_name"),
    )


def downgrade() -> None:
    op.drop_table("user_gmail_labels")
