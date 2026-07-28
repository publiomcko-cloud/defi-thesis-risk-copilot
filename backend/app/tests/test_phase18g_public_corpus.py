from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.protocol_research_agent import retrieve_protocol_context
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.knowledge.public_corpus import import_curated_public_corpus, require_public_corpus_import_enabled
from app.knowledge.retrieval_evaluation import evaluate_durable_public_retrieval
from app.knowledge.public_retriever import retrieve_public_durable_context
from app.models.knowledge import KnowledgeDocumentVersionModel, KnowledgeSourceModel
from app.rag.retriever import RetrievalResult
from app.storage.memory import InMemoryPrivateObjectStorage


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
    assert summary.citation_issue_count == 0
