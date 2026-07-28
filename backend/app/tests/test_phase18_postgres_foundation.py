from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.auth.service import create_user, user_context
from app.db.session import create_database_engine
from app.knowledge.access import (
    create_knowledge_source,
    get_visible_knowledge_source,
    list_visible_knowledge_sources,
)
from app.core.config import get_settings
from app.jobs.cancellation import CancellationContext
from app.knowledge.embedding import LocalDeterministicEmbeddingProvider, vector_literal
from app.knowledge.public_corpus import import_curated_public_corpus
from app.knowledge.public_retriever import retrieve_public_durable_context
from app.knowledge.shadow_retriever import _eligible_embeddings, retrieve_shadow_knowledge
from app.models.knowledge import (
    KnowledgeChunkEmbeddingModel,
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeEmbeddingGenerationModel,
    KnowledgeSourceModel,
)
from app.models.organization import OrganizationMembershipModel, OrganizationModel
from app.models.user import UserModel
from app.storage.memory import InMemoryPrivateObjectStorage


pytestmark = pytest.mark.postgres_integration


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 18 PostgreSQL tests require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("Phase 18 PostgreSQL tests require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_postgres_knowledge_scope_constraints_and_organization_isolation(
    postgres_sessions: sessionmaker,
) -> None:
    suffix = uuid4().hex[:10]
    with postgres_sessions() as db:
        owner = create_user(db, f"phase18-pg-owner-{suffix}@example.test")
        member = create_user(db, f"phase18-pg-member-{suffix}@example.test")
        outsider = create_user(db, f"phase18-pg-outsider-{suffix}@example.test")
        organization = OrganizationModel(
            id=f"org_phase18_pg_{suffix}",
            name="Phase 18 PostgreSQL",
            slug=f"phase-18-pg-{suffix}",
            status="active",
            created_by_user_id=owner.id,
        )
        db.add(organization)
        db.flush()
        db.add_all(
            [
                OrganizationMembershipModel(
                    id=f"mbr_phase18_pg_owner_{suffix}",
                    organization_id=organization.id,
                    user_id=owner.id,
                    role="owner",
                    status="active",
                ),
                OrganizationMembershipModel(
                    id=f"mbr_phase18_pg_member_{suffix}",
                    organization_id=organization.id,
                    user_id=member.id,
                    role="viewer",
                    status="active",
                ),
            ]
        )
        db.commit()
        ids = {
            "owner": owner.id,
            "member": member.id,
            "outsider": outsider.id,
            "organization": organization.id,
        }

    try:
        with postgres_sessions() as db:
            owner = db.get(UserModel, ids["owner"])
            member = db.get(UserModel, ids["member"])
            outsider = db.get(UserModel, ids["outsider"])
            source = create_knowledge_source(
                db,
                user_context(owner),
                visibility="organization",
                organization_id=ids["organization"],
                title="PostgreSQL tenant source",
                source_type="upload",
            )
            db.commit()
            source_id = source.id

            assert get_visible_knowledge_source(
                db,
                user_context(member),
                source_id,
            ).id == source_id
            assert list_visible_knowledge_sources(db, user_context(outsider)) == []

            invalid = KnowledgeSourceModel(
                id=f"ksrc_invalid_{suffix}",
                owner_user_id=ids["owner"],
                organization_id=ids["organization"],
                visibility="private",
                source_type="upload",
                title="Invalid mixed tenant scope",
                status="registered",
                trust_state="needs_review",
                created_by_user_id=ids["owner"],
            )
            db.add(invalid)
            with pytest.raises(IntegrityError) as constraint_error:
                db.flush()
            assert "ck_knowledge_sources_scope" in str(constraint_error.value)
            db.rollback()

            membership = db.execute(
                select(OrganizationMembershipModel)
                .where(
                    OrganizationMembershipModel.organization_id == ids["organization"]
                )
                .where(OrganizationMembershipModel.user_id == ids["member"])
            ).scalars().one()
            membership.status = "removed"
            db.commit()
            assert list_visible_knowledge_sources(db, user_context(member)) == []
    finally:
        with postgres_sessions() as db:
            db.execute(
                delete(KnowledgeSourceModel).where(
                    KnowledgeSourceModel.organization_id == ids["organization"]
                )
            )
            db.execute(
                delete(OrganizationMembershipModel).where(
                    OrganizationMembershipModel.organization_id == ids["organization"]
                )
            )
            db.execute(
                delete(OrganizationModel).where(
                    OrganizationModel.id == ids["organization"]
                )
            )
            db.execute(
                delete(UserModel).where(
                    UserModel.id.in_(
                        {ids["owner"], ids["member"], ids["outsider"]}
                    )
                )
            )
            db.commit()


def test_postgres_pgvector_extension_and_embedding_index_are_present(
    postgres_sessions: sessionmaker,
) -> None:
    with postgres_sessions() as db:
        extension = db.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one_or_none()
        assert extension == "vector"
        vector_column = db.execute(
            text(
                "SELECT format_type(a.atttypid, a.atttypmod) "
                "FROM pg_attribute a "
                "JOIN pg_class c ON c.oid = a.attrelid "
                "WHERE c.relname = 'knowledge_chunk_embeddings' "
                "AND a.attname = 'embedding_vector' AND a.attnum > 0"
            )
        ).scalar_one()
        assert vector_column == "vector(384)"
        index_definition = db.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE tablename = 'knowledge_chunk_embeddings' "
                "AND indexname = 'ix_knowledge_chunk_embeddings_vector_hnsw'"
            )
        ).scalar_one()
        assert "USING hnsw" in index_definition
        assert "vector_cosine_ops" in index_definition
        vector = "[1" + ",0" * 383 + "]"
        distance = db.execute(
            text("SELECT CAST(:left AS vector) <=> CAST(:right AS vector)"),
            {"left": vector, "right": vector},
        ).scalar_one()
        assert distance == 0


def test_postgres_shadow_retrieval_filters_tenants_before_pgvector_ranking(
    postgres_sessions: sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("WORKER_API_ENABLED", "true")
    monkeypatch.setenv("KNOWLEDGE_EMBEDDINGS_ENABLED", "true")
    monkeypatch.setenv("KNOWLEDGE_SHADOW_RETRIEVAL_ENABLED", "true")
    get_settings.cache_clear()
    suffix = uuid4().hex[:10]
    ids: dict[str, str] = {}
    try:
        with postgres_sessions() as db:
            owner = create_user(db, f"phase18e-pg-owner-{suffix}@example.test")
            member = create_user(db, f"phase18e-pg-member-{suffix}@example.test")
            outsider = create_user(db, f"phase18e-pg-outsider-{suffix}@example.test")
            organization = OrganizationModel(
                id=f"org_phase18e_pg_{suffix}",
                name="Phase 18E PostgreSQL",
                slug=f"phase-18e-pg-{suffix}",
                status="active",
                created_by_user_id=owner.id,
            )
            db.add(organization)
            db.flush()
            db.add(
                OrganizationMembershipModel(
                    id=f"mbr_phase18e_pg_{suffix}",
                    organization_id=organization.id,
                    user_id=member.id,
                    role="viewer",
                    status="active",
                )
            )
            db.flush()
            _add_pgvector_document(db, suffix, "organization", owner.id, organization.id, "organization only health factor")
            _add_pgvector_document(db, suffix, "private", owner.id, None, "owner private liquidation data")
            _add_pgvector_document(db, suffix, "public", owner.id, None, "public oracle safeguards", public=True)
            db.commit()
            ids = {"owner": owner.id, "member": member.id, "outsider": outsider.id, "org": organization.id}

            member_result = retrieve_shadow_knowledge(
                db, user_context(member), query="health factor", top_k=10, protocols=[], request_id=f"pg-member-{suffix}"
            )
            assert {item.citation.source_id for item in member_result.items} == {
                f"ksrc_phase18e_pg_{suffix}_organization",
                f"ksrc_phase18e_pg_{suffix}_public",
            }
            outsider_result = retrieve_shadow_knowledge(
                db, user_context(outsider), query="health factor", top_k=10, protocols=[], request_id=f"pg-outsider-{suffix}"
            )
            assert {item.citation.source_id for item in outsider_result.items} == {f"ksrc_phase18e_pg_{suffix}_public"}
            membership = db.get(OrganizationMembershipModel, f"mbr_phase18e_pg_{suffix}")
            assert membership is not None
            membership.status = "removed"
            db.flush()
            revoked_result = retrieve_shadow_knowledge(
                db, user_context(member), query="health factor", top_k=10, protocols=[], request_id=f"pg-revoked-{suffix}"
            )
            assert {item.citation.source_id for item in revoked_result.items} == {f"ksrc_phase18e_pg_{suffix}_public"}
    finally:
        if ids:
            with postgres_sessions() as db:
                db.execute(delete(KnowledgeChunkEmbeddingModel).where(KnowledgeChunkEmbeddingModel.id.like(f"kembed_phase18e_pg_{suffix}%")))
                db.execute(delete(KnowledgeEmbeddingGenerationModel).where(KnowledgeEmbeddingGenerationModel.id.like(f"kgen_phase18e_pg_{suffix}%")))
                db.execute(delete(KnowledgeChunkModel).where(KnowledgeChunkModel.id.like(f"kchunk_phase18e_pg_{suffix}%")))
                db.execute(delete(KnowledgeDocumentVersionModel).where(KnowledgeDocumentVersionModel.id.like(f"kver_phase18e_pg_{suffix}%")))
                db.execute(delete(KnowledgeDocumentModel).where(KnowledgeDocumentModel.id.like(f"kdoc_phase18e_pg_{suffix}%")))
                db.execute(delete(KnowledgeSourceModel).where(KnowledgeSourceModel.id.like(f"ksrc_phase18e_pg_{suffix}%")))
                db.execute(delete(OrganizationMembershipModel).where(OrganizationMembershipModel.organization_id == ids["org"]))
                db.execute(delete(OrganizationModel).where(OrganizationModel.id == ids["org"]))
                db.execute(delete(UserModel).where(UserModel.id.in_({ids["owner"], ids["member"], ids["outsider"]})))
                db.commit()
        get_settings.cache_clear()


def test_postgres_curated_import_populates_pgvector_and_retrieves_public_only(
    postgres_sessions: sessionmaker,
) -> None:
    """The Phase 18G importer must populate the actual pgvector ranking field."""

    with postgres_sessions() as db:
        try:
            summary = import_curated_public_corpus(db, InMemoryPrivateObjectStorage())
            results = retrieve_public_durable_context(
                db,
                "What is Health Factor?",
                protocols=["aave"],
            )
            populated_vectors = db.execute(
                text(
                    "SELECT count(*) FROM knowledge_chunk_embeddings "
                    "WHERE id LIKE 'kemb_pub_%' AND embedding_vector IS NOT NULL"
                )
            ).scalar_one()
            assert summary.documents_seen >= 1
            assert results and results[0].metadata["protocol"] == "aave"
            assert populated_vectors >= len(results)
        finally:
            # Curated bootstrap evaluation must not persist rows in the shared
            # integration database.
            db.rollback()


def test_postgres_generation_pointer_supports_same_profile_rollback_and_exact_retrieval(
    postgres_sessions: sessionmaker,
) -> None:
    suffix = uuid4().hex[:10]
    owner_id = ""
    try:
        with postgres_sessions() as db:
            owner = create_user(db, f"phase18-generation-{suffix}@example.test")
            owner_id = owner.id
            _add_pgvector_document(
                db,
                suffix,
                "private",
                owner.id,
                None,
                "generation rollback oracle controls",
            )
            version_id = f"kver_phase18e_pg_{suffix}_private"
            chunk_id = f"kchunk_phase18e_pg_{suffix}_private"
            active_generation_id = f"kgen_phase18e_pg_{suffix}_private"
            second_generation_id = f"kgen_phase18e_pg_{suffix}_private_second"
            version = db.get(KnowledgeDocumentVersionModel, version_id)
            chunk = db.get(KnowledgeChunkModel, chunk_id)
            assert version is not None and chunk is not None
            values = LocalDeterministicEmbeddingProvider().embed(
                chunk.content, CancellationContext()
            )
            second_generation = KnowledgeEmbeddingGenerationModel(
                id=second_generation_id,
                document_version_id=version_id,
                embedding_profile_id="kembprof_local_hash_384_v1",
                status="completed",
                expected_chunk_count=1,
                completed_chunk_count=1,
                content_checksum=chunk.content_checksum,
            )
            second_embedding = KnowledgeChunkEmbeddingModel(
                id=f"kembed_phase18e_pg_{suffix}_private_second",
                knowledge_chunk_id=chunk_id,
                embedding_profile_id="kembprof_local_hash_384_v1",
                embedding_generation_id=second_generation_id,
                content_checksum=chunk.content_checksum,
                dimensions=384,
                embedding_json=values,
                status="completed",
            )
            db.add(second_generation)
            db.flush()
            db.add(second_embedding)
            db.flush()
            db.execute(
                text(
                    "UPDATE knowledge_chunk_embeddings SET embedding_vector = "
                    "CAST(:vector AS vector) WHERE id = :id"
                ),
                {"vector": vector_literal(values), "id": second_embedding.id},
            )
            version.active_embedding_generation_id = second_generation_id
            db.commit()

        with postgres_sessions() as db:
            owner = db.get(UserModel, owner_id)
            assert owner is not None
            query_embedding = LocalDeterministicEmbeddingProvider().embed(
                "generation rollback oracle controls", CancellationContext()
            )
            active_rows = _eligible_embeddings(
                db,
                user_context(owner),
                protocol_filter=["aave"],
                query_embedding=query_embedding,
                top_k=4,
            )
            assert [row[4].embedding_generation_id for row in active_rows] == [
                second_generation_id
            ]
            version = db.get(KnowledgeDocumentVersionModel, version_id)
            assert version is not None
            version.active_embedding_generation_id = active_generation_id
            db.commit()

            reverted_rows = _eligible_embeddings(
                db,
                user_context(owner),
                protocol_filter=["aave"],
                query_embedding=query_embedding,
                top_k=4,
            )
            assert [row[4].embedding_generation_id for row in reverted_rows] == [
                active_generation_id
            ]
    finally:
        with postgres_sessions() as db:
            db.execute(
                delete(KnowledgeChunkEmbeddingModel).where(
                    KnowledgeChunkEmbeddingModel.id.like(f"kembed_phase18e_pg_{suffix}%")
                )
            )
            db.execute(
                delete(KnowledgeEmbeddingGenerationModel).where(
                    KnowledgeEmbeddingGenerationModel.id.like(f"kgen_phase18e_pg_{suffix}%")
                )
            )
            db.execute(
                delete(KnowledgeChunkModel).where(
                    KnowledgeChunkModel.id.like(f"kchunk_phase18e_pg_{suffix}%")
                )
            )
            db.execute(
                delete(KnowledgeDocumentVersionModel).where(
                    KnowledgeDocumentVersionModel.id.like(f"kver_phase18e_pg_{suffix}%")
                )
            )
            db.execute(
                delete(KnowledgeDocumentModel).where(
                    KnowledgeDocumentModel.id.like(f"kdoc_phase18e_pg_{suffix}%")
                )
            )
            db.execute(
                delete(KnowledgeSourceModel).where(
                    KnowledgeSourceModel.id.like(f"ksrc_phase18e_pg_{suffix}%")
                )
            )
            if owner_id:
                db.execute(delete(UserModel).where(UserModel.id == owner_id))
            db.commit()


def _add_pgvector_document(
    db,
    suffix: str,
    kind: str,
    owner_id: str,
    organization_id: str | None,
    content: str,
    *,
    public: bool = False,
) -> None:
    from hashlib import sha256

    source_id = f"ksrc_phase18e_pg_{suffix}_{kind}"
    document_id = f"kdoc_phase18e_pg_{suffix}_{kind}"
    version_id = f"kver_phase18e_pg_{suffix}_{kind}"
    chunk_id = f"kchunk_phase18e_pg_{suffix}_{kind}"
    generation_id = f"kgen_phase18e_pg_{suffix}_{kind}"
    embedding_id = f"kembed_phase18e_pg_{suffix}_{kind}"
    checksum = sha256(content.encode("utf-8")).hexdigest()
    source = KnowledgeSourceModel(
        id=source_id,
        owner_user_id=None if public else owner_id,
        organization_id=organization_id,
        visibility="public" if public else ("organization" if organization_id else "private"),
        source_type="upload",
        title=f"Phase 18E {kind}",
        protocol="aave",
        status="ingested",
        trust_state="approved_for_rag",
        created_by_user_id=owner_id,
    )
    document = KnowledgeDocumentModel(id=document_id, knowledge_source_id=source_id, current_version_id=version_id, filename="source.md", media_type="text/markdown", status="ready")
    version = KnowledgeDocumentVersionModel(id=version_id, document_id=document_id, version_number=1, storage_key=f"knowledge/{suffix}/{kind}", checksum="a" * 64, size_bytes=len(content), status="ready", active_embedding_profile_id="kembprof_local_hash_384_v1", active_embedding_generation_id=generation_id)
    chunk = KnowledgeChunkModel(id=chunk_id, document_version_id=version_id, chunk_index=0, heading_path=[kind], content=content, content_checksum=checksum, token_count=len(content.split()))
    generation = KnowledgeEmbeddingGenerationModel(id=generation_id, document_version_id=version_id, embedding_profile_id="kembprof_local_hash_384_v1", status="completed", expected_chunk_count=1, completed_chunk_count=1, content_checksum=checksum)
    values = LocalDeterministicEmbeddingProvider().embed(content, CancellationContext())
    embedding = KnowledgeChunkEmbeddingModel(id=embedding_id, knowledge_chunk_id=chunk_id, embedding_profile_id="kembprof_local_hash_384_v1", embedding_generation_id=generation_id, content_checksum=checksum, dimensions=384, embedding_json=values, status="completed")
    # The test models intentionally have no ORM relationships; flush the
    # parent rows before the embedding foreign keys on PostgreSQL.
    db.add(source)
    db.flush()
    db.add(document)
    db.flush()
    db.add(version)
    db.flush()
    db.add_all([chunk, generation])
    db.flush()
    db.add(embedding)
    db.flush()
    db.execute(
        text("UPDATE knowledge_chunk_embeddings SET embedding_vector = CAST(:vector AS vector) WHERE id = :id"),
        {"vector": vector_literal(values), "id": embedding_id},
    )
