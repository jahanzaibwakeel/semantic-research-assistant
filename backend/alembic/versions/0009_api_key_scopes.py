"""api key scopes

Revision ID: 0009_api_key_scopes
Revises: 0008_api_keys
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_api_key_scopes"
down_revision: str | None = "0008_api_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("api_keys", sa.Column("scopes", sa.Text(), server_default="*", nullable=False))
    op.add_column("api_keys", sa.Column("daily_request_limit", sa.Integer(), nullable=True))
    op.add_column("api_keys", sa.Column("requests_today", sa.Integer(), server_default="0", nullable=False))
    op.add_column("api_keys", sa.Column("quota_reset_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("api_keys", "scopes", server_default=None)
    op.alter_column("api_keys", "requests_today", server_default=None)


def downgrade() -> None:
    op.drop_column("api_keys", "quota_reset_at")
    op.drop_column("api_keys", "requests_today")
    op.drop_column("api_keys", "daily_request_limit")
    op.drop_column("api_keys", "scopes")
