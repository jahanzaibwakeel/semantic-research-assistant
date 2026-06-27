"""research extractions

Revision ID: 0002_research_extractions
Revises: 0001_initial_schema
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_research_extractions"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_extractions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("authors", sa.Text(), nullable=True),
        sa.Column("publication_year", sa.String(length=50), nullable=True),
        sa.Column("venue", sa.String(length=500), nullable=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("research_question", sa.Text(), nullable=True),
        sa.Column("methods", sa.Text(), nullable=True),
        sa.Column("datasets", sa.Text(), nullable=True),
        sa.Column("claims", sa.Text(), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("findings", sa.Text(), nullable=True),
        sa.Column("limitations", sa.Text(), nullable=True),
        sa.Column("future_work", sa.Text(), nullable=True),
        sa.Column("practical_implications", sa.Text(), nullable=True),
        sa.Column("annotated_bibliography", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id"),
    )
    op.create_index(op.f("ix_research_extractions_document_id"), "research_extractions", ["document_id"], unique=True)
    op.create_index(op.f("ix_research_extractions_owner_id"), "research_extractions", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_research_extractions_owner_id"), table_name="research_extractions")
    op.drop_index(op.f("ix_research_extractions_document_id"), table_name="research_extractions")
    op.drop_table("research_extractions")
