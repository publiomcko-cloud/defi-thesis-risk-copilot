"""Bounded, non-production Phase 19H capacity and dependency exercises."""

from __future__ import annotations

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from io import BytesIO
from math import ceil
from threading import Barrier
from time import perf_counter
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import Headers

from app.auth.schemas import UserContext
from app.auth.service import create_user, ensure_bootstrap_admin, user_context
from app.core.config import get_settings
from app.db.session import create_database_engine, get_db
from app.jobs.control_service import submit_job
from app.jobs.schemas import (
    JobSubmissionRequest,
    WorkerCredentialCreateRequest,
    WorkerHeartbeatRequest,
    WorkerLeaseRequest,
    WorkerRegistrationRequest,
)
from app.jobs.worker_protocol import (
    authenticate_worker,
    claim_next_job,
    heartbeat_job,
    recover_durable_jobs,
    start_job,
)
from app.jobs.worker_service import issue_worker_credential, register_worker
from app.knowledge.schemas import KnowledgeSourceCreateRequest
from app.knowledge.service import create_document_upload, create_source
from app.models.access_audit_event import AccessAuditEventModel
from app.models.job import JobAttemptModel, JobCapacityReservationModel, JobEventModel, JobModel
from app.models.knowledge import KnowledgeDocumentModel, KnowledgeDocumentVersionModel, KnowledgeSourceModel
from app.models.usage_quota import UsageQuotaModel
from app.models.user import UserModel
from app.models.worker import WorkerCredentialModel, WorkerModel
from app.operations.exercise_metrics import record_exercise_metrics
from app.storage.base import StorageError
from app.storage.memory import InMemoryPrivateObjectStorage


pytestmark = pytest.mark.postgres_integration


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 19 isolated operations require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("Phase 19 isolated operations require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _configure_exercise(monkeypatch: pytest.MonkeyPatch, **values: str) -> None:
    defaults = {
        "APP_ENV": "exercise",
        "AUTH_ENABLED": "true",
        "AUTH_PROVIDER": "legacy_local",
        "PUBLIC_DEMO_MODE": "false",
        "JOBS_ENABLED": "true",
        "WORKER_API_ENABLED": "true",
        "WORKER_TOKEN_PEPPER": "phase19-isolated-worker-pepper",
        "VAST_DRY_RUN": "true",
        "VAST_REAL_RENTALS_ENABLED": "false",
        "VAST_ENABLED": "false",
        "RATE_LIMITING_ENABLED": "false",
    }
    defaults.update(values)
    for key, value in defaults.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()


@contextmanager
def _app_database_override(Session: sessionmaker):
    from app.main import app

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield app
    finally:
        app.dependency_overrides.pop(get_db, None)


def _actor(user_id: str, email: str) -> UserContext:
    return UserContext(
        id=user_id,
        email=email,
        role="common",
        platform_role="user",
        plan="free",
        auth_enabled=True,
        email_verified=True,
    )


def _analysis_submission(label: str) -> JobSubmissionRequest:
    return JobSubmissionRequest(
        job_type="analysis.generate",
        input_schema_version="analysis.generate.v1",
        input_json={
            "analysis_request": {
                "strategy_description": f"Phase 19 isolated exercise {label}.",
                "protocols": ["aave"],
                "manual_inputs": {},
                "analysis_depth": "standard",
            }
        },
    )


async def _http_scenario(
    client: httpx.AsyncClient,
    *,
    path: str,
    headers: dict[str, str] | None,
    request_count: int,
    concurrency: int,
) -> dict[str, float | int]:
    semaphore = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()
    active = 0
    peak_active = 0
    latencies: list[float] = []
    statuses: list[int] = []
    started = perf_counter()

    async def request_once() -> None:
        nonlocal active, peak_active
        async with semaphore:
            async with lock:
                active += 1
                peak_active = max(peak_active, active)
            request_started = perf_counter()
            try:
                response = await client.get(path, headers=headers)
                statuses.append(response.status_code)
            finally:
                latencies.append((perf_counter() - request_started) * 1_000)
                async with lock:
                    active -= 1

    await asyncio.gather(*(request_once() for _ in range(request_count)))
    duration = perf_counter() - started
    ordered = sorted(latencies)
    success_count = sum(status == 200 for status in statuses)
    return {
        "request_count": request_count,
        "configured_concurrency": concurrency,
        "observed_concurrency": peak_active,
        "success_count": success_count,
        "error_count": request_count - success_count,
        "success_rate_pct": round(success_count / request_count * 100, 2),
        "throughput_rps": round(request_count / max(duration, 0.001), 2),
        "p50_latency_ms": round(_percentile(ordered, 50), 2),
        "p95_latency_ms": round(_percentile(ordered, 95), 2),
    }


def _percentile(values: list[float], percentile: int) -> float:
    return values[max(0, ceil(len(values) * percentile / 100) - 1)]


def test_isolated_http_load_harness(
    postgres_sessions: sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise actual public and authenticated API routes through ASGI HTTP."""
    _configure_exercise(monkeypatch)
    suffix = uuid4().hex[:12]
    email = f"phase19-load-{suffix}@example.test"
    token = f"phase19-load-token-{suffix}"
    try:
        with postgres_sessions() as db:
            user = create_user(db, email, token=token)
            user_id = user.id

        async def run() -> tuple[dict[str, float | int], dict[str, float | int]]:
            with _app_database_override(postgres_sessions) as app:
                transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
                async with httpx.AsyncClient(transport=transport, base_url="http://phase19.exercise") as client:
                    public = await _http_scenario(
                        client, path="/health", headers=None, request_count=24, concurrency=6
                    )
                    authenticated = await _http_scenario(
                        client,
                        path="/api/auth/me",
                        headers={"Authorization": f"Bearer {token}"},
                        request_count=24,
                        concurrency=6,
                    )
                    return public, authenticated

        public, authenticated = asyncio.run(run())
        for result in (public, authenticated):
            assert result["request_count"] == 24
            assert result["configured_concurrency"] == 6
            assert result["success_rate_pct"] == 100
            assert result["error_count"] == 0
            assert result["p95_latency_ms"] <= 2_000
            assert result["throughput_rps"] >= 1
        record_exercise_metrics(
            {
                "public_requests": public["request_count"],
                "authenticated_requests": authenticated["request_count"],
                "configured_concurrency": 6,
                "public_success_rate_pct": public["success_rate_pct"],
                "authenticated_success_rate_pct": authenticated["success_rate_pct"],
                "public_p50_latency_ms": public["p50_latency_ms"],
                "public_p95_latency_ms": public["p95_latency_ms"],
                "authenticated_p50_latency_ms": authenticated["p50_latency_ms"],
                "authenticated_p95_latency_ms": authenticated["p95_latency_ms"],
                "public_throughput_rps": public["throughput_rps"],
                "authenticated_throughput_rps": authenticated["throughput_rps"],
                "p95_threshold_ms": 2_000,
                "minimum_throughput_rps": 1,
                "thresholds_passed": True,
            }
        )
    finally:
        with postgres_sessions() as db:
            db.execute(delete(AccessAuditEventModel).where(AccessAuditEventModel.actor_user_id == locals().get("user_id", "")))
            db.execute(delete(UserModel).where(UserModel.id == locals().get("user_id", "")))
            db.commit()
        get_settings.cache_clear()


def test_bootstrap_admin_initialization_is_concurrency_safe(
    postgres_sessions: sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_exercise(monkeypatch, ADMIN_EMAIL=f"phase19-bootstrap-{uuid4().hex[:12]}@example.test")
    email = get_settings().admin_email
    barrier = Barrier(6)
    try:
        def initialize() -> str:
            with postgres_sessions() as db:
                barrier.wait()
                admin = ensure_bootstrap_admin(db)
                assert admin is not None
                return admin.id

        with ThreadPoolExecutor(max_workers=6) as executor:
            ids = list(executor.map(lambda _: initialize(), range(6)))
        assert len(set(ids)) == 1
        with postgres_sessions() as db:
            admin = db.scalar(select(UserModel).where(UserModel.email == email))
            assert admin is not None and admin.id == ids[0]
    finally:
        with postgres_sessions() as db:
            db.execute(delete(UserModel).where(UserModel.email == email))
            db.commit()
        get_settings.cache_clear()


def test_concurrent_queue_admission_and_recovery(
    postgres_sessions: sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_exercise(
        monkeypatch,
        JOB_GLOBAL_PENDING_LIMIT="20",
        JOB_PROVIDER_PENDING_LIMIT="20",
        JOB_USER_PENDING_LIMIT="2",
    )
    suffix = uuid4().hex[:12]
    email = f"phase19-queue-{suffix}@example.test"
    user_id = ""
    try:
        with postgres_sessions() as db:
            user = create_user(db, email, token=f"phase19-queue-{suffix}")
            user_id = user.id
        actor = _actor(user_id, email)
        barrier = Barrier(6)

        def submit(index: int) -> tuple[str, int]:
            with postgres_sessions() as db:
                barrier.wait()
                try:
                    job, _ = submit_job(db, actor, _analysis_submission(f"queue-{index}"), f"phase19-queue-{suffix}-{index}")
                    return job.id, 202
                except HTTPException as exc:
                    return "", exc.status_code

        started = perf_counter()
        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(submit, range(6)))
        admission_duration = perf_counter() - started
        accepted_ids = [job_id for job_id, status in results if status == 202]
        rejected = sum(status == 429 for _, status in results)
        assert len(accepted_ids) == 2
        assert rejected == 4

        with postgres_sessions() as db:
            queued = db.execute(select(JobModel).where(JobModel.id.in_(accepted_ids))).scalars().all()
            assert len(queued) == 2
            for job in queued:
                job.queue_expires_at = datetime.now(UTC) - timedelta(seconds=1)
            db.commit()
            recovery_started = perf_counter()
            recovered = recover_durable_jobs(db)
            recovery_seconds = perf_counter() - recovery_started
            remaining_pending = db.execute(
                select(JobModel).where(JobModel.id.in_(accepted_ids)).where(JobModel.status.in_({"queued", "retry_wait"}))
            ).scalars().all()
            user_capacity = db.execute(
                select(JobCapacityReservationModel)
                .where(JobCapacityReservationModel.scope_type == "user")
                .where(JobCapacityReservationModel.scope_id == user_id)
            ).scalars().one()
            assert recovered["expired_jobs"] == 2
            assert remaining_pending == []
            assert user_capacity.pending_count == 0
        assert admission_duration <= 10
        assert recovery_seconds <= 5
        record_exercise_metrics(
            {
                "concurrent_submissions": 6,
                "queue_depth_peak": len(accepted_ids),
                "admission_accepted": len(accepted_ids),
                "admission_rejected": rejected,
                "recovered_expired_jobs": recovered["expired_jobs"],
                "remaining_pending": 0,
                "admission_duration_ms": round(admission_duration * 1_000, 2),
                "recovery_duration_ms": round(recovery_seconds * 1_000, 2),
                "admission_threshold_ms": 10_000,
                "recovery_threshold_ms": 5_000,
                "thresholds_passed": True,
            }
        )
    finally:
        _cleanup_job_exercise(postgres_sessions, user_id)
        get_settings.cache_clear()


def test_worker_loss_lease_recovery_blocks_duplicate_execution(
    postgres_sessions: sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_exercise(monkeypatch, JOB_LEASE_SECONDS="1", JOB_HEARTBEAT_SECONDS="1")
    suffix = uuid4().hex[:12]
    owner_id = ""
    admin_id = ""
    job_id = ""
    worker_ids: list[str] = []
    try:
        with postgres_sessions() as db:
            owner = create_user(db, f"phase19-worker-owner-{suffix}@example.test", token=f"owner-{suffix}")
            admin = create_user(db, f"phase19-worker-admin-{suffix}@example.test", role="admin", token=f"admin-{suffix}")
            owner_id = owner.id
            admin_id = admin.id
            job, _ = submit_job(db, user_context(owner), _analysis_submission("worker-loss"), f"phase19-worker-job-{suffix}")
            job_id = job.id
            first_worker = register_worker(
                db,
                user_context(admin),
                WorkerRegistrationRequest(name=f"phase19-worker-one-{suffix}", protocol_version="v1", allowed_job_types=["analysis.generate"]),
            )
            second_worker = register_worker(
                db,
                user_context(admin),
                WorkerRegistrationRequest(name=f"phase19-worker-two-{suffix}", protocol_version="v1", allowed_job_types=["analysis.generate"]),
            )
            worker_ids.extend([first_worker.id, second_worker.id])
            first_token = issue_worker_credential(db, user_context(admin), first_worker.id, WorkerCredentialCreateRequest()).token
            second_token = issue_worker_credential(db, user_context(admin), second_worker.id, WorkerCredentialCreateRequest()).token
            db.commit()

        with postgres_sessions() as db:
            first_identity = authenticate_worker(db, first_token, "v1")
            first_claim = claim_next_job(db, first_identity).job
            assert first_claim is not None and first_claim.id == job_id
            first_lease = WorkerLeaseRequest(lease_generation=first_claim.lease_generation, lease_token=first_claim.lease_token)
            assert start_job(db, first_identity, job_id, first_lease).status == "running"
            lease_expiry = first_claim.lease_expires_at

        with postgres_sessions() as db:
            recovery_started = perf_counter()
            recovered = recover_durable_jobs(db, now=lease_expiry + timedelta(seconds=1))
            recovery_seconds = perf_counter() - recovery_started
            record = db.get(JobModel, job_id)
            assert record is not None and record.status == "retry_wait"
            # The isolated scheduler advances availability after simulated expiry.
            record.available_at = datetime.now(UTC) - timedelta(seconds=1)
            db.commit()

        with postgres_sessions() as db:
            first_identity = authenticate_worker(db, first_token, "v1")
            with pytest.raises(HTTPException) as stale:
                heartbeat_job(
                    db,
                    first_identity,
                    job_id,
                    WorkerHeartbeatRequest(lease_generation=first_lease.lease_generation, lease_token=first_lease.lease_token),
                )
            assert stale.value.status_code == 409
            second_identity = authenticate_worker(db, second_token, "v1")
            second_claim = claim_next_job(db, second_identity).job
            assert second_claim is not None and second_claim.id == job_id
            assert second_claim.lease_generation == first_claim.lease_generation + 1
        assert recovered["expired_jobs"] == 1
        assert recovery_seconds <= 5
        record_exercise_metrics(
            {
                "leased_jobs": 1,
                "stopped_workers": 1,
                "recovered_expired_jobs": recovered["expired_jobs"],
                "stale_execution_rejections": 1,
                "replacement_claims": 1,
                "recovery_duration_ms": round(recovery_seconds * 1_000, 2),
                "recovery_threshold_ms": 5_000,
                "duplicate_execution_blocked": True,
                "thresholds_passed": True,
            }
        )
    finally:
        _cleanup_job_exercise(postgres_sessions, owner_id, worker_ids)
        _cleanup_job_exercise(postgres_sessions, admin_id)
        get_settings.cache_clear()


def test_database_and_storage_fault_injection_recovers_without_partial_data(
    postgres_sessions: sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_exercise(monkeypatch, KNOWLEDGE_STORAGE_ENABLED="true")
    suffix = uuid4().hex[:12]
    user_id = ""
    storage = InMemoryPrivateObjectStorage()
    try:
        with postgres_sessions() as db:
            user = create_user(db, f"phase19-storage-{suffix}@example.test", token=f"storage-{suffix}")
            user_id = user.id
            source = create_source(
                db,
                user_context(user),
                KnowledgeSourceCreateRequest(visibility="private", title="Isolated storage exercise", source_type="upload"),
            )

        with _app_database_override(postgres_sessions) as app:
            def unavailable_database():
                raise OperationalError("select 1", {}, RuntimeError("isolated database outage"))
                yield  # pragma: no cover - keeps this function a dependency generator

            app.dependency_overrides[get_db] = unavailable_database
            database_started = perf_counter()
            with TestClient(app, raise_server_exceptions=False) as client:
                outage = client.get("/ready")
            database_failure_ms = (perf_counter() - database_started) * 1_000
            assert outage.status_code >= 500
            app.dependency_overrides.pop(get_db, None)
            database_recovery_started = perf_counter()
            with TestClient(app, raise_server_exceptions=False) as client:
                ready = client.get("/ready")
            database_recovery_ms = (perf_counter() - database_recovery_started) * 1_000
            assert ready.status_code == 200

        class UnavailableStorage:
            def put_create_only(self, **_kwargs):
                raise StorageError("isolated storage outage")

        monkeypatch.setattr("app.knowledge.service._configured_storage", lambda: UnavailableStorage())
        with postgres_sessions() as db:
            owner = db.get(UserModel, user_id)
            assert owner is not None
            upload = UploadFile(filename="exercise.md", file=BytesIO(b"# Isolated\n"), headers=Headers({"content-type": "text/markdown"}))
            storage_started = perf_counter()
            with pytest.raises(HTTPException) as failed_upload:
                asyncio.run(create_document_upload(db, user_context(owner), source.id, upload, None))
            storage_failure_ms = (perf_counter() - storage_started) * 1_000
            assert failed_upload.value.status_code == 503
            assert db.execute(select(KnowledgeDocumentModel).where(KnowledgeDocumentModel.knowledge_source_id == source.id)).scalars().all() == []

        monkeypatch.setattr("app.knowledge.service._configured_storage", lambda: storage)
        with postgres_sessions() as db:
            owner = db.get(UserModel, user_id)
            assert owner is not None
            upload = UploadFile(filename="exercise.md", file=BytesIO(b"# Isolated\n"), headers=Headers({"content-type": "text/markdown"}))
            storage_recovery_started = perf_counter()
            result = asyncio.run(create_document_upload(db, user_context(owner), source.id, upload, None))
            storage_recovery_ms = (perf_counter() - storage_recovery_started) * 1_000
            version = db.get(KnowledgeDocumentVersionModel, result.versions[0].id)
            assert version is not None
            assert storage.head(key=version.storage_key).checksum == version.checksum
        assert database_recovery_ms <= 5_000
        assert storage_recovery_ms <= 5_000
        record_exercise_metrics(
            {
                "database_failure_status": outage.status_code,
                "database_recovery_status": ready.status_code,
                "database_failure_duration_ms": round(database_failure_ms, 2),
                "database_recovery_duration_ms": round(database_recovery_ms, 2),
                "storage_failure_status": failed_upload.value.status_code,
                "storage_recovery_duration_ms": round(storage_recovery_ms, 2),
                "partial_documents_after_failure": 0,
                "verified_recovered_objects": 1,
                "recovery_threshold_ms": 5_000,
                "fail_closed": True,
                "data_integrity_verified": True,
                "thresholds_passed": True,
            }
        )
    finally:
        _cleanup_knowledge_exercise(postgres_sessions, user_id)
        get_settings.cache_clear()


def _cleanup_job_exercise(Session: sessionmaker, user_id: str, worker_ids: list[str] | None = None) -> None:
    if not user_id:
        return
    with Session() as db:
        job_ids = select(JobModel.id).where(JobModel.owner_user_id == user_id)
        db.execute(delete(JobEventModel).where(JobEventModel.job_id.in_(job_ids)))
        db.execute(delete(JobAttemptModel).where(JobAttemptModel.job_id.in_(job_ids)))
        db.execute(delete(JobModel).where(JobModel.owner_user_id == user_id))
        if worker_ids:
            db.execute(delete(WorkerCredentialModel).where(WorkerCredentialModel.worker_id.in_(worker_ids)))
            db.execute(delete(WorkerModel).where(WorkerModel.id.in_(worker_ids)))
        db.execute(delete(JobCapacityReservationModel).where(JobCapacityReservationModel.scope_type == "user").where(JobCapacityReservationModel.scope_id == user_id))
        db.execute(delete(UsageQuotaModel).where(UsageQuotaModel.subject_id == user_id))
        db.execute(delete(AccessAuditEventModel).where(AccessAuditEventModel.actor_user_id == user_id))
        db.execute(delete(UserModel).where(UserModel.id == user_id))
        db.commit()


def _cleanup_knowledge_exercise(Session: sessionmaker, user_id: str) -> None:
    if not user_id:
        return
    with Session() as db:
        source_ids = select(KnowledgeSourceModel.id).where(KnowledgeSourceModel.owner_user_id == user_id)
        document_ids = select(KnowledgeDocumentModel.id).where(KnowledgeDocumentModel.knowledge_source_id.in_(source_ids))
        db.execute(delete(KnowledgeDocumentVersionModel).where(KnowledgeDocumentVersionModel.document_id.in_(document_ids)))
        db.execute(delete(KnowledgeDocumentModel).where(KnowledgeDocumentModel.knowledge_source_id.in_(source_ids)))
        db.execute(delete(KnowledgeSourceModel).where(KnowledgeSourceModel.owner_user_id == user_id))
        db.execute(delete(AccessAuditEventModel).where(AccessAuditEventModel.actor_user_id == user_id))
        db.execute(delete(UserModel).where(UserModel.id == user_id))
        db.commit()
