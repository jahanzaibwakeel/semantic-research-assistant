"""document lifecycle fields

Revision ID: 0006_document_lifecycle_fields
Revises: 0005_multiformat_documents
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_document_lifecycle_fields"
down_revision: str | None = "0005_multiformat_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_documents_deleted_at"), "documents", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_deleted_at"), table_name="documents")
    op.drop_column("documents", "deleted_at")
    op.drop_column("documents", "indexed_at")
    op.drop_column("documents", "processed_at")
