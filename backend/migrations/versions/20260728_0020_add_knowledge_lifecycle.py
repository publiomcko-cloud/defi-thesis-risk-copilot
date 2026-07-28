"""add durable knowledge lifecycle controls

Revision ID: 20260728_0020
Revises: 20260727_0019
Create Date: 2026-07-28
"""

from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa


revision = "20260728_0020"
down_revision = "20260727_0019"
branch_labels = None
depends_on = None


DEFAULT_PROFILE_ID = "kembprof_local_hash_384_v1"


def upgrade() -> None:
    op.add_column(
        "knowledge_document_versions",
        sa.Column("active_embedding_profile_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_knowledge_document_versions_active_embedding_profile_id",
        "knowledge_document_versions",
        ["active_embedding_profile_id"],
    )
    # Existing completed Phase 18D generations were produced only by the seeded
    # local profile. This metadata backfill is additive and performs no vectors.
    op.execute(
        "UPDATE knowledge_document_versions "
        f"SET active_embedding_profile_id = '{DEFAULT_PROFILE_ID}' "
        "WHERE embedding_model = 'local-hash-384-v1' "
        "AND embedding_dimensions = 384 "
        "AND active_embedding_profile_id IS NULL"
    )
    op.create_table(
        "knowledge_cleanup_tasks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("document_version_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'failed', 'completed')",
            name="ck_knowledge_cleanup_tasks_status",
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_knowledge_cleanup_tasks_attempt_count"),
        sa.ForeignKeyConstraint(
            ["document_version_id"], ["knowledge_document_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_version_id", name="uq_knowledge_cleanup_tasks_version"),
    )
    op.create_index("ix_knowledge_cleanup_tasks_document_version_id", "knowledge_cleanup_tasks", ["document_version_id"])
    op.create_index("ix_knowledge_cleanup_tasks_status", "knowledge_cleanup_tasks", ["status"])
    op.create_index("ix_knowledge_cleanup_tasks_status_next", "knowledge_cleanup_tasks", ["status", "next_attempt_at"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_cleanup_tasks_status_next", table_name="knowledge_cleanup_tasks")
    op.drop_index("ix_knowledge_cleanup_tasks_status", table_name="knowledge_cleanup_tasks")
    op.drop_index("ix_knowledge_cleanup_tasks_document_version_id", table_name="knowledge_cleanup_tasks")
    op.drop_table("knowledge_cleanup_tasks")
    op.drop_index("ix_knowledge_document_versions_active_embedding_profile_id", table_name="knowledge_document_versions")
    op.drop_column("knowledge_document_versions", "active_embedding_profile_id")
