from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user, user_context
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.jobs.cancellation import CancellationContext
from app.jobs.control_service import submit_job
from app.jobs.errors import JobExecutionError
from app.jobs.schemas import JobSubmissionRequest, WorkerLeaseRequest
from app.jobs.worker_protocol import WorkerIdentity, claim_next_job, complete_job, start_job
from app.knowledge.access import create_knowledge_source
from app.knowledge.embedding_executor import (
    DocumentEmbedJobExecutor,
    cleanup_document_embedding_outputs,
    finalize_document_embedding,
)
from app.knowledge.lifecycle_service import promote_document_embedding_generation
from app.knowledge.embedding_service import submit_document_embedding
from app.models.job import JobModel
from app.models.knowledge import (
    KnowledgeChunkEmbeddingModel,
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeEmbeddingGenerationModel,
)
from app.models.user import UserModel
from app.models.worker import WorkerCredentialModel, WorkerModel


@pytest.fixture()
def embedding_session(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("WORKER_API_ENABLED", "true")
    monkeypatch.setenv("KNOWLEDGE_EMBEDDINGS_ENABLED", "true")
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


def test_document_embedding_is_server_owned_idempotent_and_activates_through_worker_protocol(
    embedding_session,
) -> None:
    Session = embedding_session
    owner_id, version_id = _seed_ready_version(Session)
    with Session() as db:
        owner = db.get(UserModel, owner_id)
        job, replayed = submit_document_embedding(db, user_context(owner), version_id, "phase18d-embed-key")
        assert replayed is False
        generation = db.get(KnowledgeEmbeddingGenerationModel, job.result_resource_id)
        assert generation is not None and generation.status == "pending"
        replay, replayed = submit_document_embedding(db, user_context(owner), version_id, "phase18d-embed-key")
        assert replayed is True and replay.id == job.id
        with pytest.raises(HTTPException) as duplicate:
            submit_document_embedding(db, user_context(owner), version_id, "phase18d-other-key")
        assert duplicate.value.status_code == 409
        worker, credential = _worker(db, owner)
        db.commit()
        identity = WorkerIdentity(credential=credential, worker=worker)
        claim = claim_next_job(db, identity)
        assert claim.job is not None and claim.job.id == job.id
        lease = WorkerLeaseRequest(lease_generation=claim.job.lease_generation, lease_token=claim.job.lease_token)
        assert start_job(db, identity, job.id, lease).status == "running"

    result = DocumentEmbedJobExecutor(session_factory=Session).execute(claim.job)
    with Session() as db:
        worker = db.get(WorkerModel, "worker_phase18d")
        credential = db.get(WorkerCredentialModel, "workercred_phase18d")
        assert worker is not None and credential is not None
        finished = complete_job(db, WorkerIdentity(credential=credential, worker=worker), job.id, lease, result)
        assert finished.status == "completed"
        version = db.get(KnowledgeDocumentVersionModel, version_id)
        generation = db.get(KnowledgeEmbeddingGenerationModel, result.result_json["embedding_generation_id"])
        embeddings = db.execute(select(KnowledgeChunkEmbeddingModel)).scalars().all()
        assert version is not None and version.embedding_model == "local-hash-384-v1"
        assert version.embedding_dimensions == 384
        assert generation is not None and generation.status == "completed"
        first_generation_id = generation.id
        assert len(embeddings) == result.result_json["embedding_count"]
        assert all(item.status == "completed" and len(item.embedding_json) == 384 for item in embeddings)

        second_job, replayed = submit_document_embedding(
            db, user_context(db.get(UserModel, owner_id)), version_id, "phase18d-embed-second-key"
        )
        assert replayed is False
        second_generation = db.get(KnowledgeEmbeddingGenerationModel, second_job.result_resource_id)
        assert second_generation is not None and second_generation.id != first_generation_id
        assert generation.status == "completed"
        second_job_id = second_job.id
        db.commit()

    with Session() as db:
        second_job = db.get(JobModel, second_job_id)
        assert second_job is not None
        second_claim = _claimed_job(second_job)
    second_result = DocumentEmbedJobExecutor(session_factory=Session).execute(second_claim)
    with Session() as db:
        second_job = db.get(JobModel, second_job_id)
        assert second_job is not None
        finalize_document_embedding(db, second_job, second_result.result_json)
        db.commit()
        version = db.get(KnowledgeDocumentVersionModel, version_id)
        assert version is not None
        assert version.active_embedding_generation_id == second_result.result_json["embedding_generation_id"]
        assert db.get(KnowledgeEmbeddingGenerationModel, first_generation_id).status == "completed"
        assert len(db.execute(select(KnowledgeChunkEmbeddingModel)).scalars().all()) == 4

        owner = db.get(UserModel, owner_id)
        assert owner is not None
        reverted = promote_document_embedding_generation(db, user_context(owner), version_id, first_generation_id)
        assert reverted.active_embedding_generation_id == first_generation_id


def test_embedding_cleanup_and_dimension_mismatch_never_activate_partial_vectors(
    embedding_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Session = embedding_session
    owner_id, version_id = _seed_ready_version(Session)
    with Session() as db:
        owner = db.get(UserModel, owner_id)
        job, _ = submit_document_embedding(db, user_context(owner), version_id, "phase18d-cleanup-key")
        generation_id = job.result_resource_id
        claimed = _claimed_job(job)
    executor = DocumentEmbedJobExecutor(session_factory=Session)
    executor.execute(claimed)
    with Session() as db:
        cleanup_document_embedding_outputs(db, generation_id, retryable=True, terminal=False)
        db.commit()
        assert db.execute(select(KnowledgeChunkEmbeddingModel)).scalars().all() == []
        assert db.get(KnowledgeEmbeddingGenerationModel, generation_id).status == "pending"

    monkeypatch.setattr("app.knowledge.embedding_executor.LocalDeterministicEmbeddingProvider.dimensions", 1)
    with pytest.raises(JobExecutionError, match="embedding_dimension_mismatch"):
        executor.execute(claimed, CancellationContext())
    with Session() as db:
        assert db.execute(select(KnowledgeChunkEmbeddingModel)).scalars().all() == []
        assert db.get(KnowledgeDocumentVersionModel, version_id).embedding_model is None


def test_embedding_requires_approved_source_and_rejects_generic_submission(embedding_session) -> None:
    Session = embedding_session
    owner_id, version_id = _seed_ready_version(Session, approved=False)
    with Session() as db:
        owner = db.get(UserModel, owner_id)
        with pytest.raises(HTTPException) as approval:
            submit_document_embedding(db, user_context(owner), version_id, "phase18d-approval-key")
        assert approval.value.status_code == 409
        with pytest.raises(HTTPException) as generic:
            submit_job(
                db,
                user_context(owner),
                JobSubmissionRequest(
                    job_type="document.embed",
                    input_schema_version="document.embed.v1",
                    input_json={"document_version_id": version_id, "embedding_profile_id": "kembprof_local_hash_384_v1"},
                ),
                "phase18d-generic-key",
            )
        assert generic.value.status_code == 403


def test_embedding_config_rejects_external_or_dimension_mismatched_provider() -> None:
    with pytest.raises(ValueError, match="local deterministic"):
        Settings(knowledge_embedding_provider="remote_provider")
    with pytest.raises(ValueError, match="local deterministic"):
        Settings(knowledge_embedding_dimensions=768)


def _seed_ready_version(Session, *, approved: bool = True) -> tuple[str, str]:
    with Session() as db:
        owner = create_user(db, "phase18d-owner@example.test")
        source = create_knowledge_source(
            db,
            user_context(owner),
            visibility="private",
            title="Phase 18D private source",
            source_type="upload",
        )
        source.trust_state = "approved_for_rag" if approved else "needs_review"
        source.status = "ingested"
        document = KnowledgeDocumentModel(
            id="kdoc_phase18d",
            knowledge_source_id=source.id,
            current_version_id="kver_phase18d",
            filename="risk.md",
            media_type="text/markdown",
            status="ready",
        )
        version = KnowledgeDocumentVersionModel(
            id="kver_phase18d",
            document_id=document.id,
            version_number=1,
            storage_key="knowledge/private/test/original",
            checksum="a" * 64,
            size_bytes=100,
            status="ready",
        )
        chunks = [
            KnowledgeChunkModel(
                id="kchunk_phase18d_1",
                document_version_id=version.id,
                chunk_index=0,
                heading_path=["Oracle"],
                content="Oracle controls should use independent price feeds.",
                content_checksum="b" * 64,
                token_count=7,
            ),
            KnowledgeChunkModel(
                id="kchunk_phase18d_2",
                document_version_id=version.id,
                chunk_index=1,
                heading_path=["Liquidity"],
                content="Liquidity stress can increase liquidation risk.",
                content_checksum="c" * 64,
                token_count=6,
            ),
        ]
        db.add_all([document, version, *chunks])
        db.commit()
        return owner.id, version.id


def _worker(db, owner):
    worker = WorkerModel(
        id="worker_phase18d",
        name="phase18d-embedding-worker",
        status="active",
        protocol_version="v1",
        capabilities_json={},
        allowed_job_types=["document.embed"],
        max_concurrency=1,
    )
    credential = WorkerCredentialModel(
        id="workercred_phase18d",
        worker_id=worker.id,
        token_prefix="wrk_phase18d_test_prefix",
        token_hash="phase18d-test-token-hash",
        allowed_job_types=["document.embed"],
        status="active",
        created_by_user_id=owner.id,
    )
    db.add_all([worker, credential])
    return worker, credential


def _claimed_job(job: JobModel):
    from app.jobs.schemas import WorkerClaimedJob

    now = datetime.now(UTC)
    return WorkerClaimedJob(
        id=job.id,
        job_type=job.job_type,
        input_schema_version=job.input_schema_version,
        input_json=job.input_json,
        lease_generation=1,
        lease_token="lease_" + "x" * 30,
        lease_expires_at=now + timedelta(minutes=5),
        execution_deadline_at=now + timedelta(minutes=5),
        deadline_at=None,
    )
