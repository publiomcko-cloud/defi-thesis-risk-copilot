from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.orchestrator import run_analysis_workflow
from app.auth.service import create_user, demo_common_context, user_context
from app.core.config import get_settings
from app.db.base import Base
from app.jobs.cancellation import CancellationContext
from app.knowledge.embedding import LocalDeterministicEmbeddingProvider
from app.knowledge.shadow_retriever import retrieve_durable_analysis_context
from app.models.knowledge import (
    KnowledgeChunkEmbeddingModel,
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeEmbeddingGenerationModel,
    KnowledgeEmbeddingProfileModel,
    KnowledgeSourceModel,
)
from app.models.organization import OrganizationMembershipModel, OrganizationModel
from app.schemas.analysis import AnalysisRequest


@pytest.fixture()
def durable_analysis_session(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("WORKER_API_ENABLED", "true")
    monkeypatch.setenv("KNOWLEDGE_EMBEDDINGS_ENABLED", "true")
    monkeypatch.setenv("KNOWLEDGE_SHADOW_RETRIEVAL_ENABLED", "true")
    monkeypatch.setenv("KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED", "true")
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        yield Session
    finally:
        get_settings.cache_clear()


def test_authenticated_analysis_uses_only_server_derived_tenant_context_and_lineage(
    durable_analysis_session,
) -> None:
    Session = durable_analysis_session
    with Session() as db:
        owner = create_user(db, "phase18-final-owner@example.test")
        member = create_user(db, "phase18-final-member@example.test")
        outsider = create_user(db, "phase18-final-outsider@example.test")
        organization = OrganizationModel(
            id="org_phase18_final",
            name="Phase 18 Final",
            slug="phase-18-final",
            status="active",
            created_by_user_id=owner.id,
        )
        db.add_all(
            [
                organization,
                OrganizationMembershipModel(
                    id="mbr_phase18_final_owner",
                    organization_id=organization.id,
                    user_id=owner.id,
                    role="owner",
                    status="active",
                ),
                OrganizationMembershipModel(
                    id="mbr_phase18_final_member",
                    organization_id=organization.id,
                    user_id=member.id,
                    role="viewer",
                    status="active",
                ),
            ]
        )
        _profile(db)
        public = _add_document(db, "public", None, None, "public oracle safety", public=True)
        private = _add_document(db, "owner", owner.id, None, "owner liquidation controls")
        organization_source = _add_document(
            db, "organization", owner.id, organization.id, "organization health factor"
        )
        outsider_source = _add_document(db, "outsider", outsider.id, None, "outsider secret alpha")
        _add_document(db, "deleted", owner.id, None, "deleted oracle record", deleted=True)
        _add_document(db, "superseded", owner.id, None, "superseded oracle record", current=False)
        _add_document(db, "stale", owner.id, None, "stale generation record", stale_generation=True)
        db.commit()

        owner_results = retrieve_durable_analysis_context(
            db, user_context(owner), query="oracle liquidation health factor", top_k=10
        )
        assert {item.metadata["citation_lineage"]["source_id"] for item in owner_results} == {
            public,
            private,
            organization_source,
            "ksrc_stale",
        }
        assert all("storage_key" not in str(item.metadata) for item in owner_results)

        member_results = retrieve_durable_analysis_context(
            db, user_context(member), query="oracle liquidation health factor", top_k=10
        )
        assert {item.metadata["citation_lineage"]["source_id"] for item in member_results} == {
            public,
            organization_source,
        }

        outsider_results = retrieve_durable_analysis_context(
            db, user_context(outsider), query="oracle liquidation health factor", top_k=10
        )
        assert {item.metadata["citation_lineage"]["source_id"] for item in outsider_results} == {
            public,
            outsider_source,
        }

        anonymous_results = retrieve_durable_analysis_context(
            db, demo_common_context(), query="oracle liquidation health factor", top_k=10
        )
        assert {item.metadata["citation_lineage"]["source_id"] for item in anonymous_results} == {public}

        report = run_analysis_workflow(
            AnalysisRequest(
                strategy_description="Evaluate oracle liquidation health factor safeguards.",
                protocols=["aave"],
                manual_inputs={},
                analysis_depth="standard",
            ),
            "report_phase18_final",
            db,
            actor=user_context(owner),
        ).report
        report_source_ids = {
            source.citation_lineage.source_id
            for source in report.sources
            if source.citation_lineage is not None
        }
        assert outsider_source not in report_source_ids
        assert private in report_source_ids
        assert organization_source in report_source_ids

        # A protocol filter with no trusted rows is an explicit no-answer,
        # instead of silently returning a caller's unrelated tenant content.
        assert retrieve_durable_analysis_context(
            db, user_context(owner), query="unknown", protocols=["not-a-protocol"], top_k=4
        ) == []


def test_durable_retrieval_overfetches_before_discarding_corrupt_lineage(
    durable_analysis_session,
) -> None:
    Session = durable_analysis_session
    with Session() as db:
        owner = create_user(db, "phase18-final-overfetch@example.test")
        _profile(db)
        valid = _add_document(db, "valid-overfetch", owner.id, None, "oracle safety controls")
        corrupt = _add_document(db, "corrupt-overfetch", owner.id, None, "oracle safety controls")
        db.flush()
        corrupt_embedding = db.get(KnowledgeChunkEmbeddingModel, "kemb_corrupt-overfetch_active")
        assert corrupt_embedding is not None
        corrupt_embedding.content_checksum = "0" * 64
        db.commit()

        results = retrieve_durable_analysis_context(
            db, user_context(owner), query="oracle safety controls", top_k=1
        )
        assert len(results) == 1
        assert results[0].metadata["citation_lineage"]["source_id"] == valid
        assert results[0].metadata["citation_lineage"]["source_id"] != corrupt


def _profile(db) -> None:
    db.add(
        KnowledgeEmbeddingProfileModel(
            id="kembprof_local_hash_384_v1",
            provider="local_deterministic",
            model="local-hash-384-v1",
            dimensions=384,
            status="active",
            is_active=True,
        )
    )


def _add_document(
    db,
    suffix: str,
    owner_id: str | None,
    organization_id: str | None,
    content: str,
    *,
    public: bool = False,
    deleted: bool = False,
    current: bool = True,
    stale_generation: bool = False,
) -> str:
    now = datetime.now(UTC)
    source_id = f"ksrc_{suffix}"
    document_id = f"kdoc_{suffix}"
    version_id = f"kver_{suffix}"
    generation_id = f"kembgen_{suffix}_active"
    visibility = "public" if public else ("organization" if organization_id else "private")
    source = KnowledgeSourceModel(
        id=source_id,
        owner_user_id=None if public else owner_id,
        organization_id=organization_id,
        visibility=visibility,
        source_type="curated_markdown" if public else "upload",
        title=f"{suffix} source",
        protocol="aave",
        status="ingested",
        trust_state="approved_for_rag",
        created_by_user_id=owner_id,
        deleted_at=now if deleted else None,
    )
    document = KnowledgeDocumentModel(
        id=document_id,
        knowledge_source_id=source_id,
        current_version_id=version_id if current else f"{version_id}_current",
        filename=f"{suffix}.md",
        media_type="text/markdown",
        status="ready",
    )
    version = KnowledgeDocumentVersionModel(
        id=version_id,
        document_id=document_id,
        version_number=1,
        storage_key=f"knowledge/private/{suffix}/original",
        checksum="a" * 64,
        size_bytes=len(content),
        status="ready" if current else "superseded",
        superseded_at=None if current else now,
        active_embedding_profile_id="kembprof_local_hash_384_v1",
        active_embedding_generation_id=generation_id,
    )
    checksum = sha256(content.encode()).hexdigest()
    chunk = KnowledgeChunkModel(
        id=f"kchunk_{suffix}",
        document_version_id=version_id,
        chunk_index=0,
        heading_path=[suffix],
        content=content,
        content_checksum=checksum,
        token_count=len(content.split()),
    )
    generation = KnowledgeEmbeddingGenerationModel(
        id=generation_id,
        document_version_id=version_id,
        embedding_profile_id="kembprof_local_hash_384_v1",
        status="completed",
        expected_chunk_count=1,
        completed_chunk_count=1,
        content_checksum=checksum,
        completed_at=now,
    )
    values = LocalDeterministicEmbeddingProvider().embed(content, CancellationContext())
    active_embedding = KnowledgeChunkEmbeddingModel(
        id=f"kemb_{suffix}_active",
        knowledge_chunk_id=chunk.id,
        embedding_profile_id="kembprof_local_hash_384_v1",
        embedding_generation_id=generation_id,
        content_checksum=checksum,
        dimensions=384,
        embedding_json=values,
        status="completed",
    )
    db.add_all([source, document, version, chunk, generation, active_embedding])
    if stale_generation:
        stale_generation_record = KnowledgeEmbeddingGenerationModel(
            id=f"kembgen_{suffix}_stale",
            document_version_id=version_id,
            embedding_profile_id="kembprof_local_hash_384_v1",
            status="completed",
            expected_chunk_count=1,
            completed_chunk_count=1,
            content_checksum=checksum,
            completed_at=now,
        )
        db.add(stale_generation_record)
        db.add(
            KnowledgeChunkEmbeddingModel(
                id=f"kemb_{suffix}_stale",
                knowledge_chunk_id=chunk.id,
                embedding_profile_id="kembprof_local_hash_384_v1",
                embedding_generation_id=stale_generation_record.id,
                content_checksum="0" * 64,
                dimensions=384,
                embedding_json=values,
                status="completed",
            )
        )
    if not current:
        db.add(
            KnowledgeDocumentVersionModel(
                id=f"{version_id}_current",
                document_id=document_id,
                version_number=2,
                storage_key=f"knowledge/private/{suffix}/current",
                checksum="b" * 64,
                size_bytes=1,
                status="ready",
            )
        )
    return source_id
