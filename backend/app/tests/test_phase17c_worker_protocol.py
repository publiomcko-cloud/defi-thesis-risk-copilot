from __future__ import annotations

import os
import signal
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.schemas import UserContext
from app.auth.service import create_user, user_context
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.jobs import worker_runner
from app.jobs.schemas import WorkerClaimedJob, WorkerCredentialCreateRequest, WorkerRegistrationRequest
from app.jobs.worker_service import issue_worker_credential, register_worker
from app.main import app
from app.models.job import JobModel
from app.models.user import UserModel
from app.reports.templates import REQUIRED_REPORT_SECTIONS


@pytest.fixture
def worker_client(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "legacy_local")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("WORKER_API_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", "phase17c-auth")
    monkeypatch.setenv("WORKER_TOKEN_PEPPER", "phase17c-worker")
    monkeypatch.setenv("JOB_RETRY_BASE_SECONDS", "1")
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), Session
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_worker_protocol_leases_progresses_completes_and_rejects_stale_mutations(worker_client) -> None:
    client, Session = worker_client
    owner_token, worker_token = _seed_owner_and_worker(Session)
    job = _submit_job(client, owner_token, "worker-lifecycle-key")
    lease = _claim(client, worker_token)
    assert lease["id"] == job["id"]

    payload = _lease_payload(lease)
    assert client.post(f"/internal/workers/v1/jobs/{job['id']}/start", json=payload, headers=_worker_auth(worker_token)).json()["status"] == "running"
    progress = client.post(
        f"/internal/workers/v1/jobs/{job['id']}/progress",
        json={**payload, "progress_percent": 50, "progress_message": "Fake worker validated queue lifecycle."},
        headers=_worker_auth(worker_token),
    )
    assert progress.status_code == 200
    complete = client.post(
        f"/internal/workers/v1/jobs/{job['id']}/complete",
        json={
            **payload,
            "result": {
                "result_schema_version": "analysis.generate.v1",
                "result_json": _worker_result(lease),
            },
        },
        headers=_worker_auth(worker_token),
    )
    assert complete.status_code == 200
    assert complete.json()["status"] == "completed"
    stale = client.post(f"/internal/workers/v1/jobs/{job['id']}/complete", json={**payload, "result": {"result_schema_version": "analysis.generate.v1", "result_json": _worker_result(lease)}}, headers=_worker_auth(worker_token))
    assert stale.status_code == 409


def test_worker_protocol_scope_cancellation_and_lease_recovery(worker_client) -> None:
    client, Session = worker_client
    owner_token, worker_token = _seed_owner_and_worker(Session)
    wrong_scope_token = _seed_worker(Session, "vast-only-worker", ["vast.session.start"])
    queued = _submit_job(client, owner_token, "worker-scope-key")
    assert client.post("/internal/workers/v1/claim", json={"protocol_version": "v1"}, headers=_worker_auth(wrong_scope_token)).json()["job"] is None

    lease = _claim(client, worker_token)
    assert lease["id"] == queued["id"]
    payload = _lease_payload(lease)
    assert client.post(f"/internal/workers/v1/jobs/{queued['id']}/start", json=payload, headers=_worker_auth(worker_token)).status_code == 200
    assert client.post(f"/api/jobs/{queued['id']}/cancel", headers=_user_auth(owner_token)).json()["status"] == "cancel_requested"
    cancellation = client.get(f"/internal/workers/v1/jobs/{queued['id']}/cancellation", headers=_worker_auth(worker_token))
    assert cancellation.json()["cancellation_requested"] is True
    assert client.post(f"/internal/workers/v1/jobs/{queued['id']}/release", json=payload, headers=_worker_auth(worker_token)).json()["status"] == "cancelled"

    retry_job = _submit_job(client, owner_token, "worker-recovery-key")
    first_lease = _claim(client, worker_token)
    assert first_lease["id"] == retry_job["id"]
    with Session() as db:
        record = db.get(JobModel, retry_job["id"])
        assert record is not None
        record.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    # Claim recovers the expired lease and may reclaim it immediately when the short
    # test backoff has already elapsed.
    reclaimed = client.post("/internal/workers/v1/claim", json={"protocol_version": "v1"}, headers=_worker_auth(worker_token)).json()["job"]
    if reclaimed is None:
        with Session() as db:
            record = db.get(JobModel, retry_job["id"])
            assert record is not None
            record.available_at = datetime.now(UTC) - timedelta(seconds=1)
            db.commit()
        second_lease = _claim(client, worker_token)
    else:
        second_lease = reclaimed
    assert second_lease["id"] == retry_job["id"]
    assert second_lease["lease_generation"] == first_lease["lease_generation"] + 1
    stale_start = client.post(
        f"/internal/workers/v1/jobs/{retry_job['id']}/start",
        json=_lease_payload(first_lease),
        headers=_worker_auth(worker_token),
    )
    assert stale_start.status_code == 409


def test_worker_protocol_feature_gate_is_safe(worker_client, monkeypatch) -> None:
    client, Session = worker_client
    _, worker_token = _seed_owner_and_worker(Session)
    monkeypatch.setenv("WORKER_API_ENABLED", "false")
    get_settings.cache_clear()
    response = client.post("/internal/workers/v1/claim", json={"protocol_version": "v1"}, headers=_worker_auth(worker_token))
    assert response.status_code == 503


def test_local_worker_runner_uses_allowlisted_fake_executor_and_releases_on_sigterm(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    class FakeWorkerClient:
        def __init__(self, _base_url: str, _credential: str) -> None:
            pass

        def request(self, method: str, path: str, _payload: dict | None = None) -> dict:
            calls.append((method, path))
            if path.endswith("/claim"):
                return {
                    "job": {
                        "id": "job_runner",
                        "job_type": "analysis.generate",
                        "input_schema_version": "v1",
                        "input_json": {"request": {"strategy": "Fake only."}},
                        "lease_generation": 1,
                        "lease_token": "lease_abcdefghijklmnopqrstuvwxyz",
                        "lease_expires_at": (datetime.now(UTC) + timedelta(seconds=30)).isoformat(),
                        "deadline_at": None,
                    }
                }
            if path.endswith("/start"):
                os.kill(os.getpid(), signal.SIGTERM)
            return {"status": "ok"}

    monkeypatch.setenv("WORKER_CREDENTIAL", "wrk_abcdefghijklmnopqrstuvwxyz")
    monkeypatch.setattr(worker_runner, "WorkerClient", FakeWorkerClient)
    previous_handler = signal.getsignal(signal.SIGTERM)
    try:
        assert worker_runner.run_worker(once=True) == 0
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
    assert ("POST", "/internal/workers/v1/jobs/job_runner/release") in calls
    assert not any(path.endswith("/complete") for _, path in calls)


def _seed_owner_and_worker(Session) -> tuple[str, str]:
    with Session() as db:
        owner = create_user(db, "phase17c-owner@example.test", token="phase17c-owner-token")
        admin = create_user(db, "phase17c-admin@example.test", role="admin", token="phase17c-admin-token")
        worker = register_worker(
            db,
            user_context(admin),
            WorkerRegistrationRequest(name="phase17c-worker", protocol_version="v1", allowed_job_types=["analysis.generate"]),
        )
        issued = issue_worker_credential(db, user_context(admin), worker.id, WorkerCredentialCreateRequest())
        db.commit()
        return "phase17c-owner-token", issued.token


def _seed_worker(Session, name: str, scopes: list[str]) -> str:
    with Session() as db:
        admin = db.query(UserModel).filter_by(email="phase17c-admin@example.test").one()
        worker = register_worker(db, user_context(admin), WorkerRegistrationRequest(name=name, protocol_version="v1", allowed_job_types=scopes))
        issued = issue_worker_credential(db, user_context(admin), worker.id, WorkerCredentialCreateRequest())
        db.commit()
        return issued.token


def _submit_job(client: TestClient, token: str, key: str) -> dict:
    response = client.post(
        "/api/jobs",
        json={
            "job_type": "analysis.generate",
            "input_schema_version": "analysis.generate.v1",
            "input_json": {
                "analysis_request": {
                    "strategy_description": f"Queue protocol test {key}.",
                    "protocols": ["pendle"],
                    "manual_inputs": {},
                    "analysis_depth": "standard",
                }
            },
        },
        headers={**_user_auth(token), "Idempotency-Key": key},
    )
    assert response.status_code == 202
    return response.json()["job"]


def _claim(client: TestClient, worker_token: str) -> dict:
    response = client.post("/internal/workers/v1/claim", json={"protocol_version": "v1"}, headers=_worker_auth(worker_token))
    assert response.status_code == 200
    assert response.json()["job"] is not None
    return response.json()["job"]


def _lease_payload(lease: dict) -> dict:
    return {"lease_generation": lease["lease_generation"], "lease_token": lease["lease_token"]}


def _user_auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _worker_auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _worker_result(lease: dict) -> dict:
    request = lease["input_json"]["request"]["analysis_request"]
    return {
        "analysis_request": {
            "strategy_description": request["strategy_description"],
            "protocols": request["protocols"],
            "market_url": request.get("market_url"),
            "manual_inputs": request["manual_inputs"],
            "analysis_depth": request["analysis_depth"],
        },
        "report": {
            "report_id": lease["input_json"]["_server_context"]["report_id"],
            "status": "completed",
            "risk_rating": "Very Risky",
            "executive_summary": "Deterministic test report.",
            "strategy_description": request["strategy_description"],
            "protocols": request["protocols"],
            "assumptions": ["Deterministic scoring used."],
            "missing_data": [],
            "sections": [{"title": title, "content": "Test report."} for title in REQUIRED_REPORT_SECTIONS],
            "sources": [],
            "disclaimer": "This report is for research and educational purposes only. It is not financial advice.",
        },
    }
