from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import sessionmaker

from app.auth.schemas import UserContext
from app.auth.service import create_user
from app.core.config import get_settings
from app.db.session import create_database_engine
from app.models.access_audit_event import AccessAuditEventModel
from app.models.product_analytics import (
    PrivacyPreferenceDecisionModel,
    PrivacyPreferenceModel,
    ProductAnalyticsEventModel,
)
from app.models.user import UserModel
from app.product_analytics.service import emit_product_event_safely, set_privacy_preference


pytestmark = pytest.mark.postgres_integration


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("PostgreSQL analytics tests require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL analytics tests require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_postgres_preference_idempotency_serializes_first_opt_in(
    postgres_sessions: sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_analytics(monkeypatch)
    user_id = _create_test_user(postgres_sessions, "preference-race")
    actor = _actor(user_id)
    barrier = Barrier(2)

    def grant() -> tuple[str, bool]:
        with postgres_sessions() as db:
            barrier.wait()
            result = set_privacy_preference(
                db,
                actor,
                enabled=True,
                idempotency_key="postgres-concurrent-grant",
            )
            return result.decision, result.duplicate

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: grant(), range(2)))
        assert sorted(results) == [("grant", False), ("grant", True)]
        with postgres_sessions() as db:
            assert db.scalar(
                select(func.count()).select_from(PrivacyPreferenceDecisionModel).where(
                    PrivacyPreferenceDecisionModel.user_id == user_id
                )
            ) == 1
            preference = db.execute(
                select(PrivacyPreferenceModel).where(PrivacyPreferenceModel.user_id == user_id)
            ).scalars().one()
            assert preference.enabled is True
            assert preference.latest_decision_id is not None
    finally:
        _cleanup_user_data(postgres_sessions, user_id)
        get_settings.cache_clear()


def test_postgres_event_deduplication_is_concurrency_safe(
    postgres_sessions: sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_analytics(monkeypatch)
    user_id = _create_test_user(postgres_sessions, "event-race")
    actor = _actor(user_id)
    with postgres_sessions() as db:
        set_privacy_preference(
            db,
            actor,
            enabled=True,
            idempotency_key="postgres-event-grant",
        )
    barrier = Barrier(2)

    def emit() -> bool:
        with postgres_sessions() as db:
            barrier.wait()
            return emit_product_event_safely(
                db,
                owner_user_id=user_id,
                event_name="analysis_completed",
                metadata={
                    "actor_class": "authenticated",
                    "execution_mode": "durable",
                    "result_class": "report_created",
                },
                source_boundary="job-concurrent-event",
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: emit(), range(2)))
        assert sorted(results) == [False, True]
        with postgres_sessions() as db:
            event = db.execute(
                select(ProductAnalyticsEventModel).where(
                    ProductAnalyticsEventModel.owner_user_id == user_id
                )
            ).scalars().one()
            assert event.event_name == "analysis_completed"
            assert event.dimensions_json == {
                "execution_mode": "durable",
                "result_class": "report_created",
            }
    finally:
        _cleanup_user_data(postgres_sessions, user_id)
        get_settings.cache_clear()


def test_postgres_withdrawal_race_cannot_leave_an_event_after_opt_out(
    postgres_sessions: sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_analytics(monkeypatch)
    user_id = _create_test_user(postgres_sessions, "withdrawal-race")
    actor = _actor(user_id)
    with postgres_sessions() as db:
        set_privacy_preference(
            db,
            actor,
            enabled=True,
            idempotency_key="postgres-withdrawal-grant",
        )
    barrier = Barrier(2)

    def emit() -> bool:
        with postgres_sessions() as db:
            barrier.wait()
            return emit_product_event_safely(
                db,
                owner_user_id=user_id,
                event_name="watchlist_created",
                metadata={"actor_class": "authenticated", "visibility_class": "private"},
                source_boundary="watchlist-withdrawal-race",
            )

    def withdraw() -> str:
        with postgres_sessions() as db:
            barrier.wait()
            return set_privacy_preference(
                db,
                actor,
                enabled=False,
                idempotency_key="postgres-concurrent-withdrawal",
            ).decision

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            emitted = executor.submit(emit)
            withdrawn = executor.submit(withdraw)
            assert withdrawn.result() == "withdraw"
            assert emitted.result() in {True, False}
        with postgres_sessions() as db:
            preference = db.execute(
                select(PrivacyPreferenceModel).where(PrivacyPreferenceModel.user_id == user_id)
            ).scalars().one()
            assert preference.enabled is False
            assert db.scalar(
                select(func.count()).select_from(ProductAnalyticsEventModel).where(
                    ProductAnalyticsEventModel.owner_user_id == user_id
                )
            ) == 0
    finally:
        _cleanup_user_data(postgres_sessions, user_id)
        get_settings.cache_clear()


def _enable_analytics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("PRODUCT_ANALYTICS_ENABLED", "true")
    monkeypatch.setenv("PRODUCT_ANALYTICS_POLICY_VERSION", "phase20b-postgres-v1")
    get_settings.cache_clear()


def _create_test_user(postgres_sessions: sessionmaker, label: str) -> str:
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        user = create_user(db, f"phase20b-{label}-{suffix}@example.test", token=f"token-{suffix}")
        return user.id


def _actor(user_id: str) -> UserContext:
    return UserContext(
        id=user_id,
        email=f"{user_id}@example.test",
        role="common",
        platform_role="user",
        plan="free",
        auth_enabled=True,
        email_verified=True,
    )


def _cleanup_user_data(postgres_sessions: sessionmaker, user_id: str) -> None:
    with postgres_sessions() as db:
        db.execute(delete(ProductAnalyticsEventModel).where(ProductAnalyticsEventModel.owner_user_id == user_id))
        db.execute(delete(PrivacyPreferenceModel).where(PrivacyPreferenceModel.user_id == user_id))
        db.execute(
            delete(PrivacyPreferenceDecisionModel).where(
                PrivacyPreferenceDecisionModel.user_id == user_id
            )
        )
        db.execute(delete(AccessAuditEventModel).where(AccessAuditEventModel.actor_user_id == user_id))
        db.execute(delete(UserModel).where(UserModel.id == user_id))
        db.commit()
