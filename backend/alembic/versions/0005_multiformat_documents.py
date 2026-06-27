"""multi format documents

Revision ID: 0005_multiformat_documents
Revises: 0004_usage_evaluations
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_multiformat_documents"
down_revision: str | None = "0004_usage_evaluations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("document_type", sa.String(length=50), nullable=False, server_default="pdf"))
    op.create_index(op.f("ix_documents_document_type"), "documents", ["document_type"], unique=False)
    op.alter_column("documents", "document_type", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_document_type"), table_name="documents")
    op.drop_column("documents", "document_type")
