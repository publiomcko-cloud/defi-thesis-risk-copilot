"""Controlled migration support for the repository's curated public corpus.

This is intentionally an operator-only bootstrap, not a browser upload path.
It imports only Markdown that ships in ``knowledge_base/`` and creates the
same immutable source/document/version/chunk/embedding lineage used by the
durable worker pipeline.  Tenant content and discovered sources are never
considered here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.jobs.cancellation import CancellationContext
from app.knowledge.embedding import (
    EMBEDDING_ALGORITHM_VERSION,
    LOCAL_EMBEDDING_DIMENSIONS,
    LOCAL_EMBEDDING_MODEL,
    LocalDeterministicEmbeddingProvider,
    vector_literal,
)
from app.knowledge.embedding_service import get_configured_embedding_profile
from app.models.knowledge import (
    KnowledgeChunkEmbeddingModel,
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeEmbeddingGenerationModel,
    KnowledgeSourceModel,
)
from app.rag.chunking import chunk_markdown_document
from app.rag.ingest import DEFAULT_KNOWLEDGE_BASE
from app.rag.loaders import LoadedDocument, load_markdown_documents
from app.storage.base import ObjectConflictError, PrivateObjectStorage, StorageError
from app.storage.keys import build_version_object_key


CURATED_SOURCE_TYPE = "curated_markdown"
CURATED_PARSER_VERSION = "phase18g.curated-markdown.v1"
CURATED_CHUNKER_VERSION = "phase18g.curated-sections.v1"


@dataclass(frozen=True)
class PublicCorpusImportSummary:
    documents_seen: int
    documents_created: int
    documents_unchanged: int
    document_versions_created: int
    chunks_created: int
    dry_run: bool


def import_curated_public_corpus(
    db: Session,
    storage: PrivateObjectStorage,
    *,
    knowledge_base_path: Path = DEFAULT_KNOWLEDGE_BASE,
    dry_run: bool = False,
) -> PublicCorpusImportSummary:
    """Import only trusted repository Markdown with stable, repeatable IDs.

    The normal API/worker ingestion route remains authoritative for user and
    organization uploads.  This bootstrap is deliberately narrow so migration
    cannot turn discovered or unapproved data into trusted public retrieval.
    """

    documents = load_markdown_documents(knowledge_base_path)
    created_documents = 0
    unchanged_documents = 0
    created_versions = 0
    created_chunks = 0
    profile = None if dry_run else get_configured_embedding_profile(db, create=True)

    for loaded in documents:
        result = _import_document(
            db,
            storage,
            loaded,
            knowledge_base_path=knowledge_base_path,
            dry_run=dry_run,
            profile_id=profile.id if profile else None,
        )
        created_documents += result.documents_created
        unchanged_documents += result.documents_unchanged
        created_versions += result.document_versions_created
        created_chunks += result.chunks_created

    if not dry_run:
        db.flush()
    return PublicCorpusImportSummary(
        documents_seen=len(documents),
        documents_created=created_documents,
        documents_unchanged=unchanged_documents,
        document_versions_created=created_versions,
        chunks_created=created_chunks,
        dry_run=dry_run,
    )


def require_public_corpus_import_enabled() -> None:
    if not get_settings().knowledge_public_corpus_import_enabled:
        raise RuntimeError("Curated public corpus import is disabled")


def _import_document(
    db: Session,
    storage: PrivateObjectStorage,
    loaded: LoadedDocument,
    *,
    knowledge_base_path: Path,
    dry_run: bool,
    profile_id: str | None,
) -> PublicCorpusImportSummary:
    relative_path = _relative_source_path(loaded.path, knowledge_base_path)
    content = loaded.content.encode("utf-8")
    checksum = sha256(content).hexdigest()
    source_id = _stable_id("ksrc_pub_", relative_path)
    document_id = _stable_id("kdoc_pub_", relative_path)
    version_id = _stable_id("kver_pub_", f"{relative_path}:{checksum}")

    existing_version = db.get(KnowledgeDocumentVersionModel, version_id)
    if existing_version is not None:
        return PublicCorpusImportSummary(1, 0, 1, 0, 0, dry_run)

    source = db.get(KnowledgeSourceModel, source_id)
    document = db.get(KnowledgeDocumentModel, document_id)
    if dry_run:
        return PublicCorpusImportSummary(1, 1 if document is None else 0, 0, 1, len(chunk_markdown_document(loaded)), True)

    now = datetime.now(UTC)
    if source is None:
        source = KnowledgeSourceModel(
            id=source_id,
            owner_user_id=None,
            organization_id=None,
            visibility="public",
            source_type=CURATED_SOURCE_TYPE,
            source_uri=relative_path,
            canonical_uri=relative_path,
            title=loaded.title,
            protocol=loaded.protocol.lower(),
            status="ingested",
            trust_state="approved_for_rag",
            approved_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(source)
        db.flush()
    elif (
        source.visibility != "public"
        or source.source_type != CURATED_SOURCE_TYPE
        or source.trust_state != "approved_for_rag"
        or source.deleted_at is not None
    ):
        raise RuntimeError("Existing curated public source has an unsafe state")

    if document is None:
        document = KnowledgeDocumentModel(
            id=document_id,
            knowledge_source_id=source_id,
            filename=loaded.path.name,
            media_type="text/markdown",
            status="ready",
            created_at=now,
            updated_at=now,
        )
        db.add(document)
        db.flush()
        version_number = 1
        documents_created = 1
    else:
        if document.knowledge_source_id != source_id or document.deleted_at is not None:
            raise RuntimeError("Existing curated public document has an unsafe lineage")
        version_number = (
            db.execute(
                select(KnowledgeDocumentVersionModel.version_number)
                .where(KnowledgeDocumentVersionModel.document_id == document_id)
                .order_by(KnowledgeDocumentVersionModel.version_number.desc())
                .limit(1)
            ).scalar_one_or_none()
            or 0
        ) + 1
        documents_created = 0

    version = KnowledgeDocumentVersionModel(
        id=version_id,
        document_id=document_id,
        version_number=version_number,
        storage_key="pending",
        checksum=checksum,
        size_bytes=len(content),
        parser_version=CURATED_PARSER_VERSION,
        chunker_version=CURATED_CHUNKER_VERSION,
        embedding_model=LOCAL_EMBEDDING_MODEL,
        embedding_dimensions=LOCAL_EMBEDDING_DIMENSIONS,
        active_embedding_profile_id=profile_id,
        status="ready",
        created_at=now,
    )
    version.storage_key = build_version_object_key(source, document, version)
    _store_curated_object(storage, version.storage_key, content, checksum)
    db.add(version)
    db.flush()

    if document.current_version_id and document.current_version_id != version.id:
        previous = db.get(KnowledgeDocumentVersionModel, document.current_version_id)
        if previous is not None and previous.status == "ready":
            previous.status = "superseded"
            previous.superseded_at = now
    document.current_version_id = version.id
    document.status = "ready"
    document.updated_at = now
    source.status = "ingested"
    source.updated_at = now

    chunks = chunk_markdown_document(loaded)
    generation = KnowledgeEmbeddingGenerationModel(
        id=_stable_id("kembgen_pub_", f"{version_id}:{profile_id}"),
        document_version_id=version.id,
        embedding_profile_id=profile_id or "",
        status="completed",
        expected_chunk_count=len(chunks),
        completed_chunk_count=len(chunks),
        content_checksum=_generation_checksum(chunks),
        created_at=now,
        completed_at=now,
    )
    db.add(generation)
    db.flush()
    embedder = LocalDeterministicEmbeddingProvider()
    cancellation = CancellationContext()
    for index, chunk in enumerate(chunks):
        chunk_model = KnowledgeChunkModel(
            id=_stable_id("kchunk_pub_", f"{version_id}:{index}:{chunk.id}"),
            document_version_id=version.id,
            chunk_index=index,
            heading_path=[str(chunk.metadata["section_title"])],
            content=chunk.text,
            content_checksum=sha256(chunk.text.encode("utf-8")).hexdigest(),
            token_count=len(chunk.text.split()),
            metadata_json={**chunk.metadata, "curated_relative_path": relative_path},
            created_at=now,
        )
        embedding = KnowledgeChunkEmbeddingModel(
            id=_stable_id("kemb_pub_", f"{generation.id}:{chunk_model.id}"),
            knowledge_chunk_id=chunk_model.id,
            embedding_profile_id=profile_id or "",
            embedding_generation_id=generation.id,
            content_checksum=chunk_model.content_checksum,
            dimensions=LOCAL_EMBEDDING_DIMENSIONS,
            embedding_json=embedder.embed(chunk.text, cancellation),
            status="completed",
            created_at=now,
        )
        # These models intentionally have no ORM relationships so they are
        # flushed in FK order rather than relying on unit-of-work inference.
        db.add(chunk_model)
        db.flush()
        db.add(embedding)
        # The portable JSON representation is used by SQLite. PostgreSQL also
        # needs its indexed pgvector column populated for the real cutover
        # ordering path; the ORM model intentionally stays cross-dialect.
        if db.bind is not None and db.bind.dialect.name == "postgresql":
            db.flush()
            db.execute(
                text(
                    "UPDATE knowledge_chunk_embeddings "
                    "SET embedding_vector = CAST(:embedding AS vector) WHERE id = :embedding_id"
                ),
                {"embedding": vector_literal(embedding.embedding_json), "embedding_id": embedding.id},
            )
    return PublicCorpusImportSummary(1, documents_created, 0, 1, len(chunks), False)


def _store_curated_object(storage: PrivateObjectStorage, key: str, content: bytes, checksum: str) -> None:
    try:
        storage.put_create_only(
            key=key,
            content=content,
            content_type="text/markdown",
            expected_checksum=checksum,
        )
    except ObjectConflictError:
        existing = storage.head(key=key)
        if existing.checksum != checksum:
            raise StorageError("Curated object checksum does not match immutable version")


def _relative_source_path(path: Path, knowledge_base_path: Path) -> str:
    try:
        return path.resolve().relative_to(knowledge_base_path.resolve()).as_posix()
    except ValueError as exc:
        raise RuntimeError("Curated document is outside the configured knowledge base") from exc


def _stable_id(prefix: str, material: str) -> str:
    return prefix + sha256(material.encode("utf-8")).hexdigest()[:20]


def _generation_checksum(chunks) -> str:
    return sha256(
        "|".join(sha256(chunk.text.encode("utf-8")).hexdigest() for chunk in chunks).encode("utf-8")
    ).hexdigest()
