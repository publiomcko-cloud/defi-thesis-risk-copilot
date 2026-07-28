from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.jobs.cancellation import CancellationContext
from app.jobs.errors import JobErrorCategory, JobExecutionError
from app.jobs.schemas import JobResultEnvelope, WorkerClaimedJob
from app.knowledge.embedding import (
    EMBEDDING_ALGORITHM_VERSION,
    LOCAL_EMBEDDING_DIMENSIONS,
    LOCAL_EMBEDDING_MODEL,
    LocalDeterministicEmbeddingProvider,
    vector_literal,
)
from app.models.knowledge import (
    KnowledgeChunkEmbeddingModel,
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeEmbeddingGenerationModel,
    KnowledgeEmbeddingProfileModel,
    KnowledgeSourceModel,
)


class DocumentEmbedJobExecutor:
    """Create local-only vectors; control-plane completion activates a generation."""

    def __init__(self, session_factory: Callable[[], Session] = SessionLocal) -> None:
        self._session_factory = session_factory

    def execute(self, job: WorkerClaimedJob, cancellation: CancellationContext | None = None) -> JobResultEnvelope:
        cancellation = cancellation or CancellationContext()
        version_id, profile_id = _input_identifiers(job)
        with self._session_factory() as db:
            version, document, source = _load_lineage(db, version_id)
            generation = _load_generation(db, job, version_id, profile_id)
            profile = _load_profile(db, profile_id)
            _ensure_embeddable(version, document, source, generation, profile)
            cancellation.raise_if_cancelled()
            provider = LocalDeterministicEmbeddingProvider()
            chunks = db.execute(
                select(KnowledgeChunkModel)
                .where(KnowledgeChunkModel.document_version_id == version.id)
                .where(KnowledgeChunkModel.deleted_at.is_(None))
                .order_by(KnowledgeChunkModel.chunk_index)
            ).scalars().all()
            if not chunks:
                raise JobExecutionError(
                    JobErrorCategory.PERMANENT_INPUT,
                    "document_chunks_unavailable",
                    "The document has no validated chunks to embed.",
                )
            db.execute(
                delete(KnowledgeChunkEmbeddingModel).where(
                    KnowledgeChunkEmbeddingModel.embedding_generation_id == generation.id
                )
            )
            checksum = _generation_checksum(chunks)
            now = datetime.now(UTC)
            generation.status = "processing"
            generation.expected_chunk_count = len(chunks)
            generation.completed_chunk_count = 0
            generation.content_checksum = checksum
            for chunk in chunks:
                cancellation.raise_if_cancelled()
                values = provider.embed(chunk.content, cancellation)
                if len(values) != profile.dimensions:
                    raise JobExecutionError(
                        JobErrorCategory.PERMANENT_INPUT,
                        "embedding_dimension_mismatch",
                        "The embedding profile dimensions are incompatible with the local provider.",
                    )
                record = KnowledgeChunkEmbeddingModel(
                    id=f"kemb_{sha256(f'{chunk.id}:{generation.id}:{chunk.content_checksum}'.encode()).hexdigest()[:20]}",
                    knowledge_chunk_id=chunk.id,
                    embedding_profile_id=profile.id,
                    embedding_generation_id=generation.id,
                    content_checksum=chunk.content_checksum,
                    dimensions=profile.dimensions,
                    embedding_json=values,
                    status="pending",
                    created_at=now,
                )
                db.add(record)
                db.flush()
                if db.bind is not None and db.bind.dialect.name == "postgresql":
                    db.execute(
                        text(
                            "UPDATE knowledge_chunk_embeddings "
                            "SET embedding_vector = CAST(:value AS vector) WHERE id = :id"
                        ),
                        {"value": vector_literal(values), "id": record.id},
                    )
            generation.completed_chunk_count = len(chunks)
            db.commit()
            return JobResultEnvelope(
                result_schema_version="document.embed.v1",
                result_json={
                    "document_version_id": version.id,
                    "embedding_profile_id": profile.id,
                    "embedding_generation_id": generation.id,
                    "embedding_count": len(chunks),
                    "content_checksum": checksum,
                    "embedding_model": profile.model,
                    "embedding_dimensions": profile.dimensions,
                    "embedding_algorithm_version": EMBEDDING_ALGORITHM_VERSION,
                },
            )

    def cancel(self, job: WorkerClaimedJob) -> None:
        with self._session_factory() as db:
            cleanup_document_embedding_outputs(db, _generation_id(job), retryable=False, terminal=False)
            db.commit()


def cleanup_document_embedding_outputs(db: Session, generation_id: str, *, retryable: bool, terminal: bool) -> None:
    generation = db.get(KnowledgeEmbeddingGenerationModel, generation_id)
    if generation is None or generation.deleted_at is not None or generation.status == "completed":
        return
    db.execute(
        delete(KnowledgeChunkEmbeddingModel).where(
            KnowledgeChunkEmbeddingModel.embedding_generation_id == generation.id
        )
    )
    generation.completed_chunk_count = 0
    if retryable:
        generation.status = "pending"
    elif terminal:
        generation.status = "failed"
    else:
        generation.status = "cancelled"


def finalize_document_embedding(db: Session, job, result: dict) -> None:
    version_id, profile_id = _input_identifiers_from_model(job)
    version, document, source = _load_lineage(db, version_id, lock=True)
    generation = _load_generation(db, job, version_id, profile_id, lock=True)
    profile = _load_profile(db, profile_id, lock=True)
    _validate_job_lineage(job, version, document, source, generation, profile)
    _ensure_embeddable(version, document, source, generation, profile)
    if (
        result["document_version_id"] != version.id
        or result["embedding_profile_id"] != profile.id
        or result["embedding_generation_id"] != generation.id
        or result["content_checksum"] != generation.content_checksum
        or result["embedding_model"] != profile.model
        or result["embedding_dimensions"] != profile.dimensions
        or result["embedding_algorithm_version"] != EMBEDDING_ALGORITHM_VERSION
    ):
        raise JobExecutionError(
            JobErrorCategory.PERMANENT_INPUT,
            "embedding_result_mismatch",
            "The embedding result does not match the approved document generation.",
        )
    embeddings = db.execute(
        select(KnowledgeChunkEmbeddingModel)
        .where(KnowledgeChunkEmbeddingModel.embedding_generation_id == generation.id)
        .where(KnowledgeChunkEmbeddingModel.deleted_at.is_(None))
    ).scalars().all()
    if (
        len(embeddings) != generation.expected_chunk_count
        or result["embedding_count"] != generation.expected_chunk_count
        or any(
            item.dimensions != profile.dimensions
            or len(item.embedding_json) != profile.dimensions
            or item.content_checksum is None
            for item in embeddings
        )
    ):
        raise JobExecutionError(
            JobErrorCategory.PERMANENT_INPUT,
            "embedding_output_incomplete",
            "The embedding output is incomplete or incompatible.",
        )
    for embedding in embeddings:
        embedding.status = "completed"
    generation.status = "completed"
    generation.completed_chunk_count = len(embeddings)
    generation.completed_at = datetime.now(UTC)
    version.embedding_model = profile.model
    version.embedding_dimensions = profile.dimensions
    version.active_embedding_profile_id = profile.id
    version.active_embedding_generation_id = generation.id


def _load_lineage(db: Session, version_id: str, *, lock: bool = False):
    statement = (
        select(KnowledgeDocumentVersionModel, KnowledgeDocumentModel, KnowledgeSourceModel)
        .join(KnowledgeDocumentModel, KnowledgeDocumentModel.id == KnowledgeDocumentVersionModel.document_id)
        .join(KnowledgeSourceModel, KnowledgeSourceModel.id == KnowledgeDocumentModel.knowledge_source_id)
        .where(KnowledgeDocumentVersionModel.id == version_id)
    )
    if lock:
        statement = statement.with_for_update()
    row = db.execute(statement).first()
    if row is None:
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "document_version_not_found", "The document version is unavailable.")
    return row


def _load_generation(db: Session, job, version_id: str, profile_id: str, *, lock: bool = False) -> KnowledgeEmbeddingGenerationModel:
    statement = (
        select(KnowledgeEmbeddingGenerationModel)
        .where(KnowledgeEmbeddingGenerationModel.id == _generation_id(job))
        .where(KnowledgeEmbeddingGenerationModel.document_version_id == version_id)
        .where(KnowledgeEmbeddingGenerationModel.embedding_profile_id == profile_id)
    )
    if lock:
        statement = statement.with_for_update()
    generation = db.execute(statement).scalars().one_or_none()
    if generation is None:
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "embedding_generation_not_found", "The embedding generation is unavailable.")
    return generation


def _load_profile(db: Session, profile_id: str, *, lock: bool = False) -> KnowledgeEmbeddingProfileModel:
    statement = select(KnowledgeEmbeddingProfileModel).where(KnowledgeEmbeddingProfileModel.id == profile_id)
    if lock:
        statement = statement.with_for_update()
    profile = db.execute(statement).scalars().one_or_none()
    if profile is None:
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "embedding_profile_not_found", "The embedding profile is unavailable.")
    return profile


def _ensure_embeddable(version, document, source, generation, profile) -> None:
    if any(record.deleted_at is not None for record in (version, document, source, generation)):
        raise JobExecutionError(JobErrorCategory.PERMANENT_AUTHORIZATION, "document_access_revoked", "The document is no longer available.")
    if source.trust_state != "approved_for_rag" or version.status != "ready":
        raise JobExecutionError(JobErrorCategory.PERMANENT_AUTHORIZATION, "source_not_approved", "The source is no longer approved for embedding.")
    if profile.provider != "local_deterministic" or profile.model != LOCAL_EMBEDDING_MODEL or profile.dimensions != LOCAL_EMBEDDING_DIMENSIONS or profile.status != "active" or not profile.is_active:
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "embedding_profile_incompatible", "The embedding profile is not approved for local generation.")
    if generation.status not in {"pending", "processing"}:
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "embedding_generation_not_pending", "The embedding generation is not pending.")


def _validate_job_lineage(job, version, document, source, generation, profile) -> None:
    context = job.input_json.get("_server_context", {})
    expected = {
        "knowledge_source_id": source.id,
        "knowledge_document_id": document.id,
        "document_version_id": version.id,
        "embedding_profile_id": profile.id,
        "embedding_generation_id": generation.id,
    }
    if not isinstance(context, dict) or any(context.get(key) != value for key, value in expected.items()):
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "embedding_lineage_mismatch", "The embedding job lineage is invalid.")
    if job.result_resource_type != "knowledge_embedding_generation" or job.result_resource_id != generation.id:
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "embedding_result_resource_mismatch", "The embedding result resource is invalid.")


def _generation_checksum(chunks: list[KnowledgeChunkModel]) -> str:
    return sha256("|".join(chunk.content_checksum for chunk in chunks).encode("utf-8")).hexdigest()


def _input_identifiers(job: WorkerClaimedJob) -> tuple[str, str]:
    request = job.input_json.get("request", {})
    version_id = request.get("document_version_id")
    profile_id = request.get("embedding_profile_id")
    if not isinstance(version_id, str) or not version_id.startswith("kver_") or not isinstance(profile_id, str) or not profile_id.startswith("kembprof_"):
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "invalid_embedding_input", "The embedding job input is invalid.")
    return version_id, profile_id


def _input_identifiers_from_model(job) -> tuple[str, str]:
    return _input_identifiers(job)


def _generation_id(job: WorkerClaimedJob) -> str:
    value = job.input_json.get("_server_context", {}).get("embedding_generation_id")
    if not isinstance(value, str) or not value.startswith("kembgen_"):
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "invalid_embedding_generation", "The embedding generation is invalid.")
    return value
