from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user, user_context
from app.core.config import get_settings
from app.db.base import Base
from app.jobs.cancellation import CancellationContext
from app.jobs.control_service import submit_job
from app.jobs.schemas import JobSubmissionRequest, WorkerClaimedJob, WorkerLeaseRequest
from app.jobs.worker_protocol import WorkerIdentity, claim_next_job, complete_job, start_job
from app.knowledge.access import create_knowledge_source
from app.knowledge.ingestion import extract_normalize_and_chunk
from app.knowledge.ingestion_executor import (
    DocumentIngestJobExecutor,
    cleanup_document_ingest_outputs,
    finalize_document_ingestion,
)
from app.knowledge.ingestion_service import submit_document_ingestion
from app.models.knowledge import KnowledgeChunkModel, KnowledgeDocumentModel, KnowledgeDocumentVersionModel
from app.models.job import JobModel
from app.models.user import UserModel
from app.models.worker import WorkerCredentialModel, WorkerModel
from app.storage.base import ObjectMetadata
from app.storage.keys import build_version_object_key
from app.storage.memory import InMemoryPrivateObjectStorage


@pytest.fixture()
def ingestion_session(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("WORKER_API_ENABLED", "true")
    monkeypatch.setenv("KNOWLEDGE_STORAGE_ENABLED", "true")
    monkeypatch.setenv("DOCUMENT_INGEST_ENABLED", "true")
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    storage = InMemoryPrivateObjectStorage()
    try:
        yield Session, storage
    finally:
        get_settings.cache_clear()


def test_document_ingest_is_server_owned_idempotent_and_activates_only_on_completion(
    ingestion_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Session, storage = ingestion_session
    owner_id, _, document_id, version_id = _seed_uploaded_version(Session, storage)
    monkeypatch.setattr("app.knowledge.ingestion_executor.create_private_object_storage", lambda: storage)
    with Session() as db:
        owner = db.get(UserModel, owner_id)
        job, replayed = submit_document_ingestion(db, user_context(owner), version_id, "phase18c-ingest-key")
        assert replayed is False
        assert job.result_resource_id == version_id
        assert db.get(KnowledgeDocumentVersionModel, version_id).status == "ingestion_pending"
        replay, replayed = submit_document_ingestion(db, user_context(owner), version_id, "phase18c-ingest-key")
        assert replayed is True
        assert replay.id == job.id
        with pytest.raises(HTTPException) as duplicate:
            submit_document_ingestion(db, user_context(owner), version_id, "phase18c-other-key")
        assert duplicate.value.status_code == 409
        claimed = _claimed_job(job)

    # Supabase object-info may omit Content-Length; the bounded downloaded payload
    # and immutable version record still provide authoritative integrity checks.
    monkeypatch.setattr(
        storage,
        "head",
        lambda *, key: ObjectMetadata(key=key, size_bytes=0, content_type="text/markdown"),
    )
    result = DocumentIngestJobExecutor(session_factory=Session).execute(claimed)
    with Session() as db:
        job = db.get(JobModel, claimed.id)
        assert job is not None
        assert db.get(KnowledgeDocumentVersionModel, version_id).status == "ingesting"
        assert len(db.execute(select(KnowledgeChunkModel)).scalars().all()) == result.result_json["chunk_count"]
        finalize_document_ingestion(db, job, result.result_json)
        db.commit()
        final_version = db.get(KnowledgeDocumentVersionModel, version_id)
        final_document = db.get(KnowledgeDocumentModel, document_id)
        assert final_version is not None and final_version.status == "ready"
        assert final_document is not None and final_document.current_version_id == version_id


def test_document_ingest_runs_through_the_phase17_worker_protocol(
    ingestion_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Session, storage = ingestion_session
    owner_id, _, _, version_id = _seed_uploaded_version(Session, storage)
    monkeypatch.setattr("app.knowledge.ingestion_executor.create_private_object_storage", lambda: storage)
    with Session() as db:
        owner = db.get(UserModel, owner_id)
        job, _ = submit_document_ingestion(db, user_context(owner), version_id, "phase18c-worker-key")
        worker = WorkerModel(
            id="worker_phase18c",
            name="phase18c-ingestion-worker",
            status="active",
            protocol_version="v1",
            capabilities_json={},
            allowed_job_types=["document.ingest"],
            max_concurrency=1,
        )
        credential = WorkerCredentialModel(
            id="workercred_phase18c",
            worker_id=worker.id,
            token_prefix="wrk_phase18c_test_prefix",
            token_hash="phase18c-test-token-hash",
            allowed_job_types=["document.ingest"],
            status="active",
            created_by_user_id=owner.id,
        )
        db.add_all([worker, credential])
        db.commit()
        identity = WorkerIdentity(credential=credential, worker=worker)
        claim = claim_next_job(db, identity)
        assert claim.job is not None and claim.job.id == job.id
        lease = WorkerLeaseRequest(
            lease_generation=claim.job.lease_generation,
            lease_token=claim.job.lease_token,
        )
        assert start_job(db, identity, job.id, lease).status == "running"

    result = DocumentIngestJobExecutor(session_factory=Session).execute(claim.job)
    with Session() as db:
        worker = db.get(WorkerModel, "worker_phase18c")
        credential = db.get(WorkerCredentialModel, "workercred_phase18c")
        assert worker is not None and credential is not None
        finished = complete_job(
            db,
            WorkerIdentity(credential=credential, worker=worker),
            job.id,
            lease,
            result,
        )
        assert finished.status == "completed"
        assert db.get(KnowledgeDocumentVersionModel, version_id).status == "ready"


def test_retry_and_cancellation_cleanup_never_activate_partial_chunks(
    ingestion_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Session, storage = ingestion_session
    owner_id, _, document_id, version_id = _seed_uploaded_version(Session, storage)
    monkeypatch.setattr("app.knowledge.ingestion_executor.create_private_object_storage", lambda: storage)
    with Session() as db:
        owner = db.get(UserModel, owner_id)
        job, _ = submit_document_ingestion(db, user_context(owner), version_id, "phase18c-retry-key")
        claimed = _claimed_job(job)
    executor = DocumentIngestJobExecutor(session_factory=Session)
    first = executor.execute(claimed)
    with Session() as db:
        cleanup_document_ingest_outputs(db, version_id, retryable=True, terminal=False)
        db.commit()
        assert db.execute(select(KnowledgeChunkModel)).scalars().all() == []
        assert db.get(KnowledgeDocumentVersionModel, version_id).status == "ingestion_pending"
    second = executor.execute(claimed)
    assert first.result_json["chunk_count"] == second.result_json["chunk_count"]
    with Session() as db:
        cleanup_document_ingest_outputs(db, version_id, retryable=False, terminal=False)
        db.commit()
        assert db.execute(select(KnowledgeChunkModel)).scalars().all() == []
        assert db.get(KnowledgeDocumentVersionModel, version_id).status == "uploaded"
        assert db.get(KnowledgeDocumentModel, document_id).current_version_id is None


def test_document_ingest_requires_approved_source_and_generic_submission_stays_blocked(
    ingestion_session,
) -> None:
    Session, storage = ingestion_session
    owner_id, _, _, version_id = _seed_uploaded_version(Session, storage, approved=False)
    with Session() as db:
        owner = db.get(UserModel, owner_id)
        with pytest.raises(HTTPException) as approval:
            submit_document_ingestion(db, user_context(owner), version_id, "phase18c-approval-key")
        assert approval.value.status_code == 409
        with pytest.raises(HTTPException) as generic:
            submit_job(
                db,
                user_context(owner),
                JobSubmissionRequest(
                    job_type="document.ingest",
                    input_schema_version="document.ingest.v1",
                    input_json={"document_version_id": version_id},
                ),
                "phase18c-generic-key",
            )
        assert generic.value.status_code == 403


def test_html_parser_removes_scripts_and_rejects_empty_text() -> None:
    chunks = extract_normalize_and_chunk(
        content=b"<h1>Aave</h1><script>secret = 'no'</script><p>Oracle controls</p>",
        media_type="text/html",
        cancellation=CancellationContext(),
    )
    assert "secret" not in " ".join(chunk.content for chunk in chunks)
    assert "Oracle controls" in " ".join(chunk.content for chunk in chunks)
    with pytest.raises(Exception):
        extract_normalize_and_chunk(
            content=b"<script>only script</script>",
            media_type="text/html",
            cancellation=CancellationContext(),
        )


def _seed_uploaded_version(Session, storage, *, approved: bool = True):
    with Session() as db:
        owner = create_user(db, "phase18c-owner@example.test")
        source = create_knowledge_source(
            db,
            user_context(owner),
            visibility="private",
            title="Phase 18C private source",
            source_type="upload",
        )
        source.trust_state = "approved_for_rag" if approved else "needs_review"
        document = KnowledgeDocumentModel(
            id="kdoc_phase18c",
            knowledge_source_id=source.id,
            filename="risk.md",
            media_type="text/markdown",
            status="uploaded",
        )
        content = b"# Oracle controls\n\nUse multiple oracle checks before liquidations.\n\n## Risks\n\nLiquidity can disappear during volatility.\n"
        version = KnowledgeDocumentVersionModel(
            id="kver_phase18c",
            document_id=document.id,
            version_number=1,
            storage_key="pending",
            checksum=sha256(content).hexdigest(),
            size_bytes=len(content),
            status="uploaded",
        )
        version.storage_key = build_version_object_key(source, document, version)
        db.add_all([document, version])
        storage.put_create_only(key=version.storage_key, content=content, content_type=document.media_type, expected_checksum=version.checksum)
        db.commit()
        return owner.id, source.id, document.id, version.id


def _claimed_job(job) -> WorkerClaimedJob:
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
