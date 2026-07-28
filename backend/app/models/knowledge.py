from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class KnowledgeSourceModel(Base):
    __tablename__ = "knowledge_sources"
    __table_args__ = (
        CheckConstraint(
            "visibility IN ('public', 'private', 'organization')",
            name="ck_knowledge_sources_visibility",
        ),
        CheckConstraint(
            "status IN ('registered', 'upload_pending', 'ingestion_pending', 'ingesting', "
            "'ingested', 'ingestion_failed', 'deletion_pending', 'deleted')",
            name="ck_knowledge_sources_status",
        ),
        CheckConstraint(
            "trust_state IN ('discovered', 'needs_review', 'approved_for_rag', "
            "'rejected', 'archived')",
            name="ck_knowledge_sources_trust_state",
        ),
        CheckConstraint(
            "(visibility = 'public' AND owner_user_id IS NULL AND organization_id IS NULL) OR "
            "(visibility = 'private' AND owner_user_id IS NOT NULL AND organization_id IS NULL) OR "
            "(visibility = 'organization' AND organization_id IS NOT NULL)",
            name="ck_knowledge_sources_scope",
        ),
        Index(
            "ix_knowledge_sources_owner_visibility_deleted",
            "owner_user_id",
            "visibility",
            "deleted_at",
        ),
        Index(
            "ix_knowledge_sources_org_visibility_deleted",
            "organization_id",
            "visibility",
            "deleted_at",
        ),
        Index(
            "ix_knowledge_sources_trust_status_deleted",
            "trust_state",
            "status",
            "deleted_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    canonical_uri: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    protocol: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    chain: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="registered", nullable=False, index=True)
    trust_state: Mapped[str] = mapped_column(
        String(32),
        default="needs_review",
        nullable=False,
        index=True,
    )
    approved_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeDocumentModel(Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('registered', 'upload_pending', 'uploaded', 'ingestion_pending', "
            "'ingesting', 'ready', 'failed', 'deletion_pending', 'deleted')",
            name="ck_knowledge_documents_status",
        ),
        Index(
            "ix_knowledge_documents_source_status_deleted",
            "knowledge_source_id",
            "status",
            "deleted_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    knowledge_source_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Application-validated in 18A to avoid a circular cross-dialect migration.
    current_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="registered", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeDocumentVersionModel(Base):
    __tablename__ = "knowledge_document_versions"
    __table_args__ = (
        CheckConstraint("version_number > 0", name="ck_knowledge_document_versions_number"),
        CheckConstraint("size_bytes >= 0", name="ck_knowledge_document_versions_size"),
        CheckConstraint(
            "embedding_dimensions IS NULL OR embedding_dimensions > 0",
            name="ck_knowledge_document_versions_dimensions",
        ),
        CheckConstraint(
            "status IN ('pending_upload', 'uploaded', 'ingestion_pending', 'ingesting', "
            "'ready', 'failed', 'superseded', 'deletion_pending', 'deleted')",
            name="ck_knowledge_document_versions_status",
        ),
        UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_knowledge_document_versions_number",
        ),
        UniqueConstraint("storage_key", name="uq_knowledge_document_versions_storage_key"),
        Index(
            "ix_knowledge_document_versions_document_status",
            "document_id",
            "status",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parser_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    chunker_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_embedding_profile_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # Kept application-validated rather than a foreign key because generations
    # already reference their immutable document version.  Retrieval must bind
    # this exact completed generation, never merely the reusable profile.
    active_embedding_generation_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending_upload",
        nullable=False,
        index=True,
    )
    created_by_job_id: Mapped[str | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeChunkModel(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        CheckConstraint("chunk_index >= 0", name="ck_knowledge_chunks_index"),
        CheckConstraint("token_count >= 0", name="ck_knowledge_chunks_token_count"),
        UniqueConstraint(
            "document_version_id",
            "chunk_index",
            name="uq_knowledge_chunks_version_index",
        ),
        Index(
            "ix_knowledge_chunks_version_deleted",
            "document_version_id",
            "deleted_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_version_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    heading_path: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeEmbeddingProfileModel(Base):
    __tablename__ = "knowledge_embedding_profiles"
    __table_args__ = (
        CheckConstraint("provider = 'local_deterministic'", name="ck_knowledge_embedding_profiles_provider"),
        CheckConstraint("dimensions = 384", name="ck_knowledge_embedding_profiles_dimensions"),
        CheckConstraint("status IN ('active', 'retired')", name="ck_knowledge_embedding_profiles_status"),
        Index("ix_knowledge_embedding_profiles_active", "is_active", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeEmbeddingGenerationModel(Base):
    __tablename__ = "knowledge_embedding_generations"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')", name="ck_knowledge_embedding_generations_status"),
        Index(
            "ix_knowledge_embedding_generations_version_profile_status",
            "document_version_id",
            "embedding_profile_id",
            "status",
        ),
        Index("ix_knowledge_embedding_generations_profile_status", "embedding_profile_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("knowledge_document_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding_profile_id: Mapped[str] = mapped_column(ForeignKey("knowledge_embedding_profiles.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_by_job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    expected_chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeChunkEmbeddingModel(Base):
    __tablename__ = "knowledge_chunk_embeddings"
    __table_args__ = (
        CheckConstraint("dimensions = 384", name="ck_knowledge_chunk_embeddings_dimensions"),
        CheckConstraint("status IN ('pending', 'completed', 'failed', 'deleted')", name="ck_knowledge_chunk_embeddings_status"),
        UniqueConstraint(
            "knowledge_chunk_id",
            "embedding_generation_id",
            name="uq_knowledge_chunk_embeddings_chunk_generation",
        ),
        Index("ix_knowledge_chunk_embeddings_profile_status", "embedding_profile_id", "status", "deleted_at"),
        Index("ix_knowledge_chunk_embeddings_generation", "embedding_generation_id", "deleted_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    knowledge_chunk_id: Mapped[str] = mapped_column(ForeignKey("knowledge_chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding_profile_id: Mapped[str] = mapped_column(ForeignKey("knowledge_embedding_profiles.id", ondelete="RESTRICT"), nullable=False, index=True)
    embedding_generation_id: Mapped[str] = mapped_column(ForeignKey("knowledge_embedding_generations.id", ondelete="CASCADE"), nullable=False, index=True)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    # Canonical portable representation. PostgreSQL also receives an indexed
    # pgvector column in the Phase 18D migration for future shadow retrieval.
    embedding_json: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeRetrievalEventModel(Base):
    """Privacy-safe audit evidence for the disabled-by-default shadow retriever."""

    __tablename__ = "knowledge_retrieval_events"
    __table_args__ = (
        CheckConstraint("latency_ms >= 0", name="ck_knowledge_retrieval_events_latency"),
        Index("ix_knowledge_retrieval_events_user_created", "user_id", "created_at"),
        Index("ix_knowledge_retrieval_events_org_created", "organization_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    organization_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    query_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    filters_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    retrieved_chunk_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    scores_json: Mapped[list[float]] = mapped_column(JSON, default=list, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    retriever_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class KnowledgeCleanupTaskModel(Base):
    """Retryable physical cleanup after a durable version is tombstoned."""

    __tablename__ = "knowledge_cleanup_tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'failed', 'completed')",
            name="ck_knowledge_cleanup_tasks_status",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_knowledge_cleanup_tasks_attempt_count"),
        UniqueConstraint("document_version_id", name="uq_knowledge_cleanup_tasks_version"),
        Index("ix_knowledge_cleanup_tasks_status_next", "status", "next_attempt_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_version_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_document_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
