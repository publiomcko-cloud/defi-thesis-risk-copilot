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

from sqlalchemy import delete, select, text
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
from app.storage.base import (
    ObjectConflictError,
    ObjectNotFoundError,
    PrivateObjectStorage,
    StorageError,
)
from app.storage.keys import build_version_object_key


CURATED_SOURCE_TYPE = "curated_markdown"
CURATED_PARSER_VERSION = "phase18g.curated-markdown.v1"
CURATED_CHUNKER_VERSION = "phase18g.curated-sections.v1"
CURATED_MEDIA_TYPE = "text/markdown"


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
    created_object_keys: set[str] = set()

    try:
        # A savepoint makes the complete corpus attempt atomic without taking
        # ownership of a caller's surrounding transaction. Objects are outside
        # the database transaction, so every newly-created key is compensated
        # if any later document fails.
        with db.begin_nested():
            profile = None if dry_run else get_configured_embedding_profile(db, create=True)
            for loaded in documents:
                result = _import_document(
                    db,
                    storage,
                    loaded,
                    knowledge_base_path=knowledge_base_path,
                    dry_run=dry_run,
                    profile_id=profile.id if profile else None,
                    created_object_keys=created_object_keys,
                )
                created_documents += result.documents_created
                unchanged_documents += result.documents_unchanged
                created_versions += result.document_versions_created
                created_chunks += result.chunks_created

            if not dry_run:
                db.flush()
    except Exception:
        if not dry_run:
            _compensate_created_objects(storage, created_object_keys)
        raise

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
    created_object_keys: set[str],
) -> PublicCorpusImportSummary:
    relative_path = _relative_source_path(loaded.path, knowledge_base_path)
    content = loaded.content.encode("utf-8")
    checksum = sha256(content).hexdigest()
    source_id = _stable_id("ksrc_pub_", relative_path)
    document_id = _stable_id("kdoc_pub_", relative_path)
    version_id = _stable_id("kver_pub_", f"{relative_path}:{checksum}")

    source = db.get(KnowledgeSourceModel, source_id)
    document = db.get(KnowledgeDocumentModel, document_id)
    if dry_run:
        existing_version = db.get(KnowledgeDocumentVersionModel, version_id)
        return PublicCorpusImportSummary(
            1,
            1 if document is None else 0,
            1 if existing_version is not None else 0,
            0 if existing_version is not None else 1,
            0 if existing_version is not None else len(chunk_markdown_document(loaded)),
            True,
        )

    now = datetime.now(UTC)
    profile_id = _required_profile_id(profile_id)
    source = _repair_source(source, source_id, relative_path, loaded, now)
    document, documents_created = _repair_document(document, document_id, source, loaded, now)
    db.add(source)
    db.flush()
    db.add(document)
    db.flush()
    version, version_created = _repair_version(
        db, version_id, document, source, checksum, len(content), profile_id, now
    )
    db.add(version)
    # These intentionally relationship-free models are portable across SQLite
    # and PostgreSQL. Flush their immutable parent lineage in dependency order
    # before inserting chunks so PostgreSQL enforces the production contract.
    db.flush()
    if _ensure_curated_object(storage, version.storage_key, content, checksum):
        created_object_keys.add(version.storage_key)
    chunks = _ensure_curated_chunks(db, version, loaded, relative_path, now)
    generation = _ensure_curated_generation(db, version, profile_id, chunks, now)
    embeddings_created = _ensure_curated_embeddings(
        db, version, generation, profile_id, chunks, now
    )
    _activate_curated_version(
        db, document, source, version, profile_id, generation.id, now
    )
    db.flush()
    return PublicCorpusImportSummary(
        1,
        documents_created,
        0 if version_created else 1,
        1 if version_created else 0,
        embeddings_created,
        False,
    )


def _repair_source(
    source: KnowledgeSourceModel | None,
    source_id: str,
    relative_path: str,
    loaded: LoadedDocument,
    now: datetime,
) -> KnowledgeSourceModel:
    if source is None:
        source = KnowledgeSourceModel(id=source_id, created_at=now)
    elif not _is_expected_curated_source(source, relative_path, loaded):
        raise RuntimeError("Existing curated public source has an unsafe lineage")
    source.owner_user_id = None
    source.organization_id = None
    source.visibility = "public"
    source.source_type = CURATED_SOURCE_TYPE
    source.source_uri = relative_path
    source.canonical_uri = relative_path
    source.title = loaded.title
    source.protocol = loaded.protocol.lower()
    source.status = "ingested"
    source.trust_state = "approved_for_rag"
    source.approved_at = source.approved_at or now
    source.deleted_at = None
    source.updated_at = now
    return source


def _is_expected_curated_source(
    source: KnowledgeSourceModel,
    relative_path: str,
    loaded: LoadedDocument,
) -> bool:
    """Reject ID collisions before mutable repair can change their scope."""

    return bool(
        source.owner_user_id is None
        and source.organization_id is None
        and source.created_by_user_id is None
        and source.visibility == "public"
        and source.source_type == CURATED_SOURCE_TYPE
        and source.source_uri == relative_path
        and source.canonical_uri == relative_path
        and source.protocol == loaded.protocol.lower()
    )


def _repair_document(
    document: KnowledgeDocumentModel | None,
    document_id: str,
    source: KnowledgeSourceModel,
    loaded: LoadedDocument,
    now: datetime,
) -> tuple[KnowledgeDocumentModel, int]:
    if document is None:
        document = KnowledgeDocumentModel(
            id=document_id,
            knowledge_source_id=source.id,
            filename=loaded.path.name,
            media_type="text/markdown",
            status="ready",
            created_at=now,
            updated_at=now,
        )
        return document, 1
    if (
        document.knowledge_source_id != source.id
        or document.filename != loaded.path.name
        or document.media_type != CURATED_MEDIA_TYPE
    ):
        raise RuntimeError("Existing curated public document has an unsafe lineage")
    document.status = "ready"
    document.deleted_at = None
    document.updated_at = now
    return document, 0


def _repair_version(
    db: Session,
    version_id: str,
    document: KnowledgeDocumentModel,
    source: KnowledgeSourceModel,
    checksum: str,
    size_bytes: int,
    profile_id: str,
    now: datetime,
) -> tuple[KnowledgeDocumentVersionModel, bool]:
    version = db.get(KnowledgeDocumentVersionModel, version_id)
    if version is None:
        next_number = (
            db.execute(
                select(KnowledgeDocumentVersionModel.version_number)
                .where(KnowledgeDocumentVersionModel.document_id == document.id)
                .order_by(KnowledgeDocumentVersionModel.version_number.desc())
                .limit(1)
            ).scalar_one_or_none()
            or 0
        ) + 1
        version = KnowledgeDocumentVersionModel(
            id=version_id,
            document_id=document.id,
            version_number=next_number,
            storage_key="pending",
            created_at=now,
        )
        created = True
    else:
        if (
            version.document_id != document.id
            or (version.checksum is not None and version.checksum != checksum)
            or (version.size_bytes not in {0, size_bytes})
        ):
            raise RuntimeError("Existing curated public version has an unsafe lineage")
        created = False
    expected_storage_key = build_version_object_key(source, document, version)
    if not created and version.storage_key not in {"pending", expected_storage_key}:
        raise RuntimeError("Existing curated public version has an unsafe lineage")
    version.storage_key = expected_storage_key
    version.checksum = checksum
    version.size_bytes = size_bytes
    version.parser_version = CURATED_PARSER_VERSION
    version.chunker_version = CURATED_CHUNKER_VERSION
    version.embedding_model = LOCAL_EMBEDDING_MODEL
    version.embedding_dimensions = LOCAL_EMBEDDING_DIMENSIONS
    version.active_embedding_profile_id = profile_id
    version.status = "ready"
    version.superseded_at = None
    version.deleted_at = None
    return version, created


def _ensure_curated_chunks(
    db: Session,
    version: KnowledgeDocumentVersionModel,
    loaded: LoadedDocument,
    relative_path: str,
    now: datetime,
) -> list[KnowledgeChunkModel]:
    expected = chunk_markdown_document(loaded)
    expected_checksums = [sha256(chunk.text.encode("utf-8")).hexdigest() for chunk in expected]
    expected_ids = [
        _stable_id(
            "kchunk_pub_",
            f"{version.id}:{index}:{chunk.metadata['section_title']}:{expected_checksums[index]}",
        )
        for index, chunk in enumerate(expected)
    ]
    existing = db.execute(
        select(KnowledgeChunkModel)
        .where(KnowledgeChunkModel.document_version_id == version.id)
        .order_by(KnowledgeChunkModel.chunk_index)
    ).scalars().all()
    valid = (
        len(existing) == len(expected)
        and [item.id for item in existing] == expected_ids
        and [item.content_checksum for item in existing] == expected_checksums
        and all(item.deleted_at is None for item in existing)
    )
    if valid:
        return existing
    if existing:
        chunk_ids = [item.id for item in existing]
        db.execute(
            delete(KnowledgeChunkEmbeddingModel).where(
                KnowledgeChunkEmbeddingModel.knowledge_chunk_id.in_(chunk_ids)
            )
        )
        db.execute(
            delete(KnowledgeChunkModel).where(KnowledgeChunkModel.id.in_(chunk_ids))
        )
    rebuilt: list[KnowledgeChunkModel] = []
    for index, chunk in enumerate(expected):
        item = KnowledgeChunkModel(
            id=expected_ids[index],
            document_version_id=version.id,
            chunk_index=index,
            heading_path=[str(chunk.metadata["section_title"])],
            content=chunk.text,
            content_checksum=expected_checksums[index],
            token_count=len(chunk.text.split()),
            metadata_json={**chunk.metadata, "curated_relative_path": relative_path},
            created_at=now,
        )
        db.add(item)
        rebuilt.append(item)
    db.flush()
    return rebuilt


def _ensure_curated_generation(
    db: Session,
    version: KnowledgeDocumentVersionModel,
    profile_id: str,
    chunks: list[KnowledgeChunkModel],
    now: datetime,
) -> KnowledgeEmbeddingGenerationModel:
    generation_id = _stable_id("kembgen_pub_", f"{version.id}:{profile_id}")
    generation = db.get(KnowledgeEmbeddingGenerationModel, generation_id)
    if generation is None:
        generation = KnowledgeEmbeddingGenerationModel(
            id=generation_id,
            document_version_id=version.id,
            embedding_profile_id=profile_id,
            created_at=now,
        )
        db.add(generation)
    elif (
        generation.document_version_id != version.id
        or generation.embedding_profile_id != profile_id
    ):
        raise RuntimeError("Existing curated embedding generation has an unsafe lineage")
    generation.status = "completed"
    generation.expected_chunk_count = len(chunks)
    generation.completed_chunk_count = len(chunks)
    generation.content_checksum = _generation_checksum_from_models(chunks)
    generation.completed_at = now
    generation.deleted_at = None
    db.flush()
    return generation


def _ensure_curated_embeddings(
    db: Session,
    version: KnowledgeDocumentVersionModel,
    generation: KnowledgeEmbeddingGenerationModel,
    profile_id: str,
    chunks: list[KnowledgeChunkModel],
    now: datetime,
) -> int:
    existing = db.execute(
        select(KnowledgeChunkEmbeddingModel)
        .where(KnowledgeChunkEmbeddingModel.embedding_generation_id == generation.id)
    ).scalars().all()
    expected_ids = {
        _stable_id("kemb_pub_", f"{generation.id}:{chunk.id}") for chunk in chunks
    }
    valid = (
        len(existing) == len(chunks)
        and {item.id for item in existing} == expected_ids
        and all(
            item.knowledge_chunk_id in {chunk.id for chunk in chunks}
            and item.embedding_profile_id == profile_id
            and item.content_checksum == next(
                chunk.content_checksum for chunk in chunks if chunk.id == item.knowledge_chunk_id
            )
            and item.status == "completed"
            and item.deleted_at is None
            for item in existing
        )
    )
    if valid:
        return 0
    if existing:
        db.execute(
            delete(KnowledgeChunkEmbeddingModel).where(
                KnowledgeChunkEmbeddingModel.embedding_generation_id == generation.id
            )
        )
    embedder = LocalDeterministicEmbeddingProvider()
    cancellation = CancellationContext()
    for chunk in chunks:
        embedding = KnowledgeChunkEmbeddingModel(
            id=_stable_id("kemb_pub_", f"{generation.id}:{chunk.id}"),
            knowledge_chunk_id=chunk.id,
            embedding_profile_id=profile_id,
            embedding_generation_id=generation.id,
            content_checksum=chunk.content_checksum,
            dimensions=LOCAL_EMBEDDING_DIMENSIONS,
            embedding_json=embedder.embed(chunk.content, cancellation),
            status="completed",
            created_at=now,
        )
        db.add(embedding)
        db.flush()
        if db.bind is not None and db.bind.dialect.name == "postgresql":
            db.execute(
                text(
                    "UPDATE knowledge_chunk_embeddings "
                    "SET embedding_vector = CAST(:embedding AS vector) WHERE id = :embedding_id"
                ),
                {"embedding": vector_literal(embedding.embedding_json), "embedding_id": embedding.id},
            )
    return len(chunks)


def _activate_curated_version(
    db: Session,
    document: KnowledgeDocumentModel,
    source: KnowledgeSourceModel,
    version: KnowledgeDocumentVersionModel,
    profile_id: str,
    generation_id: str,
    now: datetime,
) -> None:
    if document.current_version_id and document.current_version_id != version.id:
        previous = db.get(KnowledgeDocumentVersionModel, document.current_version_id)
        if previous is not None and previous.status == "ready":
            previous.status = "superseded"
            previous.superseded_at = now
    document.current_version_id = version.id
    document.status = "ready"
    document.deleted_at = None
    document.updated_at = now
    source.status = "ingested"
    source.trust_state = "approved_for_rag"
    source.deleted_at = None
    source.updated_at = now
    version.active_embedding_profile_id = profile_id
    version.active_embedding_generation_id = generation_id


def _ensure_curated_object(
    storage: PrivateObjectStorage,
    key: str,
    content: bytes,
    checksum: str,
) -> bool:
    try:
        existing = storage.head(key=key)
    except ObjectNotFoundError:
        _store_curated_object(storage, key, content, checksum)
        _verify_curated_object(storage, key, content, checksum)
        return True
    _verify_curated_object(storage, key, content, checksum, existing=existing)
    return False


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
        _verify_curated_object(storage, key, content, checksum, existing=existing)


def _verify_curated_object(
    storage: PrivateObjectStorage,
    key: str,
    content: bytes,
    checksum: str,
    *,
    existing=None,
) -> None:
    """Verify immutable object facts without trusting provider HEAD checksums.

    Supabase's authenticated object-info HEAD response does not expose a stable
    checksum. A bounded authenticated download is therefore the authority when
    that metadata is absent. Providers that do expose a checksum still receive
    strict size and media-type validation from HEAD.
    """

    metadata = existing or storage.head(key=key)
    expected_size = len(content)
    if metadata.size_bytes not in {0, expected_size}:
        raise StorageError("Curated object size does not match immutable version")
    if _normalized_media_type(metadata.content_type) not in {
        CURATED_MEDIA_TYPE,
        "application/octet-stream",
    }:
        raise StorageError("Curated object media type does not match immutable version")
    if metadata.checksum is not None:
        if metadata.checksum != checksum:
            raise StorageError("Curated object checksum does not match immutable version")
        if _normalized_media_type(metadata.content_type) != CURATED_MEDIA_TYPE:
            raise StorageError("Curated object media type does not match immutable version")
        return

    payload = storage.get_bounded(key=key, max_bytes=expected_size)
    if payload.metadata.size_bytes != expected_size:
        raise StorageError("Curated object size does not match immutable version")
    if _normalized_media_type(payload.metadata.content_type) != CURATED_MEDIA_TYPE:
        raise StorageError("Curated object media type does not match immutable version")
    if sha256(payload.content).hexdigest() != checksum:
        raise StorageError("Curated object checksum does not match immutable version")


def _normalized_media_type(value: str) -> str:
    return value.split(";", 1)[0].strip().lower()


def _compensate_created_objects(storage: PrivateObjectStorage, keys: set[str]) -> None:
    for key in sorted(keys, reverse=True):
        try:
            storage.delete(key=key)
        except StorageError:
            # Preserve the database/import failure. Immutable orphan keys stay
            # unreachable and can be reconciled by the explicit operator path.
            pass


def _required_profile_id(profile_id: str | None) -> str:
    if not profile_id:
        raise RuntimeError("Curated corpus import requires an embedding profile")
    return profile_id


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


def _generation_checksum_from_models(chunks: list[KnowledgeChunkModel]) -> str:
    return sha256("|".join(chunk.content_checksum for chunk in chunks).encode("utf-8")).hexdigest()
