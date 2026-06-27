"""usage and evaluation records

Revision ID: 0004_usage_evaluations
Revises: 0003_projects_notes_tokens
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_usage_evaluations"
down_revision: str | None = "0003_projects_notes_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("input_chars", sa.Integer(), nullable=False),
        sa.Column("output_chars", sa.Integer(), nullable=False),
        sa.Column("estimated_tokens", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usage_records_document_id"), "usage_records", ["document_id"], unique=False)
    op.create_index(op.f("ix_usage_records_operation"), "usage_records", ["operation"], unique=False)
    op.create_index(op.f("ix_usage_records_owner_id"), "usage_records", ["owner_id"], unique=False)

    op.create_table(
        "evaluation_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("cited_source_count", sa.Integer(), nullable=False),
        sa.Column("unsupported_citation_count", sa.Integer(), nullable=False),
        sa.Column("groundedness_score", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evaluation_records_document_id"), "evaluation_records", ["document_id"], unique=False)
    op.create_index(op.f("ix_evaluation_records_owner_id"), "evaluation_records", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_evaluation_records_owner_id"), table_name="evaluation_records")
    op.drop_index(op.f("ix_evaluation_records_document_id"), table_name="evaluation_records")
    op.drop_table("evaluation_records")
    op.drop_index(op.f("ix_usage_records_owner_id"), table_name="usage_records")
    op.drop_index(op.f("ix_usage_records_operation"), table_name="usage_records")
    op.drop_index(op.f("ix_usage_records_document_id"), table_name="usage_records")
    op.drop_table("usage_records")
