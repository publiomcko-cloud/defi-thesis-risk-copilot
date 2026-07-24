from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user, user_context
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.jobs.schemas import WorkerCredentialCreateRequest, WorkerRegistrationRequest
from app.jobs.worker_service import issue_worker_credential, register_worker
from app.main import app
from app.models.analysis_request import AnalysisRequestModel
from app.models.artifact import ArtifactModel
from app.models.job import JobModel
from app.models.report import ReportModel
from app.reports.templates import REQUIRED_REPORT_SECTIONS


def test_authenticated_analysis_queues_once_and_persists_one_report(phase17d_client) -> None:
    client, Session = phase17d_client
    owner_token, worker_token = _seed_owner_and_worker(Session)
    payload = _analysis_payload()
    headers = {"Authorization": f"Bearer {owner_token}", "Idempotency-Key": "phase17d-analysis-key"}

    created = client.post("/api/analyze", json=payload, headers=headers)
    assert created.status_code == 200
    queued = created.json()
    assert queued["status"] == "queued"
    assert queued["job_id"].startswith("job_")
    assert queued["risk_rating"] is None

    replay = client.post("/api/analyze", json=payload, headers=headers)
    assert replay.status_code == 200
    assert replay.json()["job_id"] == queued["job_id"]
    assert replay.json()["report_id"] == queued["report_id"]

    lease = _claim(client, worker_token)
    lease_payload = {"lease_generation": lease["lease_generation"], "lease_token": lease["lease_token"]}
    assert client.post(f"/internal/workers/v1/jobs/{lease['id']}/start", json=lease_payload, headers=_worker_auth(worker_token)).status_code == 200
    complete = client.post(
        f"/internal/workers/v1/jobs/{lease['id']}/complete",
        json={
            **lease_payload,
            "result": {
                "result_schema_version": "analysis.generate.v1",
                "result_json": _worker_result(lease),
            },
        },
        headers=_worker_auth(worker_token),
    )
    assert complete.status_code == 200
    assert complete.json()["status"] == "completed"
    stale = client.post(
        f"/internal/workers/v1/jobs/{lease['id']}/complete",
        json={
            **lease_payload,
            "result": {"result_schema_version": "analysis.generate.v1", "result_json": _worker_result(lease)},
        },
        headers=_worker_auth(worker_token),
    )
    assert stale.status_code == 409

    with Session() as db:
        reports = db.execute(select(ReportModel).where(ReportModel.source_job_id == queued["job_id"])).scalars().all()
        requests = db.execute(
            select(AnalysisRequestModel).where(AnalysisRequestModel.source_job_id == queued["job_id"])
        ).scalars().all()
        job = db.get(JobModel, queued["job_id"])
        assert len(reports) == len(requests) == 1
        assert reports[0].id == queued["report_id"]
        assert job is not None and job.result_json == {
            "analysis_request_id": requests[0].id,
            "report_id": reports[0].id,
        }
        artifact = db.get(ArtifactModel, f"artifact_{queued['job_id']}")
        assert artifact is not None
        assert artifact.status == "available"
        assert artifact.storage_backend == "database"
        assert artifact.resource_type == "report"
        assert artifact.resource_id == reports[0].id


def test_cancellation_wins_without_persisting_a_report(phase17d_client) -> None:
    client, Session = phase17d_client
    owner_token, worker_token = _seed_owner_and_worker(Session)
    response = client.post(
        "/api/analyze",
        json=_analysis_payload(),
        headers={"Authorization": f"Bearer {owner_token}", "Idempotency-Key": "phase17d-cancel-key"},
    )
    queued = response.json()
    lease = _claim(client, worker_token)
    lease_payload = {"lease_generation": lease["lease_generation"], "lease_token": lease["lease_token"]}
    assert client.post(f"/internal/workers/v1/jobs/{lease['id']}/start", json=lease_payload, headers=_worker_auth(worker_token)).status_code == 200
    assert client.post(f"/api/jobs/{lease['id']}/cancel", headers={"Authorization": f"Bearer {owner_token}"}).json()["status"] == "cancel_requested"
    completion = client.post(
        f"/internal/workers/v1/jobs/{lease['id']}/complete",
        json={
            **lease_payload,
            "result": {"result_schema_version": "analysis.generate.v1", "result_json": _worker_result(lease)},
        },
        headers=_worker_auth(worker_token),
    )
    assert completion.status_code == 409
    assert client.post(f"/internal/workers/v1/jobs/{lease['id']}/release", json=lease_payload, headers=_worker_auth(worker_token)).json()["status"] == "cancelled"
    with Session() as db:
        assert db.get(ReportModel, queued["report_id"]) is None
        assert db.execute(select(AnalysisRequestModel)).scalars().all() == []


def test_disabling_async_flag_restores_authenticated_synchronous_analysis(phase17d_client, monkeypatch) -> None:
    client, Session = phase17d_client
    owner_token, _ = _seed_owner_and_worker(Session)
    monkeypatch.setenv("ASYNC_ANALYSIS_ENABLED", "false")
    get_settings.cache_clear()
    response = client.post(
        "/api/analyze",
        json=_analysis_payload(),
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["job_id"] is None
    with Session() as db:
        assert db.execute(select(JobModel)).scalars().all() == []


@pytest.fixture
def phase17d_client(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "legacy_local")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("WORKER_API_ENABLED", "true")
    monkeypatch.setenv("ASYNC_ANALYSIS_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", "phase17d-auth")
    monkeypatch.setenv("WORKER_TOKEN_PEPPER", "phase17d-worker")
    get_settings.cache_clear()
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
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


def _seed_owner_and_worker(Session) -> tuple[str, str]:
    with Session() as db:
        owner = create_user(db, "phase17d-owner@example.test", token="phase17d-owner-token")
        admin = create_user(db, "phase17d-admin@example.test", role="admin", token="phase17d-admin-token")
        worker = register_worker(
            db,
            user_context(admin),
            WorkerRegistrationRequest(name="phase17d-worker", protocol_version="v1", allowed_job_types=["analysis.generate"]),
        )
        issued = issue_worker_credential(db, user_context(admin), worker.id, WorkerCredentialCreateRequest())
        db.commit()
        return "phase17d-owner-token", issued.token


def _analysis_payload() -> dict:
    return {
        "strategy_description": "Analyze a hypothetical Pendle PT strategy using Morpho borrow with explicit risk limits.",
        "protocols": ["pendle", "morpho"],
        "manual_inputs": {"borrow_apy": 0.05, "implied_apy": 0.1},
        "analysis_depth": "standard",
    }


def _claim(client: TestClient, worker_token: str) -> dict:
    response = client.post("/internal/workers/v1/claim", json={"protocol_version": "v1"}, headers=_worker_auth(worker_token))
    assert response.status_code == 200
    return response.json()["job"]


def _worker_auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _worker_result(lease: dict) -> dict:
    request = lease["input_json"]["request"]["analysis_request"]
    report_id = lease["input_json"]["_server_context"]["report_id"]
    return {
        "analysis_request": {
            "strategy_description": request["strategy_description"],
            "protocols": sorted(request["protocols"]),
            "market_url": request.get("market_url"),
            "manual_inputs": request["manual_inputs"],
            "analysis_depth": request["analysis_depth"],
        },
        "report": {
            "report_id": report_id,
            "status": "completed",
            "risk_rating": "Very Risky",
            "executive_summary": "Deterministic risk score remains authoritative.",
            "strategy_description": request["strategy_description"],
            "protocols": sorted(request["protocols"]),
            "assumptions": ["Deterministic scoring used."],
            "missing_data": ["Liquidation buffer calculation"],
            "sections": [
                {"title": title, "content": "Deterministic report."}
                for title in REQUIRED_REPORT_SECTIONS
            ],
            "sources": [],
            "disclaimer": "This report is for research and educational purposes only. It is not financial advice.",
        },
    }
