from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user, user_context
from app.core.config import get_settings
from app.db.base import Base
from app.jobs.cancellation import CancellationContext
from app.knowledge.embedding import LocalDeterministicEmbeddingProvider
from app.knowledge.shadow_retriever import retrieve_shadow_knowledge
from app.models.knowledge import (
    KnowledgeChunkEmbeddingModel,
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeEmbeddingGenerationModel,
    KnowledgeEmbeddingProfileModel,
    KnowledgeRetrievalEventModel,
    KnowledgeSourceModel,
)
from app.models.organization import OrganizationMembershipModel, OrganizationModel


@pytest.fixture()
def shadow_session(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("WORKER_API_ENABLED", "true")
    monkeypatch.setenv("KNOWLEDGE_EMBEDDINGS_ENABLED", "true")
    monkeypatch.setenv("KNOWLEDGE_SHADOW_RETRIEVAL_ENABLED", "true")
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


def test_shadow_retrieval_applies_tenant_lifecycle_and_current_version_filters_before_ranking(
    shadow_session,
) -> None:
    Session = shadow_session
    with Session() as db:
        owner = create_user(db, "phase18e-owner@example.test")
        member = create_user(db, "phase18e-member@example.test")
        outsider = create_user(db, "phase18e-outsider@example.test")
        organization = OrganizationModel(
            id="org_phase18e",
            name="Phase 18E Organization",
            slug="phase-18e-organization",
            status="active",
            created_by_user_id=owner.id,
        )
        db.add(organization)
        db.add_all(
            [
                OrganizationMembershipModel(
                    id="mbr_phase18e_owner",
                    organization_id=organization.id,
                    user_id=owner.id,
                    role="owner",
                    status="active",
                ),
                OrganizationMembershipModel(
                    id="mbr_phase18e_member",
                    organization_id=organization.id,
                    user_id=member.id,
                    role="viewer",
                    status="active",
                ),
            ]
        )
        _profile(db)
        _add_retrievable_document(db, "public", owner.id, None, "public source", "public oracle safeguards")
        _add_retrievable_document(db, "private-owner", owner.id, None, "owner private", "owner private liquidation detail")
        _add_retrievable_document(db, "organization", owner.id, organization.id, "organization source", "organization health factor")
        _add_retrievable_document(db, "private-outsider", outsider.id, None, "outsider private", "secret outsider alpha")
        _add_retrievable_document(db, "tombstoned", owner.id, None, "tombstoned", "removed source text", tombstoned=True)
        _add_retrievable_document(db, "superseded", owner.id, None, "superseded", "old version should not return", current=False)
        db.commit()

        member_result = retrieve_shadow_knowledge(
            db, user_context(member), query="liquidation oracle health", top_k=10, protocols=[], request_id="req-member"
        )
        assert {item.citation.source_id for item in member_result.items} == {"ksrc_public", "ksrc_organization"}

        outsider_result = retrieve_shadow_knowledge(
            db, user_context(outsider), query="liquidation oracle health", top_k=10, protocols=[], request_id="req-outsider"
        )
        assert {item.citation.source_id for item in outsider_result.items} == {"ksrc_public", "ksrc_private-outsider"}

        membership = db.get(OrganizationMembershipModel, "mbr_phase18e_member")
        assert membership is not None
        membership.status = "removed"
        db.flush()
        removed_member_result = retrieve_shadow_knowledge(
            db, user_context(member), query="organization health", top_k=10, protocols=[], request_id="req-removed"
        )
        assert {item.citation.source_id for item in removed_member_result.items} == {"ksrc_public"}


def test_shadow_citations_bind_exact_chunk_and_version_checksums_and_events_exclude_raw_query(
    shadow_session,
) -> None:
    Session = shadow_session
    query = "private oracle safety"
    with Session() as db:
        owner = create_user(db, "phase18e-citation@example.test")
        _profile(db)
        _add_retrievable_document(db, "citation", owner.id, None, "citation source", "private oracle safety controls")
        db.commit()
        result = retrieve_shadow_knowledge(
            db, user_context(owner), query=query, top_k=4, protocols=[], request_id="req-citation"
        )
        assert len(result.items) == 1
        citation = result.items[0].citation
        assert citation.document_version_id == "kver_citation"
        assert citation.document_version_checksum == "a" * 64
        assert citation.chunk_checksum == sha256(b"private oracle safety controls").hexdigest()
        assert citation.citation_id.startswith("kcite_")
        event = db.get(KnowledgeRetrievalEventModel, result.retrieval_event_id)
        assert event is not None
        assert event.query_hash == sha256(query.encode("utf-8")).hexdigest()
        assert query not in str(event.filters_json)
        assert query not in str(event.retrieved_chunk_ids)
        assert event.retriever_version == "phase18e.pgvector-shadow.v1"


def test_shadow_retrieval_excludes_corrupt_citation_lineage(shadow_session) -> None:
    Session = shadow_session
    with Session() as db:
        owner = create_user(db, "phase18e-corrupt@example.test")
        _profile(db)
        _add_retrievable_document(db, "valid", owner.id, None, "valid", "valid integrity content")
        _add_retrievable_document(db, "corrupt", owner.id, None, "corrupt", "corrupt integrity content")
        db.flush()
        corrupt = db.get(KnowledgeChunkEmbeddingModel, "kembed_corrupt")
        assert corrupt is not None
        corrupt.content_checksum = "0" * 64
        db.commit()
        result = retrieve_shadow_knowledge(
            db, user_context(owner), query="integrity", top_k=10, protocols=[], request_id="req-corrupt"
        )
        assert [item.citation.source_id for item in result.items] == ["ksrc_valid"]


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
    db.flush()


def _add_retrievable_document(
    db,
    suffix: str,
    owner_id: str,
    organization_id: str | None,
    title: str,
    content: str,
    *,
    tombstoned: bool = False,
    current: bool = True,
) -> None:
    now = datetime.now(UTC)
    visibility = "organization" if organization_id else ("public" if suffix == "public" else "private")
    source = KnowledgeSourceModel(
        id=f"ksrc_{suffix}",
        owner_user_id=None if visibility == "public" else owner_id,
        organization_id=organization_id,
        visibility=visibility,
        source_type="upload",
        title=title,
        protocol="aave",
        status="ingested",
        trust_state="approved_for_rag",
        created_by_user_id=owner_id,
        deleted_at=now if tombstoned else None,
    )
    document = KnowledgeDocumentModel(
        id=f"kdoc_{suffix}",
        knowledge_source_id=source.id,
        current_version_id=f"kver_{suffix}" if current else f"kver_{suffix}_new",
        filename="source.md",
        media_type="text/markdown",
        status="ready",
    )
    version = KnowledgeDocumentVersionModel(
        id=f"kver_{suffix}",
        document_id=document.id,
        version_number=1,
        storage_key=f"knowledge/{suffix}/source.md",
        checksum="a" * 64,
        size_bytes=len(content),
        status="ready" if current else "superseded",
        superseded_at=None if current else now,
        active_embedding_profile_id="kembprof_local_hash_384_v1",
    )
    chunk_checksum = sha256(content.encode("utf-8")).hexdigest()
    chunk = KnowledgeChunkModel(
        id=f"kchunk_{suffix}",
        document_version_id=version.id,
        chunk_index=0,
        heading_path=[title],
        content=content,
        content_checksum=chunk_checksum,
        token_count=len(content.split()),
    )
    generation = KnowledgeEmbeddingGenerationModel(
        id=f"kgen_{suffix}",
        document_version_id=version.id,
        embedding_profile_id="kembprof_local_hash_384_v1",
        status="completed",
        expected_chunk_count=1,
        completed_chunk_count=1,
        content_checksum=chunk_checksum,
        completed_at=now,
    )
    vector = LocalDeterministicEmbeddingProvider().embed(content, CancellationContext())
    embedding = KnowledgeChunkEmbeddingModel(
        id=f"kembed_{suffix}",
        knowledge_chunk_id=chunk.id,
        embedding_profile_id="kembprof_local_hash_384_v1",
        embedding_generation_id=generation.id,
        content_checksum=chunk_checksum,
        dimensions=384,
        embedding_json=vector,
        status="completed",
    )
    db.add_all([source, document, version, chunk, generation, embedding])
    if not current:
        db.add(
            KnowledgeDocumentVersionModel(
                id=f"kver_{suffix}_new",
                document_id=document.id,
                version_number=2,
                storage_key=f"knowledge/{suffix}/new.md",
                checksum="b" * 64,
                size_bytes=1,
                status="ready",
            )
        )
