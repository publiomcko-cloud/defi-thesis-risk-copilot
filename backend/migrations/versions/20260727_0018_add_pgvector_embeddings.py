"""add versioned pgvector embedding storage

Revision ID: 20260727_0018
Revises: 20260727_0017
Create Date: 2026-07-27
"""

from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa


revision = "20260727_0018"
down_revision = "20260727_0017"
branch_labels = None
depends_on = None


DEFAULT_PROFILE_ID = "kembprof_local_hash_384_v1"


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    if is_postgres:
        # Provisioning the extension is an infrastructure responsibility. The
        # application migration role must not be assumed to hold CREATE
        # EXTENSION privileges in Supabase or another managed PostgreSQL host.
        has_vector = bind.execute(
            sa.text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        ).scalar()
        if not has_vector:
            raise RuntimeError(
                "pgvector extension is not installed. A database administrator must run "
                "CREATE EXTENSION vector before applying Phase 18 migrations."
            )

    op.create_table(
        "knowledge_embedding_profiles",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("provider = 'local_deterministic'", name="ck_knowledge_embedding_profiles_provider"),
        sa.CheckConstraint("dimensions = 384", name="ck_knowledge_embedding_profiles_dimensions"),
        sa.CheckConstraint("status IN ('active', 'retired')", name="ck_knowledge_embedding_profiles_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_embedding_profiles_active", "knowledge_embedding_profiles", ["is_active", "status"])
    op.create_index(
        "uq_knowledge_embedding_profiles_one_active",
        "knowledge_embedding_profiles",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active"),
        sqlite_where=sa.text("is_active = 1"),
    )
    op.bulk_insert(
        sa.table(
            "knowledge_embedding_profiles",
            sa.column("id", sa.String()),
            sa.column("provider", sa.String()),
            sa.column("model", sa.String()),
            sa.column("dimensions", sa.Integer()),
            sa.column("status", sa.String()),
            sa.column("is_active", sa.Boolean()),
            sa.column("created_at", sa.DateTime(timezone=True)),
        ),
        [
            {
                "id": DEFAULT_PROFILE_ID,
                "provider": "local_deterministic",
                "model": "local-hash-384-v1",
                "dimensions": 384,
                "status": "active",
                "is_active": True,
                "created_at": datetime.now(UTC),
            }
        ],
    )

    op.create_table(
        "knowledge_embedding_generations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("document_version_id", sa.String(length=64), nullable=False),
        sa.Column("embedding_profile_id", sa.String(length=64), nullable=False),
        sa.Column("created_by_job_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("expected_chunk_count", sa.Integer(), nullable=False),
        sa.Column("completed_chunk_count", sa.Integer(), nullable=False),
        sa.Column("content_checksum", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')", name="ck_knowledge_embedding_generations_status"),
        sa.ForeignKeyConstraint(["document_version_id"], ["knowledge_document_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["embedding_profile_id"], ["knowledge_embedding_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_version_id", "embedding_profile_id", name="uq_knowledge_embedding_generations_version_profile"),
    )
    op.create_index("ix_knowledge_embedding_generations_document_version_id", "knowledge_embedding_generations", ["document_version_id"])
    op.create_index("ix_knowledge_embedding_generations_embedding_profile_id", "knowledge_embedding_generations", ["embedding_profile_id"])
    op.create_index("ix_knowledge_embedding_generations_created_by_job_id", "knowledge_embedding_generations", ["created_by_job_id"])
    op.create_index("ix_knowledge_embedding_generations_status", "knowledge_embedding_generations", ["status"])
    op.create_index("ix_knowledge_embedding_generations_profile_status", "knowledge_embedding_generations", ["embedding_profile_id", "status"])

    op.create_table(
        "knowledge_chunk_embeddings",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("knowledge_chunk_id", sa.String(length=64), nullable=False),
        sa.Column("embedding_profile_id", sa.String(length=64), nullable=False),
        sa.Column("embedding_generation_id", sa.String(length=64), nullable=False),
        sa.Column("content_checksum", sa.String(length=64), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("dimensions = 384", name="ck_knowledge_chunk_embeddings_dimensions"),
        sa.CheckConstraint("status IN ('pending', 'completed', 'failed', 'deleted')", name="ck_knowledge_chunk_embeddings_status"),
        sa.ForeignKeyConstraint(["knowledge_chunk_id"], ["knowledge_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["embedding_profile_id"], ["knowledge_embedding_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["embedding_generation_id"], ["knowledge_embedding_generations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("knowledge_chunk_id", "embedding_profile_id", name="uq_knowledge_chunk_embeddings_chunk_profile"),
    )
    op.create_index("ix_knowledge_chunk_embeddings_knowledge_chunk_id", "knowledge_chunk_embeddings", ["knowledge_chunk_id"])
    op.create_index("ix_knowledge_chunk_embeddings_embedding_profile_id", "knowledge_chunk_embeddings", ["embedding_profile_id"])
    op.create_index("ix_knowledge_chunk_embeddings_embedding_generation_id", "knowledge_chunk_embeddings", ["embedding_generation_id"])
    op.create_index("ix_knowledge_chunk_embeddings_status", "knowledge_chunk_embeddings", ["status"])
    op.create_index("ix_knowledge_chunk_embeddings_profile_status", "knowledge_chunk_embeddings", ["embedding_profile_id", "status", "deleted_at"])
    op.create_index("ix_knowledge_chunk_embeddings_generation", "knowledge_chunk_embeddings", ["embedding_generation_id", "deleted_at"])

    if is_postgres:
        op.execute("ALTER TABLE knowledge_chunk_embeddings ADD COLUMN embedding_vector vector(384)")
        op.execute(
            "CREATE INDEX ix_knowledge_chunk_embeddings_vector_hnsw "
            "ON knowledge_chunk_embeddings USING hnsw (embedding_vector vector_cosine_ops) "
            "WHERE status = 'completed' AND deleted_at IS NULL"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_knowledge_chunk_embeddings_vector_hnsw")
    op.drop_index("ix_knowledge_chunk_embeddings_generation", table_name="knowledge_chunk_embeddings")
    op.drop_index("ix_knowledge_chunk_embeddings_profile_status", table_name="knowledge_chunk_embeddings")
    op.drop_index("ix_knowledge_chunk_embeddings_status", table_name="knowledge_chunk_embeddings")
    op.drop_index("ix_knowledge_chunk_embeddings_embedding_generation_id", table_name="knowledge_chunk_embeddings")
    op.drop_index("ix_knowledge_chunk_embeddings_embedding_profile_id", table_name="knowledge_chunk_embeddings")
    op.drop_index("ix_knowledge_chunk_embeddings_knowledge_chunk_id", table_name="knowledge_chunk_embeddings")
    op.drop_table("knowledge_chunk_embeddings")
    op.drop_index("ix_knowledge_embedding_generations_profile_status", table_name="knowledge_embedding_generations")
    op.drop_index("ix_knowledge_embedding_generations_status", table_name="knowledge_embedding_generations")
    op.drop_index("ix_knowledge_embedding_generations_created_by_job_id", table_name="knowledge_embedding_generations")
    op.drop_index("ix_knowledge_embedding_generations_embedding_profile_id", table_name="knowledge_embedding_generations")
    op.drop_index("ix_knowledge_embedding_generations_document_version_id", table_name="knowledge_embedding_generations")
    op.drop_table("knowledge_embedding_generations")
    op.drop_index("uq_knowledge_embedding_profiles_one_active", table_name="knowledge_embedding_profiles")
    op.drop_index("ix_knowledge_embedding_profiles_active", table_name="knowledge_embedding_profiles")
    op.drop_table("knowledge_embedding_profiles")
