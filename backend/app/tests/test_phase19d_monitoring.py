from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.models.job import JobModel
from app.models.knowledge import KnowledgeRetrievalEventModel
from app.models.worker import WorkerModel
from app.operations.monitoring import operations_monitoring_snapshot
from app.main import app
from scripts import run_synthetic_checks as synthetic_script
from scripts import run_synthetic_checks as synthetic_script
from scripts.run_synthetic_checks import _validated_origin, run_synthetic_checks


@pytest.fixture()
def monitoring_session(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "legacy_local")
    monkeypatch.setenv("AUTH_SECRET_KEY", "phase19d-auth-secret")
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("OPERATIONS_MONITORING_ENABLED", "true")
    monkeypatch.setenv("OPERATIONS_ALERT_EVALUATION_ENABLED", "true")
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


@pytest.fixture()
def monitoring_client(monitoring_session):
    def override_get_db():
        db = monitoring_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_monitoring_snapshot_is_aggregate_only_and_deduplicates_alerts(monitoring_session) -> None:
    now = datetime(2026, 7, 28, 15, 0, tzinfo=UTC)
    with monitoring_session() as db:
        admin = create_user(db, "monitor-admin@example.test", role="admin", token="monitor-admin-token")
        db.add_all(
            [
                _job(admin.id, "job_monitor_queued", "queued", now - timedelta(seconds=1_200)),
                _job(admin.id, "job_monitor_dead", "dead_letter", now - timedelta(seconds=60)),
                WorkerModel(
                    id="wrk_monitor_overdue",
                    name="monitor-overdue",
                    status="active",
                    protocol_version="v1",
                    max_concurrency=1,
                    last_seen_at=now - timedelta(seconds=500),
                    created_at=now - timedelta(seconds=600),
                    updated_at=now - timedelta(seconds=500),
                ),
                KnowledgeRetrievalEventModel(
                    id="kretr_monitor_empty",
                    request_id="req_monitor_empty",
                    user_id=admin.id,
                    query_hash="a" * 64,
                    filters_json={},
                    retrieved_chunk_ids=[],
                    scores_json=[],
                    latency_ms=6_000,
                    retriever_version="phase19d-test",
                    created_at=now - timedelta(seconds=30),
                ),
            ]
        )
        db.commit()
        snapshot = operations_monitoring_snapshot(db, now=now)

    assert snapshot.monitoring_mode == "local_aggregate"
    assert snapshot.alert_delivery == "not_implemented"
    assert snapshot.queue_depth == 1
    assert snapshot.oldest_queue_age_seconds == 1_200
    assert snapshot.dead_letter_jobs == 1
    assert snapshot.overdue_active_workers == 1
    assert snapshot.retrieval_events == 1
    assert snapshot.retrieval_empty_rate_percent == 100
    assert snapshot.retrieval_max_latency_ms == 6_000
    assert {alert.key for alert in snapshot.alerts} >= {
        "queue_age", "dead_letters", "stale_workers", "retrieval_empty_rate", "retrieval_latency"
    }
    assert len({alert.key for alert in snapshot.alerts}) == len(snapshot.alerts)
    assert "job_monitor" not in snapshot.model_dump_json()
    assert "monitor-admin" not in snapshot.model_dump_json()


def test_monitoring_endpoint_requires_admin_and_does_not_expose_records(
    monitoring_client,
    monitoring_session,
) -> None:
    with monitoring_session() as db:
        create_user(db, "monitor-route-admin@example.test", role="admin", token="monitor-route-admin-token")
        create_user(db, "monitor-route-user@example.test", token="monitor-route-user-token")

    denied = monitoring_client.get(
        "/api/admin/operations/monitoring", headers={"Authorization": "Bearer monitor-route-user-token"}
    )
    allowed = monitoring_client.get(
        "/api/admin/operations/monitoring", headers={"Authorization": "Bearer monitor-route-admin-token"}
    )

    assert denied.status_code == 403
    assert allowed.status_code == 200
    payload = allowed.json()
    assert payload["alert_delivery"] == "not_implemented"
    assert "monitor-route-admin" not in str(payload)
    assert "request_id" not in str(payload)


def test_monitoring_endpoint_requires_explicit_enablement(
    monkeypatch: pytest.MonkeyPatch,
    monitoring_client,
    monitoring_session,
) -> None:
    with monitoring_session() as db:
        create_user(db, "monitor-disabled-admin@example.test", role="admin", token="monitor-disabled-admin-token")

    monkeypatch.setenv("OPERATIONS_MONITORING_ENABLED", "false")
    monkeypatch.setenv("OPERATIONS_ALERT_EVALUATION_ENABLED", "false")
    get_settings.cache_clear()
    try:
        response = monitoring_client.get(
            "/api/admin/operations/monitoring",
            headers={"Authorization": "Bearer monitor-disabled-admin-token"},
        )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "Operations monitoring is disabled"


def test_monitoring_configuration_and_synthetic_url_rules() -> None:
    with pytest.raises(ValidationError, match="OPERATIONS_ALERT_EVALUATION_ENABLED"):
        Settings(operations_alert_evaluation_enabled=True)
    with pytest.raises(ValidationError, match="OPERATIONS_SYNTHETIC_CHECKS_ENABLED"):
        Settings(operations_synthetic_checks_enabled=True)
    with pytest.raises(ValueError, match="origin-only"):
        _validated_origin("https://synthetic.example.test/path")
    assert _validated_origin("https://synthetic.example.test/") == "https://synthetic.example.test"
    with pytest.raises(ValueError, match="SYNTHETIC_CHECK_BEARER_TOKEN"):
        run_synthetic_checks(
            "https://synthetic.example.test",
            timeout_seconds=3,
            authenticated=True,
        )


def test_synthetic_runner_uses_fixed_paths_and_never_returns_response_bodies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested: list[str] = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, size: int) -> bytes:
            assert size == 1
            return b"secret response body"

    class Opener:
        @contextmanager
        def open(self, request, timeout: float):
            requested.append(request.full_url)
            assert timeout == 3
            yield Response()

    monkeypatch.setattr("scripts.run_synthetic_checks.build_opener", lambda *_handlers: Opener())
    results = run_synthetic_checks("https://synthetic.example.test", timeout_seconds=3)

    assert [result.name for result in results] == ["health", "readiness", "demo_status"]
    assert requested == [
        "https://synthetic.example.test/health",
        "https://synthetic.example.test/ready",
        "https://synthetic.example.test/api/demo/status",
    ]
    assert "secret response body" not in str(results)


def test_synthetic_command_is_disabled_without_explicit_configuration(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sys.argv", ["run_synthetic_checks.py", "--base-url", "https://synthetic.example.test"])
    monkeypatch.setattr(synthetic_script, "get_settings", lambda: Settings())

    assert synthetic_script.main() == 2
    assert "disabled" in capsys.readouterr().out


def test_synthetic_command_rejects_an_unapproved_origin(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sys.argv", ["run_synthetic_checks.py", "--base-url", "https://unapproved.example.test"])
    monkeypatch.setattr(
        synthetic_script,
        "get_settings",
        lambda: Settings(
            operations_monitoring_enabled=True,
            operations_synthetic_checks_enabled=True,
            operations_synthetic_allowed_origins="https://approved.example.test",
        ),
    )

    assert synthetic_script.main() == 2
    assert "OPERATIONS_SYNTHETIC_ALLOWED_ORIGINS" in capsys.readouterr().out


def _job(owner_user_id: str, job_id: str, status: str, created_at: datetime) -> JobModel:
    return JobModel(
        id=job_id,
        job_type="analysis.generate",
        status=status,
        priority_class="standard",
        owner_user_id=owner_user_id,
        created_by_user_id=owner_user_id,
        visibility="private",
        input_schema_version="analysis.generate.v1",
        input_json={},
        request_fingerprint=f"fingerprint-{job_id}",
        attempt_count=0,
        max_attempts=3,
        available_at=created_at,
        progress_percent=0,
        idempotency_subject_type="user",
        idempotency_subject_id=owner_user_id,
        idempotency_key=f"key-{job_id}",
        estimated_cost_microusd=0,
        reserved_cost_microusd=0,
        actual_cost_microusd=0,
        created_at=created_at,
        updated_at=created_at,
    )
