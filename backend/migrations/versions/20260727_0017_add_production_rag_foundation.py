"""add production RAG data foundation

Revision ID: 20260727_0017
Revises: 20260724_0016
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260727_0017"
down_revision = "20260724_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.String(length=64), nullable=True),
        sa.Column("organization_id", sa.String(length=64), nullable=True),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_uri", sa.String(length=2048), nullable=True),
        sa.Column("canonical_uri", sa.String(length=2048), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("protocol", sa.String(length=64), nullable=True),
        sa.Column("chain", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("trust_state", sa.String(length=32), nullable=False),
        sa.Column("approved_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "visibility IN ('public', 'private', 'organization')",
            name="ck_knowledge_sources_visibility",
        ),
        sa.CheckConstraint(
            "status IN ('registered', 'upload_pending', 'ingestion_pending', 'ingesting', "
            "'ingested', 'ingestion_failed', 'deletion_pending', 'deleted')",
            name="ck_knowledge_sources_status",
        ),
        sa.CheckConstraint(
            "trust_state IN ('discovered', 'needs_review', 'approved_for_rag', "
            "'rejected', 'archived')",
            name="ck_knowledge_sources_trust_state",
        ),
        sa.CheckConstraint(
            "(visibility = 'public' AND owner_user_id IS NULL AND organization_id IS NULL) OR "
            "(visibility = 'private' AND owner_user_id IS NOT NULL AND organization_id IS NULL) OR "
            "(visibility = 'organization' AND organization_id IS NOT NULL)",
            name="ck_knowledge_sources_scope",
        ),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_sources_owner_user_id", "knowledge_sources", ["owner_user_id"])
    op.create_index("ix_knowledge_sources_organization_id", "knowledge_sources", ["organization_id"])
    op.create_index("ix_knowledge_sources_visibility", "knowledge_sources", ["visibility"])
    op.create_index("ix_knowledge_sources_protocol", "knowledge_sources", ["protocol"])
    op.create_index("ix_knowledge_sources_chain", "knowledge_sources", ["chain"])
    op.create_index("ix_knowledge_sources_status", "knowledge_sources", ["status"])
    op.create_index("ix_knowledge_sources_trust_state", "knowledge_sources", ["trust_state"])
    op.create_index("ix_knowledge_sources_approved_by_user_id", "knowledge_sources", ["approved_by_user_id"])
    op.create_index("ix_knowledge_sources_created_by_user_id", "knowledge_sources", ["created_by_user_id"])
    op.create_index(
        "ix_knowledge_sources_owner_visibility_deleted",
        "knowledge_sources",
        ["owner_user_id", "visibility", "deleted_at"],
    )
    op.create_index(
        "ix_knowledge_sources_org_visibility_deleted",
        "knowledge_sources",
        ["organization_id", "visibility", "deleted_at"],
    )
    op.create_index(
        "ix_knowledge_sources_trust_status_deleted",
        "knowledge_sources",
        ["trust_state", "status", "deleted_at"],
    )

    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("knowledge_source_id", sa.String(length=64), nullable=False),
        sa.Column("current_version_id", sa.String(length=64), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('registered', 'upload_pending', 'uploaded', 'ingestion_pending', "
            "'ingesting', 'ready', 'failed', 'deletion_pending', 'deleted')",
            name="ck_knowledge_documents_status",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_source_id"],
            ["knowledge_sources.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_documents_knowledge_source_id", "knowledge_documents", ["knowledge_source_id"])
    op.create_index("ix_knowledge_documents_current_version_id", "knowledge_documents", ["current_version_id"])
    op.create_index("ix_knowledge_documents_status", "knowledge_documents", ["status"])
    op.create_index(
        "ix_knowledge_documents_source_status_deleted",
        "knowledge_documents",
        ["knowledge_source_id", "status", "deleted_at"],
    )

    op.create_table(
        "knowledge_document_versions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("parser_version", sa.String(length=64), nullable=True),
        sa.Column("chunker_version", sa.String(length=64), nullable=True),
        sa.Column("embedding_model", sa.String(length=255), nullable=True),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by_job_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "version_number > 0",
            name="ck_knowledge_document_versions_number",
        ),
        sa.CheckConstraint(
            "size_bytes >= 0",
            name="ck_knowledge_document_versions_size",
        ),
        sa.CheckConstraint(
            "embedding_dimensions IS NULL OR embedding_dimensions > 0",
            name="ck_knowledge_document_versions_dimensions",
        ),
        sa.CheckConstraint(
            "status IN ('pending_upload', 'uploaded', 'ingestion_pending', 'ingesting', "
            "'ready', 'failed', 'superseded', 'deletion_pending', 'deleted')",
            name="ck_knowledge_document_versions_status",
        ),
        sa.ForeignKeyConstraint(["created_by_job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_knowledge_document_versions_number",
        ),
        sa.UniqueConstraint(
            "storage_key",
            name="uq_knowledge_document_versions_storage_key",
        ),
    )
    op.create_index("ix_knowledge_document_versions_document_id", "knowledge_document_versions", ["document_id"])
    op.create_index("ix_knowledge_document_versions_status", "knowledge_document_versions", ["status"])
    op.create_index("ix_knowledge_document_versions_created_by_job_id", "knowledge_document_versions", ["created_by_job_id"])
    op.create_index(
        "ix_knowledge_document_versions_document_status",
        "knowledge_document_versions",
        ["document_id", "status", "created_at"],
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("document_version_id", sa.String(length=64), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("heading_path", sa.JSON(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_checksum", sa.String(length=64), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("chunk_index >= 0", name="ck_knowledge_chunks_index"),
        sa.CheckConstraint("token_count >= 0", name="ck_knowledge_chunks_token_count"),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["knowledge_document_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_version_id",
            "chunk_index",
            name="uq_knowledge_chunks_version_index",
        ),
    )
    op.create_index("ix_knowledge_chunks_document_version_id", "knowledge_chunks", ["document_version_id"])
    op.create_index(
        "ix_knowledge_chunks_version_deleted",
        "knowledge_chunks",
        ["document_version_id", "deleted_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_version_deleted", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_document_version_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")

    op.drop_index(
        "ix_knowledge_document_versions_document_status",
        table_name="knowledge_document_versions",
    )
    op.drop_index(
        "ix_knowledge_document_versions_created_by_job_id",
        table_name="knowledge_document_versions",
    )
    op.drop_index("ix_knowledge_document_versions_status", table_name="knowledge_document_versions")
    op.drop_index("ix_knowledge_document_versions_document_id", table_name="knowledge_document_versions")
    op.drop_table("knowledge_document_versions")

    op.drop_index(
        "ix_knowledge_documents_source_status_deleted",
        table_name="knowledge_documents",
    )
    op.drop_index("ix_knowledge_documents_status", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_current_version_id", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_knowledge_source_id", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")

    op.drop_index("ix_knowledge_sources_trust_status_deleted", table_name="knowledge_sources")
    op.drop_index("ix_knowledge_sources_org_visibility_deleted", table_name="knowledge_sources")
    op.drop_index("ix_knowledge_sources_owner_visibility_deleted", table_name="knowledge_sources")
    op.drop_index("ix_knowledge_sources_created_by_user_id", table_name="knowledge_sources")
    op.drop_index("ix_knowledge_sources_approved_by_user_id", table_name="knowledge_sources")
    op.drop_index("ix_knowledge_sources_trust_state", table_name="knowledge_sources")
    op.drop_index("ix_knowledge_sources_status", table_name="knowledge_sources")
    op.drop_index("ix_knowledge_sources_chain", table_name="knowledge_sources")
    op.drop_index("ix_knowledge_sources_protocol", table_name="knowledge_sources")
    op.drop_index("ix_knowledge_sources_visibility", table_name="knowledge_sources")
    op.drop_index("ix_knowledge_sources_organization_id", table_name="knowledge_sources")
    op.drop_index("ix_knowledge_sources_owner_user_id", table_name="knowledge_sources")
    op.drop_table("knowledge_sources")
