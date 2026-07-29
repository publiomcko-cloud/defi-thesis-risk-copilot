from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user, user_context
from app.core.config import Settings, get_settings
from app.core.logging import SafeJsonFormatter
from app.core.observability import correlation_context, operational_readiness, redact_value
from app.db.base import Base
from app.jobs.control_service import submit_job
from app.jobs.schemas import JobSubmissionRequest
from app.jobs.worker_runner import WorkerClient
from app.main import app


@pytest.fixture()
def phase19_session(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("JOBS_ENABLED", "true")
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


def test_api_normalizes_and_returns_safe_correlation_headers() -> None:
    supplied = "web_1234567890abcdef"
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Correlation-ID": supplied})
        malformed = client.get("/health", headers={"X-Correlation-ID": "short"})

    assert response.status_code == 200
    assert response.headers["x-correlation-id"] == supplied
    assert response.headers["x-request-id"] == supplied
    assert malformed.headers["x-correlation-id"] != "short"
    assert malformed.headers["x-correlation-id"].startswith("req_")
    assert "secret" not in response.text.lower()


def test_safe_formatter_redacts_nested_sensitive_values() -> None:
    record = __import__("logging").LogRecord(
        "defi_copilot.test", 20, __file__, 1, "Bearer top-secret-token", (), None
    )
    record.event = "phase19.test"
    record.correlation_id = "web_1234567890abcdef"
    record.observability = {
        "authorization": "Bearer top-secret-token",
        "nested": {"storage_key": "private/key", "safe": "ok"},
    }

    payload = json.loads(SafeJsonFormatter().format(record))
    rendered = json.dumps(payload)
    assert "top-secret-token" not in rendered
    assert "private/key" not in rendered
    assert payload["fields"]["nested"]["safe"] == "ok"
    assert redact_value("token=super-secret") == "[REDACTED]"


def test_job_submission_persists_server_owned_correlation_id(phase19_session) -> None:
    with phase19_session() as db:
        actor = user_context(create_user(db, "phase19-owner@example.test"))
        with correlation_context("web_1234567890abcdef"):
            job, replayed = submit_job(
                db,
                actor,
                JobSubmissionRequest(
                    job_type="analysis.generate",
                    input_schema_version="analysis.generate.v1",
                    input_json={"analysis_request": {"strategy_description": "Test strategy"}},
                ),
                "phase19-correlation-key",
            )

        assert replayed is False
        assert job.input_json["_server_context"]["correlation_id"] == "web_1234567890abcdef"
        assert "correlation_id" not in job.input_json["request"]


def test_worker_client_forwards_only_generated_correlation_header(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return b"{}"

    def fake_urlopen(request, timeout: int):
        captured.update({key.lower(): value for key, value in request.header_items()})
        assert timeout == 20
        return Response()

    monkeypatch.setattr("app.jobs.worker_runner.urlopen", fake_urlopen)
    client = WorkerClient("http://worker-control-plane.test", "wrk_phase19_credential")
    client.correlation_id = "web_1234567890abcdef"
    client.request("POST", "/internal/workers/v1/claim", {"protocol_version": "v1"})

    assert captured["x-correlation-id"] == "web_1234567890abcdef"
    assert captured["x-request-id"] == "web_1234567890abcdef"
    assert captured["authorization"] == "Bearer wrk_phase19_credential"


def test_operational_readiness_is_metadata_only_and_configuration_is_bounded(phase19_session) -> None:
    with phase19_session() as db:
        result = operational_readiness(db)

    assert result["telemetry_export"] == "not_implemented"
    assert result["shared_rate_limiting"] == "disabled"
    assert result["knowledge_pgvector_primary_enabled"] is False
    assert result["vast_dry_run"] is True
    assert result["vast_real_rentals_enabled"] is False
    assert "credential" not in json.dumps(result).lower()
    with pytest.raises(ValidationError, match="OBSERVABILITY_SAMPLING_RATE"):
        Settings(observability_sampling_rate=1.1)
