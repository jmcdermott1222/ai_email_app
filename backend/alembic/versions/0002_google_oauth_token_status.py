"""Add token status fields and encrypted byte columns.

Revision ID: 0002_google_oauth_token_status
Revises: 0001_initial
Create Date: 2025-02-15 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_google_oauth_token_status"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "google_oauth_tokens",
        sa.Column("access_token_enc", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "google_oauth_tokens",
        sa.Column("refresh_token_enc", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "google_oauth_tokens",
        sa.Column("token_status", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "google_oauth_tokens",
        sa.Column("last_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("google_oauth_tokens", "last_error")
    op.drop_column("google_oauth_tokens", "token_status")
    op.drop_column("google_oauth_tokens", "refresh_token_enc")
    op.drop_column("google_oauth_tokens", "access_token_enc")
