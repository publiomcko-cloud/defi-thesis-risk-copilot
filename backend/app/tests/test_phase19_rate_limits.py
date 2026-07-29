from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from app.auth.schemas import UserContext
from app.auth.service import create_user, user_context
from app.core.config import Settings, get_settings
from app.core.public_demo import reset_public_rate_limits
from app.db.base import Base
from app.db.session import get_db
from app.jobs.schemas import JobSubmissionRequest
from app.models.organization import OrganizationMembershipModel, OrganizationModel
from app.models.rate_limit import RateLimitBucketModel
from app.models.usage_quota import UsageQuotaModel
from app.main import app
from app.rate_limits.service import (
    ACTION_AUTHENTICATED_COMPUTE,
    ACTION_JOB_SUBMISSION,
    ACTION_PUBLIC_COMPUTE,
    _scopes_for_request,
    enforce_job_submission_rate_limit,
    enforce_rate_limit,
)


def _settings(**overrides):
    values = {
        "rate_limiting_enabled": True,
        "rate_limiting_mode": "enforce",
        "rate_limit_key_pepper": "test-rate-limit-pepper",
        "rate_limit_trusted_proxy_cidrs": "",
        "rate_limit_retention_seconds": 3600,
        "rate_limit_public_compute_burst_limit": 1,
        "rate_limit_public_compute_burst_window_seconds": 60,
        "rate_limit_public_compute_sustained_limit": 10,
        "rate_limit_public_compute_sustained_window_seconds": 3600,
        "rate_limit_authenticated_compute_burst_limit": 2,
        "rate_limit_authenticated_compute_burst_window_seconds": 60,
        "rate_limit_authenticated_compute_sustained_limit": 10,
        "rate_limit_authenticated_compute_sustained_window_seconds": 3600,
        "rate_limit_job_submit_burst_limit": 1,
        "rate_limit_job_submit_burst_window_seconds": 60,
        "rate_limit_job_submit_sustained_limit": 10,
        "rate_limit_job_submit_sustained_window_seconds": 3600,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _request(client_host: str = "198.51.100.8", headers: dict[str, str] | None = None) -> Request:
    raw_headers = [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()]
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/options/analyze",
            "headers": raw_headers,
            "client": (client_host, 4000),
            "scheme": "https",
        }
    )


@pytest.fixture()
def rate_limit_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return Session


@pytest.fixture()
def shared_public_client(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    monkeypatch.setenv("RATE_LIMITING_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMITING_MODE", "enforce")
    monkeypatch.setenv("RATE_LIMIT_KEY_PEPPER", "test-rate-limit-pepper")
    monkeypatch.setenv("RATE_LIMIT_PUBLIC_COMPUTE_BURST_LIMIT", "1")
    monkeypatch.setenv("RATE_LIMIT_PUBLIC_COMPUTE_SUSTAINED_LIMIT", "10")
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

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


@pytest.fixture()
def job_submission_client(monkeypatch):
    """Exercise the public API path, including its shared limiter dependency."""

    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "legacy_local")
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMITING_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMITING_MODE", "enforce")
    monkeypatch.setenv("RATE_LIMIT_KEY_PEPPER", "test-rate-limit-pepper")
    monkeypatch.setenv("RATE_LIMIT_JOB_SUBMIT_BURST_LIMIT", "1")
    monkeypatch.setenv("RATE_LIMIT_JOB_SUBMIT_SUSTAINED_LIMIT", "10")
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

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


@pytest.fixture()
def legacy_public_client(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    monkeypatch.setenv("RATE_LIMITING_ENABLED", "false")
    monkeypatch.setenv("PUBLIC_COMPUTE_RATE_LIMIT_PER_MINUTE", "1")
    get_settings.cache_clear()
    reset_public_rate_limits()
    try:
        yield TestClient(app)
    finally:
        reset_public_rate_limits()
        get_settings.cache_clear()


def test_shared_public_compute_limit_returns_retry_metadata_and_hides_raw_scope(shared_public_client) -> None:
    client, Session = shared_public_client
    payload = {
        "option_type": "call",
        "underlying_asset": "ETH",
        "underlying_price": 3000,
        "strike_price": 3200,
        "premium": 150,
    }

    first = client.post("/api/options/analyze", json=payload)
    second = client.post("/api/options/analyze", json=payload)

    assert first.status_code == 200
    assert first.headers["x-ratelimit-mode"] == "enforce"
    assert first.headers["x-ratelimit-policy"] == ACTION_PUBLIC_COMPUTE
    assert second.status_code == 429
    assert second.headers["retry-after"]
    assert second.headers["x-ratelimit-reset"]
    with Session() as db:
        buckets = db.execute(select(RateLimitBucketModel)).scalars().all()
    assert buckets
    rendered = " ".join(bucket.scope_key_hash for bucket in buckets)
    assert "anon_" not in rendered
    assert "testclient" not in rendered


def test_untrusted_runtime_forwarded_addresses_cannot_bypass_shared_limiter(shared_public_client) -> None:
    client, _Session = shared_public_client
    payload = {
        "option_type": "call",
        "underlying_asset": "ETH",
        "underlying_price": 3000,
        "strike_price": 3200,
        "premium": 150,
    }

    first = client.post("/api/options/analyze", json=payload, headers={"X-Forwarded-For": "198.51.100.1"})
    spoofed_retry = client.post(
        "/api/options/analyze",
        json=payload,
        headers={"X-Forwarded-For": "203.0.113.250"},
    )

    assert first.status_code == 200
    assert spoofed_retry.status_code == 429


def test_untrusted_runtime_forwarded_addresses_cannot_bypass_legacy_limiter(legacy_public_client) -> None:
    payload = {
        "option_type": "put",
        "underlying_asset": "ETH",
        "underlying_price": 3000,
        "strike_price": 2800,
        "premium": 120,
    }

    first = legacy_public_client.post(
        "/api/options/analyze", json=payload, headers={"X-Forwarded-For": "198.51.100.1"}
    )
    spoofed_retry = legacy_public_client.post(
        "/api/options/analyze",
        json=payload,
        headers={"X-Forwarded-For": "203.0.113.250"},
    )

    assert first.status_code == 200
    assert spoofed_retry.status_code == 429


def test_job_submission_endpoint_enforces_shared_limiter_with_fastapi_request(job_submission_client) -> None:
    client, Session = job_submission_client
    with Session() as db:
        create_user(db, "rate-limited-job-owner@example.test", token="rate-limited-job-token")

    payload = {
        "job_type": "analysis.generate",
        "input_schema_version": "analysis.generate.v1",
        "input_json": {
            "analysis_request": {
                "strategy_description": "Evaluate a bounded lending strategy.",
                "protocols": ["aave"],
                "manual_inputs": {},
                "analysis_depth": "standard",
            }
        },
    }
    headers = {"Authorization": "Bearer rate-limited-job-token", "Idempotency-Key": "rate-limit-job-one"}
    first = client.post("/api/jobs", json=payload, headers=headers)
    blocked = client.post(
        "/api/jobs",
        json=payload,
        headers={**headers, "Idempotency-Key": "rate-limit-job-two"},
    )

    assert first.status_code == 202
    assert blocked.status_code == 429
    assert blocked.headers["x-ratelimit-policy"] == ACTION_JOB_SUBMISSION


def test_shadow_mode_observes_threshold_without_blocking(rate_limit_session) -> None:
    actor = UserContext(id="user_shadow", email="shadow@example.test", role="common")
    request = _request()
    settings = _settings(rate_limiting_mode="shadow", rate_limit_authenticated_compute_burst_limit=1)
    now = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)
    with rate_limit_session() as db:
        first = enforce_rate_limit(db, request, actor, action=ACTION_AUTHENTICATED_COMPUTE, settings=settings, now=now)
        second = enforce_rate_limit(db, request, actor, action=ACTION_AUTHENTICATED_COMPUTE, settings=settings, now=now)

    assert first.would_block is False
    assert second.would_block is True


def test_enforced_rate_limit_is_distinct_from_product_quota_and_uses_fixed_database_window(rate_limit_session) -> None:
    actor = UserContext(id="user_quota", email="quota@example.test", role="common")
    request = _request()
    settings = _settings(rate_limit_authenticated_compute_burst_limit=1)
    first_time = datetime(2026, 7, 28, 12, 0, 5, tzinfo=UTC)
    with rate_limit_session() as db:
        first = enforce_rate_limit(
            db, request, actor, action=ACTION_AUTHENTICATED_COMPUTE, settings=settings, now=first_time
        )
        with pytest.raises(HTTPException) as blocked:
            enforce_rate_limit(
                db,
                request,
                actor,
                action=ACTION_AUTHENTICATED_COMPUTE,
                settings=settings,
                now=datetime(2026, 7, 28, 12, 0, 55, tzinfo=UTC),
            )
        assert db.execute(select(UsageQuotaModel)).scalars().all() == []

    assert first.remaining == 0
    assert blocked.value.status_code == 429
    assert blocked.value.headers["Retry-After"] == "5"


def test_forwarded_address_is_used_only_for_configured_proxy() -> None:
    actor = UserContext(id="user_proxy", email="proxy@example.test", role="common")
    request = _request("10.10.0.4", {"X-Forwarded-For": "203.0.113.12, 10.10.0.4"})

    trusted = _scopes_for_request(request, actor, None, _settings(rate_limit_trusted_proxy_cidrs="10.0.0.0/8"))
    untrusted = _scopes_for_request(request, actor, None, _settings())

    assert trusted[0].identifier == "203.0.113.12"
    assert untrusted[0].identifier == "10.10.0.4"


def test_limiter_backend_outage_fails_closed_only_in_enforce_mode(rate_limit_session, monkeypatch) -> None:
    actor = UserContext(id="user_outage", email="outage@example.test", role="common")
    request = _request()

    def unavailable(*_args, **_kwargs):
        raise OperationalError("update", {}, Exception("database unavailable"))

    monkeypatch.setattr("app.rate_limits.service._increment_bucket", unavailable)
    with rate_limit_session() as db:
        with pytest.raises(HTTPException) as enforced:
            enforce_rate_limit(db, request, actor, action=ACTION_AUTHENTICATED_COMPUTE, settings=_settings())
        shadow = enforce_rate_limit(
            db,
            request,
            actor,
            action=ACTION_AUTHENTICATED_COMPUTE,
            settings=_settings(rate_limiting_mode="shadow"),
        )

    assert enforced.value.status_code == 503
    assert enforced.value.headers["Retry-After"] == "5"
    assert shadow.limited is False


def test_job_admission_adds_only_a_verified_organization_scope(rate_limit_session, monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMITING_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMITING_MODE", "enforce")
    monkeypatch.setenv("RATE_LIMIT_KEY_PEPPER", "test-rate-limit-pepper")
    get_settings.cache_clear()
    try:
        with rate_limit_session() as db:
            user = create_user(db, "rate-limit-owner@example.test")
            actor = user_context(user)
            organization = OrganizationModel(
                id="org_rate_limit",
                name="Rate limit organization",
                slug="rate-limit-organization",
                status="active",
                created_by_user_id=user.id,
            )
            db.add(organization)
            db.add(
                OrganizationMembershipModel(
                    id="mbr_rate_limit",
                    organization_id=organization.id,
                    user_id=user.id,
                    role="member",
                    status="active",
                )
            )
            db.commit()
            valid = enforce_job_submission_rate_limit(
                db,
                _request(),
                actor,
                organization.id,
            )
            with pytest.raises(HTTPException) as denied:
                enforce_job_submission_rate_limit(db, _request(), actor, "org_not_a_member")
            scopes = db.execute(select(RateLimitBucketModel.scope_type)).scalars().all()
    finally:
        get_settings.cache_clear()

    assert valid is not None
    assert denied.value.status_code == 404
    assert sorted(set(scopes)) == ["ip", "organization", "user"]


def test_production_shared_limiter_requires_secret_pepper() -> None:
    with pytest.raises(ValueError, match="RATE_LIMIT_KEY_PEPPER"):
        Settings(app_env="production", rate_limiting_enabled=True, rate_limit_key_pepper="")
