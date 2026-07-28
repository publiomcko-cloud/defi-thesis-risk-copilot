from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest
from sqlalchemy import create_engine, delete, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.protocol_research_agent import retrieve_protocol_context
from app.auth.service import create_user
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.knowledge.public_corpus import (
    CuratedObjectDisposition,
    _compensate_created_objects,
    _ensure_curated_object,
    _stable_id,
    import_curated_public_corpus,
    import_curated_public_corpus_operator,
    require_public_corpus_import_enabled,
)
from app.knowledge.retrieval_evaluation import evaluate_durable_public_retrieval
from app.knowledge.public_retriever import retrieve_public_durable_context
from app.models.knowledge import (
    KnowledgeChunkEmbeddingModel,
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeSourceModel,
)
from app.models.organization import OrganizationModel
from app.jobs.cancellation import CancellationContext
from app.knowledge.embedding import LocalDeterministicEmbeddingProvider
from app.rag.retriever import RetrievalResult
from app.storage.memory import InMemoryPrivateObjectStorage
from app.storage.base import ObjectConflictError, ObjectMetadata, StorageError


@pytest.fixture()
def public_corpus_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    yield Session


def _curated_root(tmp_path: Path, content: str = "## Oracle Safety\nOracle safeguards protect liquidation calculations.") -> Path:
    root = tmp_path / "knowledge_base"
    protocol = root / "aave"
    protocol.mkdir(parents=True, exist_ok=True)
    (protocol / "README.md").write_text(f"# Aave Curated Notes\n\n{content}\n", encoding="utf-8")
    return root


def _two_document_root(tmp_path: Path) -> Path:
    root = _curated_root(tmp_path)
    pendle = root / "pendle"
    pendle.mkdir(parents=True)
    (pendle / "README.md").write_text(
        "# Pendle Curated Notes\n\n## Maturity\nMaturity controls are documented.\n",
        encoding="utf-8",
    )
    return root


def test_curated_import_is_idempotent_and_creates_approved_public_lineage(public_corpus_session, tmp_path: Path) -> None:
    root = _curated_root(tmp_path)
    storage = InMemoryPrivateObjectStorage()
    with public_corpus_session() as db:
        first = import_curated_public_corpus(db, storage, knowledge_base_path=root)
        db.commit()
        second = import_curated_public_corpus(db, storage, knowledge_base_path=root)
        db.commit()
        source = db.execute(select(KnowledgeSourceModel)).scalar_one()
        versions = db.execute(select(KnowledgeDocumentVersionModel)).scalars().all()

    assert first.documents_created == 1
    assert first.document_versions_created == 1
    assert first.chunks_created == 1
    assert second.documents_unchanged == 1
    assert second.document_versions_created == 0
    assert source.visibility == "public"
    assert source.source_type == "curated_markdown"
    assert source.trust_state == "approved_for_rag"
    assert source.status == "ingested"
    assert len(versions) == 1
    assert versions[0].id.startswith("kver_")
    assert storage.head(key=versions[0].storage_key).checksum == versions[0].checksum


def test_curated_import_creates_immutable_reingestion_version_and_durable_results(public_corpus_session, tmp_path: Path) -> None:
    root = _curated_root(tmp_path)
    storage = InMemoryPrivateObjectStorage()
    with public_corpus_session() as db:
        import_curated_public_corpus(db, storage, knowledge_base_path=root)
        db.commit()
        _curated_root(tmp_path, "## Oracle Safety\nUpdated oracle safeguards protect liquidation calculations.")
        summary = import_curated_public_corpus(db, storage, knowledge_base_path=root)
        db.commit()
        versions = db.execute(
            select(KnowledgeDocumentVersionModel).order_by(KnowledgeDocumentVersionModel.version_number)
        ).scalars().all()
        results = retrieve_public_durable_context(db, "updated oracle safeguards", protocols=["aave"])

    assert summary.document_versions_created == 1
    assert [version.status for version in versions] == ["superseded", "ready"]
    assert len(results) == 1
    assert results[0].metadata["document_title"] == "Aave Curated Notes"
    assert results[0].metadata["source_url"].endswith("README.md")


def test_curated_import_converges_after_a_to_b_to_a_and_repairs_partial_state(
    public_corpus_session,
    tmp_path: Path,
) -> None:
    root = _curated_root(tmp_path, "## Safety\nOriginal oracle controls.")
    storage = InMemoryPrivateObjectStorage()
    with public_corpus_session() as db:
        import_curated_public_corpus(db, storage, knowledge_base_path=root)
        db.commit()
        original = db.execute(select(KnowledgeDocumentVersionModel)).scalar_one()

        _curated_root(tmp_path, "## Safety\nReplacement liquidation controls.")
        import_curated_public_corpus(db, storage, knowledge_base_path=root)
        db.commit()
        replacement = db.execute(
            select(KnowledgeDocumentVersionModel).where(
                KnowledgeDocumentVersionModel.id != original.id
            )
        ).scalar_one()

        # Simulate an interrupted retention/embedding operation before a
        # deterministic rerun returns the repository corpus to A.
        source = db.execute(select(KnowledgeSourceModel)).scalar_one()
        source.status = "deleted"
        source.deleted_at = source.created_at
        original.status = "deleted"
        original.deleted_at = original.created_at
        storage.delete(key=original.storage_key)
        db.execute(
            delete(KnowledgeChunkEmbeddingModel).where(
                KnowledgeChunkEmbeddingModel.embedding_generation_id
                == original.active_embedding_generation_id
            )
        )
        db.commit()

        _curated_root(tmp_path, "## Safety\nOriginal oracle controls.")
        summary = import_curated_public_corpus(db, storage, knowledge_base_path=root)
        db.commit()
        document = db.execute(select(KnowledgeDocumentModel)).scalar_one()
        repaired = db.get(KnowledgeDocumentVersionModel, original.id)
        assert repaired is not None
        assert summary.document_versions_created == 0
        assert source.status == "ingested" and source.deleted_at is None
        assert document.current_version_id == original.id
        assert repaired.status == "ready" and repaired.deleted_at is None
        assert repaired.active_embedding_generation_id
        assert replacement.status == "superseded"
        assert storage.head(key=repaired.storage_key).checksum == repaired.checksum
        assert db.execute(
            select(KnowledgeChunkEmbeddingModel).where(
                KnowledgeChunkEmbeddingModel.embedding_generation_id
                == repaired.active_embedding_generation_id
            )
        ).scalars().all()


def test_curated_import_compensates_a_new_object_when_database_write_fails(
    public_corpus_session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _curated_root(tmp_path)
    storage = InMemoryPrivateObjectStorage()
    with public_corpus_session() as db:
        from app.knowledge.embedding_service import get_configured_embedding_profile

        get_configured_embedding_profile(db, create=True)
        db.commit()

        original_flush = db.flush
        flush_count = 0

        def fail_flush() -> None:
            nonlocal flush_count
            flush_count += 1
            if flush_count >= 4:
                raise SQLAlchemyError("forced durable database failure")
            original_flush()

        monkeypatch.setattr(db, "flush", fail_flush)
        with pytest.raises(SQLAlchemyError, match="forced durable database failure"):
            import_curated_public_corpus(db, storage, knowledge_base_path=root)
        assert storage._objects == {}
        db.rollback()


def test_curated_import_compensates_every_object_when_the_second_document_fails(
    public_corpus_session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _two_document_root(tmp_path)
    storage = InMemoryPrivateObjectStorage()
    from app.knowledge import public_corpus

    original = public_corpus._ensure_curated_embeddings
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise SQLAlchemyError("forced second document failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(public_corpus, "_ensure_curated_embeddings", fail_second)
    with public_corpus_session() as db:
        with pytest.raises(SQLAlchemyError, match="second document"):
            import_curated_public_corpus(db, storage, knowledge_base_path=root)
        assert storage._objects == {}
        assert db.execute(select(KnowledgeSourceModel)).scalars().all() == []
        assert db.execute(select(KnowledgeDocumentModel)).scalars().all() == []


def test_curated_import_compensates_an_uploaded_object_when_post_upload_verification_fails(
    public_corpus_session,
    tmp_path: Path,
) -> None:
    class VerificationFailingStorage(InMemoryPrivateObjectStorage):
        uploaded_key: str | None = None

        def put_create_only(self, **kwargs):
            metadata = super().put_create_only(**kwargs)
            self.uploaded_key = metadata.key
            return metadata

        def head(self, *, key: str) -> ObjectMetadata:
            metadata = super().head(key=key)
            if key == self.uploaded_key:
                return ObjectMetadata(
                    key=metadata.key,
                    size_bytes=metadata.size_bytes,
                    content_type="text/plain",
                    checksum=metadata.checksum,
                )
            return metadata

    storage = VerificationFailingStorage()
    with public_corpus_session() as db:
        with pytest.raises(StorageError, match="media type"):
            import_curated_public_corpus(db, storage, knowledge_base_path=_curated_root(tmp_path))
        assert storage._objects == {}
        assert db.execute(select(KnowledgeSourceModel)).scalars().all() == []


def test_conflict_verified_object_is_not_owned_or_deleted_by_this_importer() -> None:
    class ConcurrentConflictStorage(InMemoryPrivateObjectStorage):
        def put_create_only(self, **kwargs):
            # A concurrent importer wins after this importer observed a miss.
            super().put_create_only(**kwargs)
            raise ObjectConflictError("Private object already exists")

    storage = ConcurrentConflictStorage()
    key = "knowledge/public/global/sources/ksrc_race/documents/kdoc_race/versions/kver_race/original"
    content = b"# Curated\n"
    created_keys: set[str] = set()

    disposition = _ensure_curated_object(
        storage,
        key,
        content,
        sha256(content).hexdigest(),
        created_object_keys=created_keys,
    )
    _compensate_created_objects(storage, created_keys)

    assert disposition is CuratedObjectDisposition.CONFLICT_VERIFIED
    assert created_keys == set()
    assert storage.head(key=key).content_type == "text/markdown"


def test_operator_import_compensates_every_object_when_final_commit_fails(
    public_corpus_session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = InMemoryPrivateObjectStorage()
    with public_corpus_session() as db:
        def fail_commit() -> None:
            raise SQLAlchemyError("forced operator commit failure")

        monkeypatch.setattr(db, "commit", fail_commit)
        with pytest.raises(SQLAlchemyError, match="operator commit"):
            import_curated_public_corpus_operator(
                db,
                storage,
                knowledge_base_path=_two_document_root(tmp_path),
            )
        assert storage._objects == {}
        assert db.execute(select(KnowledgeSourceModel)).scalars().all() == []
        assert db.execute(select(KnowledgeDocumentModel)).scalars().all() == []


def test_transaction_local_import_remains_rollbackable_for_evaluation(
    public_corpus_session,
    tmp_path: Path,
) -> None:
    storage = InMemoryPrivateObjectStorage()
    with public_corpus_session() as db:
        import_curated_public_corpus(db, storage, knowledge_base_path=_curated_root(tmp_path))
        assert db.execute(select(KnowledgeSourceModel)).scalars().all()
        db.rollback()
        assert db.execute(select(KnowledgeSourceModel)).scalars().all() == []


@pytest.mark.parametrize(
    "corruption",
    ["chunk_content", "chunk_heading", "chunk_metadata", "embedding_json", "embedding_dimensions"],
)
def test_curated_import_repairs_corrupted_chunks_and_embeddings(
    public_corpus_session,
    tmp_path: Path,
    corruption: str,
) -> None:
    root = _curated_root(tmp_path)
    storage = InMemoryPrivateObjectStorage()
    with public_corpus_session() as db:
        import_curated_public_corpus(db, storage, knowledge_base_path=root)
        db.commit()
        chunk = db.execute(select(KnowledgeChunkModel)).scalar_one()
        embedding = db.execute(select(KnowledgeChunkEmbeddingModel)).scalar_one()
        if corruption == "chunk_content":
            chunk.content = "tampered content"
        elif corruption == "chunk_heading":
            chunk.heading_path = ["Tampered"]
        elif corruption == "chunk_metadata":
            chunk.metadata_json = {"protocol": "tampered"}
        elif corruption == "embedding_json":
            embedding.embedding_json = [0.0] * 384
        else:
            db.execute(text("PRAGMA ignore_check_constraints = ON"))
            db.execute(
                text("UPDATE knowledge_chunk_embeddings SET dimensions = 383 WHERE id = :id"),
                {"id": embedding.id},
            )
            db.execute(text("PRAGMA ignore_check_constraints = OFF"))
        db.commit()

        import_curated_public_corpus(db, storage, knowledge_base_path=root)
        db.commit()
        repaired_chunk = db.execute(select(KnowledgeChunkModel)).scalar_one()
        repaired_embedding = db.execute(select(KnowledgeChunkEmbeddingModel)).scalar_one()

    assert repaired_chunk.content_checksum == sha256(repaired_chunk.content.encode("utf-8")).hexdigest()
    assert repaired_chunk.heading_path == ["Oracle Safety"]
    assert repaired_chunk.metadata_json["curated_relative_path"] == "aave/README.md"
    assert repaired_embedding.dimensions == 384
    assert len(repaired_embedding.embedding_json) == 384
    assert repaired_embedding.content_checksum == repaired_chunk.content_checksum
    assert repaired_embedding.embedding_json == LocalDeterministicEmbeddingProvider().embed(
        repaired_chunk.content,
        CancellationContext(),
    )


@pytest.mark.parametrize(
    "collision",
    ["private", "organization", "discovered", "different_type", "mismatched_path"],
)
def test_curated_import_fails_closed_for_deterministic_source_id_collisions(
    public_corpus_session,
    tmp_path: Path,
    collision: str,
) -> None:
    root = _curated_root(tmp_path)
    relative_path = "aave/README.md"
    source_id = _stable_id("ksrc_pub_", relative_path)
    storage = InMemoryPrivateObjectStorage()
    with public_corpus_session() as db:
        owner = create_user(db, f"phase18-collision-{collision}@example.test")
        organization = OrganizationModel(
            id=f"org_phase18_collision_{collision}",
            name=f"Phase 18 {collision}",
            slug=f"phase18-{collision}",
            status="active",
            created_by_user_id=owner.id,
        )
        if collision == "organization":
            db.add(organization)
            visibility, owner_id, organization_id = "organization", owner.id, organization.id
            source_type, source_uri, canonical_uri = "upload", relative_path, relative_path
        elif collision == "private":
            visibility, owner_id, organization_id = "private", owner.id, None
            source_type, source_uri, canonical_uri = "upload", relative_path, relative_path
        elif collision == "discovered":
            visibility, owner_id, organization_id = "public", None, None
            source_type, source_uri, canonical_uri = "discovered", relative_path, relative_path
        elif collision == "different_type":
            visibility, owner_id, organization_id = "public", None, None
            source_type, source_uri, canonical_uri = "upload", relative_path, relative_path
        else:
            visibility, owner_id, organization_id = "public", None, None
            source_type, source_uri, canonical_uri = "curated_markdown", "other/README.md", "other/README.md"
        source = KnowledgeSourceModel(
            id=source_id,
            owner_user_id=owner_id,
            organization_id=organization_id,
            visibility=visibility,
            source_type=source_type,
            source_uri=source_uri,
            canonical_uri=canonical_uri,
            title="Collision source",
            protocol="aave",
            status="registered",
            trust_state="discovered",
            created_by_user_id=owner.id if collision in {"private", "organization"} else None,
        )
        db.add(source)
        db.commit()

        with pytest.raises(RuntimeError, match="unsafe lineage"):
            import_curated_public_corpus(db, storage, knowledge_base_path=root)

        unchanged = db.get(KnowledgeSourceModel, source_id)
        assert unchanged is not None
        assert unchanged.visibility == visibility
        assert unchanged.source_type == source_type
        assert unchanged.source_uri == source_uri
        assert storage._objects == {}


def test_public_durable_retriever_never_surfaces_noncurated_or_unapproved_rows(public_corpus_session, tmp_path: Path) -> None:
    root = _curated_root(tmp_path)
    storage = InMemoryPrivateObjectStorage()
    with public_corpus_session() as db:
        import_curated_public_corpus(db, storage, knowledge_base_path=root)
        source = db.execute(select(KnowledgeSourceModel)).scalar_one()
        source.trust_state = "needs_review"
        db.commit()
        assert retrieve_public_durable_context(db, "oracle safeguards", protocols=["aave"]) == []


def test_primary_cutover_requires_shadow_and_falls_back_to_json(monkeypatch: pytest.MonkeyPatch, public_corpus_session) -> None:
    with pytest.raises(ValueError, match="KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED"):
        Settings(knowledge_pgvector_primary_enabled=True)

    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("WORKER_API_ENABLED", "true")
    monkeypatch.setenv("KNOWLEDGE_EMBEDDINGS_ENABLED", "true")
    monkeypatch.setenv("KNOWLEDGE_SHADOW_RETRIEVAL_ENABLED", "true")
    monkeypatch.setenv("KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED", "true")
    get_settings.cache_clear()
    try:
        with public_corpus_session() as db:
            # No imported durable corpus means old JSON retrieval is still used.
            fallback = retrieve_protocol_context("What is Health Factor?", ["aave"], db=db)
        assert fallback

        durable = [
            RetrievalResult(
                chunk_id="kchunk_public_test",
                text="Durable public context",
                metadata={
                    "protocol": "aave",
                    "source_url": "knowledge_base/aave/README.md",
                    "document_title": "Aave",
                    "section_title": "Safety",
                },
                similarity_score=1.0,
            )
        ]
        monkeypatch.setattr(
            "app.agents.protocol_research_agent.retrieve_public_durable_context",
            lambda *args, **kwargs: durable,
        )
        with public_corpus_session() as db:
            assert retrieve_protocol_context("oracle", ["aave"], db=db) == durable
    finally:
        get_settings.cache_clear()


def test_public_import_command_is_explicitly_disabled_by_default() -> None:
    with pytest.raises(RuntimeError, match="disabled"):
        require_public_corpus_import_enabled()


def test_durable_public_evaluation_reports_citation_coverage(public_corpus_session, tmp_path: Path) -> None:
    root = _curated_root(tmp_path, "## Oracle Safety\nOracle safeguards protect liquidation calculations.")
    dataset = tmp_path / "eval.json"
    dataset.write_text(
        '[{"id":"oracle","query":"oracle safeguards","expected_protocol":"aave","expected_terms":["oracle"],"metadata_filters":null}]',
        encoding="utf-8",
    )
    with public_corpus_session() as db:
        import_curated_public_corpus(db, InMemoryPrivateObjectStorage(), knowledge_base_path=root)
        summary = evaluate_durable_public_retrieval(db, dataset_path=dataset)

    assert summary.pass_rate == 1.0
    assert summary.source_coverage == 1.0
    assert summary.precision_at_k == 1.0
    assert summary.recall == 1.0
    assert summary.citation_issue_count == 0


def test_durable_evaluation_uses_declared_lineage_without_an_expected_protocol_filter(
    public_corpus_session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _curated_root(tmp_path, "## Oracle Safety\nOracle safeguards protect liquidation calculations.")
    dataset = tmp_path / "eval.json"
    with public_corpus_session() as db:
        import_curated_public_corpus(db, InMemoryPrivateObjectStorage(), knowledge_base_path=root)
        source = db.execute(select(KnowledgeSourceModel)).scalar_one()
        chunk = db.execute(select(KnowledgeChunkModel)).scalar_one()
        dataset.write_text(
            (
                "["
                '{"id":"oracle","query":"oracle safeguards","expected_protocol":"wrong",'
                '"expected_terms":["oracle"],"metadata_filters":null,'
                f'"relevant_source_ids":["{source.id}"],"relevant_chunk_ids":["{chunk.id}"],'
                '"expect_empty":false},'
                '{"id":"no-answer","query":"quantum satellite manufacturing",'
                '"expected_protocol":null,"expected_terms":[],"metadata_filters":null,'
                '"relevant_source_ids":[],"relevant_chunk_ids":[],"expect_empty":true}'
                "]"
            ),
            encoding="utf-8",
        )
        from app.knowledge import retrieval_evaluation

        original = retrieval_evaluation.retrieve_public_durable_context

        def assert_unfiltered(session, query, *, protocols=None, top_k=3):
            assert protocols is None
            return original(session, query, protocols=protocols, top_k=top_k)

        monkeypatch.setattr(
            retrieval_evaluation,
            "retrieve_public_durable_context",
            assert_unfiltered,
        )
        summary = evaluate_durable_public_retrieval(db, dataset_path=dataset)

    assert summary.pass_rate == 1.0
    assert summary.precision_at_k == 1.0
    assert summary.recall == 1.0
    assert summary.expected_empty_cases == summary.correct_empty_cases == 1
    assert summary.cases[0]["top_protocol"] == "aave"
    assert summary.cases[0]["matched_reference_ids"]
    assert summary.cases[1]["retrieved_chunk_ids"] == []
