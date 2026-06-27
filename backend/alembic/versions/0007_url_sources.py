"""url sources

Revision ID: 0007_url_sources
Revises: 0006_document_lifecycle_fields
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_url_sources"
down_revision: str | None = "0006_document_lifecycle_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("source_url", sa.String(length=2000), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "source_url")
