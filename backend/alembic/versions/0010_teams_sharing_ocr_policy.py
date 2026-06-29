"""teams sharing ocr policy

Revision ID: 0010_teams_sharing_ocr_policy
Revises: 0009_api_key_scopes
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_teams_sharing_ocr_policy"
down_revision: str | None = "0009_api_key_scopes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("allowed_api_scopes", sa.Text(), server_default="*", nullable=False),
        sa.Column("api_key_daily_limit", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_teams_owner_id"), "teams", ["owner_id"], unique=False)
    op.add_column("api_keys", sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_api_keys_team_id_teams", "api_keys", "teams", ["team_id"], ["id"])
    op.create_index(op.f("ix_api_keys_team_id"), "api_keys", ["team_id"], unique=False)
    op.create_table(
        "team_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=50), server_default="member", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
    )
    op.create_index(op.f("ix_team_members_role"), "team_members", ["role"], unique=False)
    op.create_index(op.f("ix_team_members_team_id"), "team_members", ["team_id"], unique=False)
    op.create_index(op.f("ix_team_members_user_id"), "team_members", ["user_id"], unique=False)
    op.create_table(
        "document_shares",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission", sa.String(length=50), server_default="read", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "team_id", name="uq_document_shares_document_team"),
    )
    op.create_index(op.f("ix_document_shares_document_id"), "document_shares", ["document_id"], unique=False)
    op.create_index(op.f("ix_document_shares_permission"), "document_shares", ["permission"], unique=False)
    op.create_index(op.f("ix_document_shares_team_id"), "document_shares", ["team_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_document_shares_team_id"), table_name="document_shares")
    op.drop_index(op.f("ix_document_shares_permission"), table_name="document_shares")
    op.drop_index(op.f("ix_document_shares_document_id"), table_name="document_shares")
    op.drop_table("document_shares")
    op.drop_index(op.f("ix_team_members_user_id"), table_name="team_members")
    op.drop_index(op.f("ix_team_members_team_id"), table_name="team_members")
    op.drop_index(op.f("ix_team_members_role"), table_name="team_members")
    op.drop_table("team_members")
    op.drop_index(op.f("ix_api_keys_team_id"), table_name="api_keys")
    op.drop_constraint("fk_api_keys_team_id_teams", "api_keys", type_="foreignkey")
    op.drop_column("api_keys", "team_id")
    op.drop_index(op.f("ix_teams_owner_id"), table_name="teams")
    op.drop_table("teams")
