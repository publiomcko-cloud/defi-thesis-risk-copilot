from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user, user_context
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.jobs.schemas import WorkerClaimedJob, WorkerCredentialCreateRequest, WorkerRegistrationRequest
from app.jobs.vast_executor import VastJobExecutor
from app.jobs.worker_protocol import recover_durable_jobs
from app.jobs.worker_service import issue_worker_credential, register_worker
from app.main import app
from app.models.job import JobModel, ProviderCostReservationModel
from app.models.vast_session import VastSessionModel


def test_vast_job_reconciles_lost_completion_without_second_session(phase17e_client) -> None:
    client, Session, admin_token, worker_token = phase17e_client
    created = _queue_vast_job(client, admin_token, "phase17e-lost-response")
    replay = _queue_vast_job(client, admin_token, "phase17e-lost-response")
    assert replay["id"] == created["id"]

    first_lease = _claim_and_start(client, worker_token)
    executor = VastJobExecutor(session_factory=Session)
    first_result = executor.execute(WorkerClaimedJob.model_validate(first_lease))
    assert first_result.result_json["provider_status"] == "ready"

    lease_payload = _lease_payload(first_lease)
    released = client.post(
        f"/internal/workers/v1/jobs/{first_lease['id']}/release",
        json=lease_payload,
        headers=_worker_auth(worker_token),
    )
    assert released.status_code == 200
    assert released.json()["status"] == "retry_wait"
    with Session() as db:
        job = db.get(JobModel, created["id"])
        assert job is not None
        job.available_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()

    retry_lease = _claim_and_start(client, worker_token)
    retry_result = executor.execute(WorkerClaimedJob.model_validate(retry_lease))
    assert retry_result.result_json["vast_session_id"] == first_result.result_json["vast_session_id"]
    completed = client.post(
        f"/internal/workers/v1/jobs/{retry_lease['id']}/complete",
        json={
            **_lease_payload(retry_lease),
            "result": retry_result.model_dump(mode="json"),
        },
        headers=_worker_auth(worker_token),
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    with Session() as db:
        sessions = db.execute(
            select(VastSessionModel).where(VastSessionModel.source_job_id == created["id"])
        ).scalars().all()
        assert len(sessions) == 1
        assert sessions[0].metadata_json["dry_run"] is True
        assert db.get(JobModel, created["id"]).actual_cost_microusd == 125_000


def test_vast_cancellation_invokes_idempotent_cleanup(phase17e_client) -> None:
    client, Session, admin_token, worker_token = phase17e_client
    created = _queue_vast_job(client, admin_token, "phase17e-cancel-cleanup")
    lease = _claim_and_start(client, worker_token)
    executor = VastJobExecutor(session_factory=Session)
    executor.execute(WorkerClaimedJob.model_validate(lease))

    cancel = client.post(f"/api/jobs/{created['id']}/cancel", headers=_auth(admin_token))
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancel_requested"
    released = client.post(
        f"/internal/workers/v1/jobs/{lease['id']}/release",
        json=_lease_payload(lease),
        headers=_worker_auth(worker_token),
    )
    assert released.status_code == 200
    assert released.json()["status"] == "cancelled"
    with Session() as db:
        session = db.execute(
            select(VastSessionModel).where(VastSessionModel.source_job_id == created["id"])
        ).scalars().one()
        assert session.status == "destroyed"
        job = db.get(JobModel, created["id"])
        reservation = db.query(ProviderCostReservationModel).filter_by(job_id=created["id"]).one()
        assert job.reserved_cost_microusd == 0
        assert job.actual_cost_microusd == 125_000
        assert reservation.status == "completed"
        assert reservation.actual_cost_microusd == 125_000


def test_provider_job_is_admin_only_server_profiled_and_budgeted(phase17e_client, monkeypatch) -> None:
    client, _, admin_token, _ = phase17e_client
    common = client.post(
        "/api/admin/vast/jobs/start",
        json={"allow_remote_gpu": False, "warm_instance": False},
        headers={**_auth("phase17e-common-token"), "Idempotency-Key": "phase17e-common"},
    )
    assert common.status_code == 403
    arbitrary_profile = client.post(
        "/api/admin/vast/jobs/start",
        json={"allow_remote_gpu": False, "warm_instance": False, "model": "untrusted"},
        headers={**_auth(admin_token), "Idempotency-Key": "phase17e-arbitrary"},
    )
    assert arbitrary_profile.status_code == 422
    generic = client.post(
        "/api/jobs",
        json={"job_type": "vast.session.start", "input_schema_version": "vast.session.start.v1", "input_json": {}},
        headers={**_auth(admin_token), "Idempotency-Key": "phase17e-generic"},
    )
    assert generic.status_code == 403

    monkeypatch.setenv("JOB_DAILY_COST_BUDGET_MICROUSD", "1")
    get_settings.cache_clear()
    budgeted = client.post(
        "/api/admin/vast/jobs/start",
        json={"allow_remote_gpu": False, "warm_instance": False},
        headers={**_auth(admin_token), "Idempotency-Key": "phase17e-budget"},
    )
    assert budgeted.status_code == 429


def test_admin_operations_exposes_aggregate_safe_job_state(phase17e_client) -> None:
    client, _, admin_token, _ = phase17e_client
    _queue_vast_job(client, admin_token, "phase17e-operations")
    response = client.get("/api/admin/jobs/operations", headers=_auth(admin_token))
    assert response.status_code == 200
    assert response.json() == {
        "queued_jobs": 1,
        "leased_or_running_jobs": 0,
        "dead_letter_jobs": 0,
        "active_workers": 1,
        "stale_workers": 0,
        "provider_cleanup_failures": 0,
    }


def test_recovery_dry_run_never_invokes_provider_cleanup(phase17e_client, monkeypatch) -> None:
    client, Session, admin_token, _ = phase17e_client
    created = _queue_vast_job(client, admin_token, "phase17e-recovery-dry-run")
    calls: list[bool] = []

    def unexpected_cleanup(*_args, **_kwargs) -> None:
        calls.append(bool(_kwargs.get("perform_external_cleanup")))

    monkeypatch.setattr("app.jobs.worker_protocol._cleanup_provider_for_terminal_job", unexpected_cleanup)
    with Session() as db:
        job = db.get(JobModel, created["id"])
        assert job is not None
        job.status = "cancel_requested"
        job.leased_by_worker_id = None
        db.commit()
        counts = recover_durable_jobs(db, dry_run=True)
        assert counts["provider_cleanup_candidates"] == 0
    with Session() as db:
        assert db.get(JobModel, created["id"]).status == "cancel_requested"
    assert calls == [False]


@pytest.fixture
def phase17e_client(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "legacy_local")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("WORKER_API_ENABLED", "true")
    monkeypatch.setenv("VAST_JOB_ENABLED", "true")
    monkeypatch.setenv("VAST_ENABLED", "true")
    monkeypatch.setenv("VAST_DRY_RUN", "true")
    monkeypatch.setenv("VAST_MODEL", "phase17e-server-model")
    monkeypatch.setenv("VAST_IMAGE", "phase17e-server-image")
    monkeypatch.setenv("VAST_MAX_HOURLY_COST_USD", "0.50")
    monkeypatch.setenv("VAST_MAX_SESSION_MINUTES", "30")
    monkeypatch.setenv("JOB_DAILY_COST_BUDGET_MICROUSD", "1000000")
    monkeypatch.setenv("AUTH_SECRET_KEY", "phase17e-auth")
    monkeypatch.setenv("WORKER_TOKEN_PEPPER", "phase17e-worker")
    get_settings.cache_clear()
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    with Session() as db:
        admin = create_user(db, "phase17e-admin@example.test", role="admin", token="phase17e-admin-token")
        create_user(db, "phase17e-common@example.test", token="phase17e-common-token")
        worker = register_worker(
            db,
            user_context(admin),
            WorkerRegistrationRequest(
                name="phase17e-worker",
                protocol_version="v1",
                allowed_job_types=["vast.session.start"],
            ),
        )
        issued = issue_worker_credential(db, user_context(admin), worker.id, WorkerCredentialCreateRequest())
        db.commit()

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), Session, "phase17e-admin-token", issued.token
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def _queue_vast_job(client: TestClient, admin_token: str, key: str) -> dict:
    response = client.post(
        "/api/admin/vast/jobs/start",
        json={"allow_remote_gpu": False, "warm_instance": False},
        headers={**_auth(admin_token), "Idempotency-Key": key},
    )
    assert response.status_code == 202
    assert response.json()["job"]["result_resource_type"] == "vast_session"
    return response.json()["job"]


def _claim_and_start(client: TestClient, worker_token: str) -> dict:
    claim = client.post(
        "/internal/workers/v1/claim",
        json={"protocol_version": "v1"},
        headers=_worker_auth(worker_token),
    )
    assert claim.status_code == 200
    lease = claim.json()["job"]
    assert lease is not None
    started = client.post(
        f"/internal/workers/v1/jobs/{lease['id']}/start",
        json=_lease_payload(lease),
        headers=_worker_auth(worker_token),
    )
    assert started.status_code == 200
    return lease


def _lease_payload(lease: dict) -> dict:
    return {"lease_generation": lease["lease_generation"], "lease_token": lease["lease_token"]}


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _worker_auth(token: str) -> dict[str, str]:
    return _auth(token)
