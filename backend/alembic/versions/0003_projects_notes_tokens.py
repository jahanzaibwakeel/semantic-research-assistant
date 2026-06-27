"""projects notes and refresh tokens

Revision ID: 0003_projects_notes_tokens
Revises: 0002_research_extractions
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_projects_notes_tokens"
down_revision: str | None = "0002_research_extractions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_owner_id"), "projects", ["owner_id"], unique=False)

    op.add_column("documents", sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("documents", sa.Column("tags", sa.String(length=1000), nullable=True))
    op.create_index(op.f("ix_documents_project_id"), "documents", ["project_id"], unique=False)
    op.create_foreign_key("fk_documents_project_id_projects", "documents", "projects", ["project_id"], ["id"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refresh_tokens_owner_id"), "refresh_tokens", ["owner_id"], unique=False)
    op.create_index(op.f("ix_refresh_tokens_revoked"), "refresh_tokens", ["revoked"], unique=False)
    op.create_index(op.f("ix_refresh_tokens_token_hash"), "refresh_tokens", ["token_hash"], unique=True)

    op.create_table(
        "saved_queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_saved_queries_owner_id"), "saved_queries", ["owner_id"], unique=False)
    op.create_index(op.f("ix_saved_queries_project_id"), "saved_queries", ["project_id"], unique=False)

    op.create_table(
        "research_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("pinned", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_research_notes_document_id"), "research_notes", ["document_id"], unique=False)
    op.create_index(op.f("ix_research_notes_owner_id"), "research_notes", ["owner_id"], unique=False)
    op.create_index(op.f("ix_research_notes_pinned"), "research_notes", ["pinned"], unique=False)
    op.create_index(op.f("ix_research_notes_project_id"), "research_notes", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_research_notes_project_id"), table_name="research_notes")
    op.drop_index(op.f("ix_research_notes_pinned"), table_name="research_notes")
    op.drop_index(op.f("ix_research_notes_owner_id"), table_name="research_notes")
    op.drop_index(op.f("ix_research_notes_document_id"), table_name="research_notes")
    op.drop_table("research_notes")
    op.drop_index(op.f("ix_saved_queries_project_id"), table_name="saved_queries")
    op.drop_index(op.f("ix_saved_queries_owner_id"), table_name="saved_queries")
    op.drop_table("saved_queries")
    op.drop_index(op.f("ix_refresh_tokens_token_hash"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_revoked"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_owner_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_constraint("fk_documents_project_id_projects", "documents", type_="foreignkey")
    op.drop_index(op.f("ix_documents_project_id"), table_name="documents")
    op.drop_column("documents", "tags")
    op.drop_column("documents", "project_id")
    op.drop_index(op.f("ix_projects_owner_id"), table_name="projects")
    op.drop_table("projects")
