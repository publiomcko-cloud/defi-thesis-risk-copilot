from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user, user_context
from app.db.base import Base
from app.knowledge.lifecycle_service import (
    cleanup_tombstoned_knowledge,
    promote_document_embedding_generation,
    rollback_document_version,
)
from app.knowledge.service import delete_document
from app.models.access_audit_event import AccessAuditEventModel
from app.models.knowledge import (
    KnowledgeChunkEmbeddingModel,
    KnowledgeChunkModel,
    KnowledgeCleanupTaskModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeEmbeddingGenerationModel,
    KnowledgeEmbeddingProfileModel,
    KnowledgeRetrievalEventModel,
    KnowledgeSourceModel,
)
from app.storage.memory import InMemoryPrivateObjectStorage
from app.storage.base import StorageError


@pytest.fixture()
def lifecycle_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_version_rollback_is_atomic_and_preserves_historical_versions(lifecycle_session) -> None:
    Session = lifecycle_session
    with Session() as db:
        owner, document, old_version, current_version = _seed_versioned_document(db)
        db.commit()
        rolled_back = rollback_document_version(
            db, user_context(owner), document.id, old_version.id
        )
        assert rolled_back.current_version_id == old_version.id
        assert db.get(KnowledgeDocumentVersionModel, old_version.id).status == "ready"
        current = db.get(KnowledgeDocumentVersionModel, current_version.id)
        assert current is not None and current.status == "superseded"
        assert current.superseded_at is not None
        event = db.execute(
            select(AccessAuditEventModel).where(
                AccessAuditEventModel.action == "knowledge.document_version_rolled_back"
            )
        ).scalars().one()
        assert event.metadata_json["to_version_id"] == old_version.id


def test_embedding_generation_promotion_and_rollback_keep_previous_generation(lifecycle_session) -> None:
    Session = lifecycle_session
    with Session() as db:
        owner, _, old_version, _ = _seed_versioned_document(db, two_profiles=True)
        db.commit()
        promoted = promote_document_embedding_generation(
            db, user_context(owner), old_version.id, "kembgen_lifecycle_secondary"
        )
        assert promoted.active_embedding_profile_id == "kembprof_lifecycle_secondary"
        reverted = promote_document_embedding_generation(
            db, user_context(owner), old_version.id, "kembgen_lifecycle_primary"
        )
        assert reverted.active_embedding_profile_id == "kembprof_lifecycle_primary"
        assert db.get(KnowledgeEmbeddingGenerationModel, "kembgen_lifecycle_secondary") is not None
        assert db.get(KnowledgeEmbeddingGenerationModel, "kembgen_lifecycle_primary") is not None


def test_tombstone_revokes_first_then_cleanup_is_retryable_and_preserves_citation_ids(
    lifecycle_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Session = lifecycle_session
    storage = InMemoryPrivateObjectStorage()
    with Session() as db:
        owner, document, old_version, _ = _seed_versioned_document(db)
        storage.put_create_only(
            key=old_version.storage_key,
            content=b"historical original",
            content_type="text/markdown",
            expected_checksum=sha256(b"historical original").hexdigest(),
        )
        old_version.checksum = sha256(b"historical original").hexdigest()
        db.add(
            KnowledgeRetrievalEventModel(
                id="kretr_lifecycle",
                request_id="req_lifecycle",
                user_id=owner.id,
                query_hash="a" * 64,
                filters_json={},
                retrieved_chunk_ids=["kchunk_lifecycle_primary"],
                scores_json=[0.9],
                latency_ms=1,
                retriever_version="phase18e.pgvector-shadow.v1",
            )
        )
        db.commit()
        delete_document(db, user_context(owner), document.id)
        task = db.execute(select(KnowledgeCleanupTaskModel)).scalars().first()
        assert task is not None and task.status == "pending"
        assert old_version.deleted_at is not None
        assert "kchunk_lifecycle_primary" in {chunk.id for chunk in db.execute(select(KnowledgeChunkModel)).scalars()}

        dry_run = cleanup_tombstoned_knowledge(db, dry_run=True)
        assert dry_run["eligible"] == 2
        assert old_version.storage_key in storage._objects
        monkeypatch.setattr("app.knowledge.lifecycle_service.create_private_object_storage", lambda: storage)
        result = cleanup_tombstoned_knowledge(db, dry_run=False)
        db.commit()
        assert result["completed"] == 2
        assert storage._objects == {}
        assert db.execute(select(KnowledgeChunkModel)).scalars().all() == []
        assert db.execute(select(KnowledgeChunkEmbeddingModel)).scalars().all() == []
        historical = db.get(KnowledgeRetrievalEventModel, "kretr_lifecycle")
        assert historical is not None and historical.retrieved_chunk_ids == ["kchunk_lifecycle_primary"]
        assert all(task.status == "completed" for task in db.execute(select(KnowledgeCleanupTaskModel)).scalars())


def test_cleanup_storage_failure_stays_retryable_without_restoring_content(lifecycle_session, monkeypatch) -> None:
    Session = lifecycle_session
    storage = InMemoryPrivateObjectStorage()
    with Session() as db:
        owner, document, old_version, _ = _seed_versioned_document(db)
        storage.put_create_only(
            key=old_version.storage_key,
            content=b"retry original",
            content_type="text/markdown",
        )
        db.commit()
        delete_document(db, user_context(owner), document.id)

        class FailingStorage:
            def delete(self, *, key: str) -> None:
                raise StorageError("provider unavailable")

        monkeypatch.setattr(
            "app.knowledge.lifecycle_service.create_private_object_storage", lambda: FailingStorage()
        )
        failed = cleanup_tombstoned_knowledge(db, dry_run=False)
        db.commit()
        assert failed["failed"] == 2
        assert all(task.status == "failed" for task in db.execute(select(KnowledgeCleanupTaskModel)).scalars())
        assert db.execute(select(KnowledgeChunkModel)).scalars().all()

        monkeypatch.setattr("app.knowledge.lifecycle_service.create_private_object_storage", lambda: storage)
        retried = cleanup_tombstoned_knowledge(db, dry_run=False)
        db.commit()
        assert retried["completed"] == 2
        assert db.execute(select(KnowledgeChunkModel)).scalars().all() == []


def _seed_versioned_document(db, *, two_profiles: bool = False):
    owner = create_user(db, "phase18f-owner@example.test")
    source = KnowledgeSourceModel(
        id="ksrc_lifecycle",
        owner_user_id=owner.id,
        visibility="private",
        source_type="upload",
        title="Lifecycle knowledge",
        status="ingested",
        trust_state="approved_for_rag",
        created_by_user_id=owner.id,
    )
    document = KnowledgeDocumentModel(
        id="kdoc_lifecycle",
        knowledge_source_id=source.id,
        current_version_id="kver_lifecycle_current",
        filename="lifecycle.md",
        media_type="text/markdown",
        status="ready",
    )
    old_version = KnowledgeDocumentVersionModel(
        id="kver_lifecycle_old",
        document_id=document.id,
        version_number=1,
        storage_key="knowledge/private/user_lifecycle/sources/ksrc_lifecycle/documents/kdoc_lifecycle/versions/kver_lifecycle_old/original",
        checksum="a" * 64,
        size_bytes=20,
        status="superseded",
        superseded_at=datetime.now(UTC),
        active_embedding_profile_id="kembprof_lifecycle_primary",
        active_embedding_generation_id="kembgen_lifecycle_primary",
    )
    current_version = KnowledgeDocumentVersionModel(
        id="kver_lifecycle_current",
        document_id=document.id,
        version_number=2,
        storage_key="knowledge/private/user_lifecycle/sources/ksrc_lifecycle/documents/kdoc_lifecycle/versions/kver_lifecycle_current/original",
        checksum="b" * 64,
        size_bytes=20,
        status="ready",
        active_embedding_profile_id="kembprof_lifecycle_primary",
        active_embedding_generation_id="kembgen_lifecycle_current",
    )
    primary = KnowledgeEmbeddingProfileModel(
        id="kembprof_lifecycle_primary",
        provider="local_deterministic",
        model="local-hash-384-v1",
        dimensions=384,
        status="active",
        is_active=True,
    )
    db.add_all([source, document, old_version, current_version, primary])
    db.flush()
    _add_generation(db, old_version.id, "primary", "kembprof_lifecycle_primary")
    _add_generation(db, current_version.id, "current", "kembprof_lifecycle_primary")
    if two_profiles:
        secondary = KnowledgeEmbeddingProfileModel(
            id="kembprof_lifecycle_secondary",
            provider="local_deterministic",
            model="local-hash-384-v1",
            dimensions=384,
            status="active",
            is_active=False,
        )
        db.add(secondary)
        db.flush()
        _add_generation(db, old_version.id, "secondary", secondary.id, reuse_existing_chunk=True)
    return owner, document, old_version, current_version


def _add_generation(
    db,
    version_id: str,
    name: str,
    profile_id: str,
    *,
    reuse_existing_chunk: bool = False,
) -> None:
    content = f"{name} lifecycle content"
    checksum = sha256(content.encode()).hexdigest()
    chunk = None
    if reuse_existing_chunk:
        chunk = db.execute(
            select(KnowledgeChunkModel)
            .where(KnowledgeChunkModel.document_version_id == version_id)
            .order_by(KnowledgeChunkModel.chunk_index)
        ).scalars().first()
        assert chunk is not None
        checksum = chunk.content_checksum
    else:
        chunk = KnowledgeChunkModel(
            id=f"kchunk_lifecycle_{name}",
            document_version_id=version_id,
            chunk_index=0,
            heading_path=[name],
            content=content,
            content_checksum=checksum,
            token_count=3,
        )
    generation = KnowledgeEmbeddingGenerationModel(
        id=f"kembgen_lifecycle_{name}",
        document_version_id=version_id,
        embedding_profile_id=profile_id,
        status="completed",
        expected_chunk_count=1,
        completed_chunk_count=1,
        content_checksum=checksum,
        completed_at=datetime.now(UTC),
    )
    db.add_all(([chunk] if not reuse_existing_chunk else []) + [generation])
    db.flush()
    db.add(
        KnowledgeChunkEmbeddingModel(
            id=f"kembed_lifecycle_{name}",
            knowledge_chunk_id=chunk.id,
            embedding_profile_id=profile_id,
            embedding_generation_id=generation.id,
            content_checksum=checksum,
            dimensions=384,
            embedding_json=[0.0] * 384,
            status="completed",
        )
    )
    db.flush()
