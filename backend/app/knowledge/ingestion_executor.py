from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.config import get_settings
from app.jobs.cancellation import CancellationContext
from app.jobs.errors import JobErrorCategory, JobExecutionError
from app.jobs.schemas import JobResultEnvelope, WorkerClaimedJob
from app.knowledge.ingestion import (
    CHUNKER_VERSION,
    EMBEDDING_MODEL,
    PARSER_VERSION,
    extract_normalize_and_chunk,
)
from app.models.knowledge import KnowledgeChunkModel, KnowledgeDocumentModel, KnowledgeDocumentVersionModel, KnowledgeSourceModel
from app.storage.base import StorageError
from app.storage.factory import create_private_object_storage


class DocumentIngestJobExecutor:
    """Extract immutable-version chunks; control-plane completion activates them."""

    def __init__(self, session_factory: Callable[[], Session] = SessionLocal) -> None:
        self._session_factory = session_factory

    def execute(self, job: WorkerClaimedJob, cancellation: CancellationContext | None = None) -> JobResultEnvelope:
        cancellation = cancellation or CancellationContext()
        version_id = _version_id(job)
        with self._session_factory() as db:
            version, document, source = _load_lineage(db, version_id)
            _ensure_ingestable(version, document, source)
            cancellation.raise_if_cancelled()
            try:
                storage = create_private_object_storage()
                metadata = storage.head(key=version.storage_key)
                settings = get_settings()
                # Storage metadata endpoints are not uniformly reliable about byte
                # counts (Supabase's object-info HEAD response can omit it). The
                # immutable version record and bounded payload are the authority;
                # a non-zero metadata count must still agree with that record.
                if (
                    version.size_bytes > settings.knowledge_ingest_max_bytes
                    or metadata.size_bytes not in {0, version.size_bytes}
                ):
                    raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "object_size_mismatch", "The stored object size is invalid.")
                payload = storage.get_bounded(key=version.storage_key, max_bytes=version.size_bytes)
            except JobExecutionError:
                raise
            except StorageError as exc:
                raise JobExecutionError(JobErrorCategory.RETRYABLE_INFRASTRUCTURE, "private_storage_unavailable", "Private document storage is unavailable.") from exc
            if payload.metadata.content_type.split(";", 1)[0].lower() != document.media_type:
                raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "object_media_type_mismatch", "The stored object media type is invalid.")
            if payload.metadata.size_bytes != version.size_bytes:
                raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "object_size_mismatch", "The stored object size is invalid.")
            checksum = sha256(payload.content).hexdigest()
            if version.checksum is None or checksum != version.checksum:
                raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "object_checksum_mismatch", "The stored object checksum is invalid.")
            chunks = extract_normalize_and_chunk(content=payload.content, media_type=document.media_type, cancellation=cancellation)
            cancellation.raise_if_cancelled()
            db.execute(delete(KnowledgeChunkModel).where(KnowledgeChunkModel.document_version_id == version.id))
            now = datetime.now(UTC)
            for chunk in chunks:
                cancellation.raise_if_cancelled()
                db.add(KnowledgeChunkModel(
                    id=f"kchunk_{sha256(f'{version.id}:{chunk.index}:{chunk.content_checksum}'.encode()).hexdigest()[:20]}",
                    document_version_id=version.id,
                    chunk_index=chunk.index,
                    heading_path=chunk.heading_path,
                    content=chunk.content,
                    content_checksum=chunk.content_checksum,
                    token_count=chunk.token_count,
                    metadata_json={"source_id": source.id, "document_id": document.id, "document_version_id": version.id, "protocol": source.protocol, "chain": source.chain, "media_type": document.media_type, "chunker_version": CHUNKER_VERSION},
                    created_at=now,
                ))
            version.status = "ingesting"
            version.parser_version = PARSER_VERSION
            version.chunker_version = CHUNKER_VERSION
            version.embedding_model = EMBEDDING_MODEL
            if document.current_version_id is None:
                document.status = "ingesting"
                source.status = "ingesting"
            db.commit()
            return JobResultEnvelope(
                result_schema_version="document.ingest.v1",
                result_json={"document_version_id": version.id, "content_checksum": checksum, "chunk_count": len(chunks), "embedding_count": 0, "parser_version": PARSER_VERSION, "chunker_version": CHUNKER_VERSION, "embedding_model": EMBEDDING_MODEL},
            )

    def cancel(self, job: WorkerClaimedJob) -> None:
        with self._session_factory() as db:
            cleanup_document_ingest_outputs(db, _version_id(job), retryable=False, terminal=False)
            db.commit()


def cleanup_document_ingest_outputs(db: Session, version_id: str, *, retryable: bool, terminal: bool) -> None:
    version = db.get(KnowledgeDocumentVersionModel, version_id)
    if version is None or version.deleted_at is not None or version.status == "ready":
        return
    db.execute(delete(KnowledgeChunkModel).where(KnowledgeChunkModel.document_version_id == version.id))
    document = db.get(KnowledgeDocumentModel, version.document_id)
    source = db.get(KnowledgeSourceModel, document.knowledge_source_id) if document else None
    if retryable:
        version.status = "ingestion_pending"
    elif terminal:
        version.status = "failed"
    else:
        version.status = "uploaded"
    if document and document.current_version_id is None:
        document.status = "failed" if terminal else "uploaded"
    if source and document and document.current_version_id is None:
        source.status = "ingestion_failed" if terminal else "registered"


def finalize_document_ingestion(db: Session, job, result: dict) -> None:
    version_id = _version_id_from_model(job)
    version, document, source = _load_lineage(db, version_id, lock=True)
    _validate_job_lineage(job, version, document, source)
    _ensure_ingestable(version, document, source, completing=True)
    if source.trust_state != "approved_for_rag":
        raise JobExecutionError(JobErrorCategory.PERMANENT_AUTHORIZATION, "source_not_approved", "The source is no longer approved for ingestion.")
    if result["document_version_id"] != version.id or result["content_checksum"] != version.checksum:
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "ingestion_result_mismatch", "The ingestion result does not match the document version.")
    chunks = db.execute(select(KnowledgeChunkModel).where(KnowledgeChunkModel.document_version_id == version.id).where(KnowledgeChunkModel.deleted_at.is_(None))).scalars().all()
    if len(chunks) != result["chunk_count"] or not chunks:
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "ingestion_chunk_mismatch", "The ingestion chunk output is incomplete.")
    previous_id = document.current_version_id
    if previous_id and previous_id != version.id:
        previous = db.get(KnowledgeDocumentVersionModel, previous_id)
        if previous is not None and previous.status == "ready":
            previous.status = "superseded"
            previous.superseded_at = datetime.now(UTC)
    version.status = "ready"
    version.parser_version = result["parser_version"]
    version.chunker_version = result["chunker_version"]
    version.embedding_model = result["embedding_model"]
    document.current_version_id = version.id
    document.status = "ready"
    document.updated_at = datetime.now(UTC)
    source.status = "ingested"
    source.updated_at = datetime.now(UTC)


def _load_lineage(db: Session, version_id: str, *, lock: bool = False):
    statement = select(KnowledgeDocumentVersionModel, KnowledgeDocumentModel, KnowledgeSourceModel).join(KnowledgeDocumentModel, KnowledgeDocumentModel.id == KnowledgeDocumentVersionModel.document_id).join(KnowledgeSourceModel, KnowledgeSourceModel.id == KnowledgeDocumentModel.knowledge_source_id).where(KnowledgeDocumentVersionModel.id == version_id)
    if lock:
        statement = statement.with_for_update()
    row = db.execute(statement).first()
    if row is None:
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "document_version_not_found", "The document version is unavailable.")
    return row


def _ensure_ingestable(version, document, source, *, completing: bool = False) -> None:
    if any(record.deleted_at is not None for record in (version, document, source)):
        raise JobExecutionError(JobErrorCategory.PERMANENT_AUTHORIZATION, "document_access_revoked", "The document is no longer available.")
    allowed = {"ingestion_pending", "ingesting"} if completing else {"ingestion_pending", "ingesting"}
    if version.status not in allowed:
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "document_version_not_pending", "The document version is not pending ingestion.")


def _validate_job_lineage(job, version, document, source) -> None:
    """Bind worker completion to the immutable, server-derived ingestion lineage."""

    context = job.input_json.get("_server_context", {})
    if not isinstance(context, dict) or any(
        context.get(field) != expected
        for field, expected in {
            "knowledge_source_id": source.id,
            "knowledge_document_id": document.id,
            "document_version_id": version.id,
        }.items()
    ):
        raise JobExecutionError(
            JobErrorCategory.PERMANENT_INPUT,
            "ingestion_lineage_mismatch",
            "The ingestion job is not bound to this document version.",
        )
    if job.result_resource_type != "knowledge_document_version" or job.result_resource_id != version.id:
        raise JobExecutionError(
            JobErrorCategory.PERMANENT_INPUT,
            "ingestion_result_resource_mismatch",
            "The ingestion job result resource is invalid.",
        )


def _version_id(job: WorkerClaimedJob) -> str:
    value = job.input_json.get("request", {}).get("document_version_id")
    if not isinstance(value, str) or not value.startswith("kver_"):
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "invalid_document_version", "The job document version is invalid.")
    return value


def _version_id_from_model(job) -> str:
    value = job.input_json.get("request", {}).get("document_version_id")
    if not isinstance(value, str) or not value.startswith("kver_"):
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "invalid_document_version", "The job document version is invalid.")
    return value
