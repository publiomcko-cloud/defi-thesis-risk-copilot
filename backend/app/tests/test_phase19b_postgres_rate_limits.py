from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from app.auth.schemas import UserContext
from app.db.session import create_database_engine
from app.rate_limits.service import ACTION_AUTHENTICATED_COMPUTE, enforce_rate_limit

pytestmark = pytest.mark.postgres_integration


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        rate_limiting_enabled=True,
        rate_limiting_mode="enforce",
        rate_limit_key_pepper="postgres-rate-limit-pepper",
        rate_limit_trusted_proxy_cidrs="",
        rate_limit_retention_seconds=3600,
        rate_limit_public_compute_burst_limit=1,
        rate_limit_public_compute_burst_window_seconds=60,
        rate_limit_public_compute_sustained_limit=10,
        rate_limit_public_compute_sustained_window_seconds=3600,
        rate_limit_authenticated_compute_burst_limit=1,
        rate_limit_authenticated_compute_burst_window_seconds=60,
        rate_limit_authenticated_compute_sustained_limit=10,
        rate_limit_authenticated_compute_sustained_window_seconds=3600,
        rate_limit_job_submit_burst_limit=1,
        rate_limit_job_submit_burst_window_seconds=60,
        rate_limit_job_submit_sustained_limit=10,
        rate_limit_job_submit_sustained_window_seconds=3600,
    )


def _request(client_host: str = "198.51.100.9") -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/analyze",
            "headers": [],
            "client": (client_host, 4000),
            "scheme": "https",
        }
    )


def test_postgres_shared_limiter_allows_only_one_concurrent_burst_request() -> None:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("PostgreSQL shared limiter test requires RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL shared limiter test requires a PostgreSQL DATABASE_URL")
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    barrier = Barrier(4)
    suffix = uuid4().hex
    actor = UserContext(
        id=f"phase19_rate_limit_user_{suffix}",
        email=f"rate-limit-{suffix}@example.test",
        role="common",
    )
    client_host = f"2001:db8:{suffix[:4]}:{suffix[4:8]}::{suffix[8:12]}"
    settings = _settings()
    now = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)

    def attempt() -> int:
        with Session() as db:
            barrier.wait()
            try:
                enforce_rate_limit(
                    db,
                    _request(client_host),
                    actor,
                    action=ACTION_AUTHENTICATED_COMPUTE,
                    settings=settings,
                    now=now,
                )
                return 200
            except HTTPException as exc:
                return exc.status_code

    with ThreadPoolExecutor(max_workers=4) as executor:
        statuses = list(executor.map(lambda _: attempt(), range(4)))

    assert statuses.count(200) == 1
    assert statuses.count(429) == 3
