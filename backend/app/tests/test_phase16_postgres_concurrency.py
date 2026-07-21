from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth.schemas import UserContext
from app.auth.service import create_user, user_context
from app.core.config import get_settings
from app.db.session import create_database_engine
from app.models.saved_thesis import SavedThesisModel
from app.models.usage_quota import UsageQuotaModel
from app.models.user import UserModel
from app.models.watchlist_item import WatchlistItemModel
from app.quotas.service import ACTION_ANALYSIS, consume_quota
from app.theses.schemas import ThesisCreateRequest
from app.theses.service import create_thesis
from app.watchlist.schemas import WatchlistItemCreate
from app.watchlist.service import create_watchlist_item


pytestmark = pytest.mark.postgres_integration


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("PostgreSQL concurrency tests require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL concurrency tests require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_postgres_concurrent_quota_first_use_is_controlled(
    postgres_sessions: sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QUOTA_FREE_ANALYSES_PER_DAY", "1")
    get_settings.cache_clear()
    user_id = _create_test_user(postgres_sessions, "quota-race")
    actor = _actor(user_id)
    barrier = Barrier(2)

    def consume() -> tuple[str, int | None]:
        with postgres_sessions() as db:
            barrier.wait()
            try:
                return ("ok", consume_quota(db, actor, ACTION_ANALYSIS)["used"])
            except HTTPException as error:
                db.rollback()
                return ("http", error.status_code)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: consume(), range(2)))

        assert sorted(results) == [("http", 429), ("ok", 1)]
        with postgres_sessions() as db:
            record = db.execute(
                select(UsageQuotaModel)
                .where(UsageQuotaModel.subject_type == "user")
                .where(UsageQuotaModel.subject_id == user_id)
                .where(UsageQuotaModel.action == ACTION_ANALYSIS)
            ).scalars().one()
            assert record.used == 1
    finally:
        _cleanup_user_data(postgres_sessions, user_id)
        get_settings.cache_clear()


def test_postgres_exact_quota_limit_then_controlled_429(
    postgres_sessions: sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QUOTA_FREE_ANALYSES_PER_DAY", "2")
    get_settings.cache_clear()
    user_id = _create_test_user(postgres_sessions, "quota-exact")
    actor = _actor(user_id)

    try:
        with postgres_sessions() as db:
            assert consume_quota(db, actor, ACTION_ANALYSIS)["used"] == 1
            assert consume_quota(db, actor, ACTION_ANALYSIS)["used"] == 2
            with pytest.raises(HTTPException) as error:
                consume_quota(db, actor, ACTION_ANALYSIS)
            assert error.value.status_code == 429
    finally:
        _cleanup_user_data(postgres_sessions, user_id)
        get_settings.cache_clear()


@pytest.mark.parametrize("resource", ["saved_theses", "watchlists"])
def test_postgres_resource_limits_serialize_and_release_after_deletion(
    postgres_sessions: sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
    resource: str,
) -> None:
    setting_name = "QUOTA_FREE_SAVED_THESES" if resource == "saved_theses" else "QUOTA_FREE_WATCHLISTS"
    monkeypatch.setenv(setting_name, "1")
    get_settings.cache_clear()
    user_id = _create_test_user(postgres_sessions, resource)
    actor = _actor(user_id)
    barrier = Barrier(2)

    def create(index: int) -> tuple[str, str | int]:
        with postgres_sessions() as db:
            barrier.wait()
            try:
                return ("ok", _create_resource(db, actor, resource, index))
            except HTTPException as error:
                db.rollback()
                return ("http", error.status_code)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(create, range(2)))
        successful_ids = [value for status, value in results if status == "ok"]
        assert len(successful_ids) == 1
        assert sorted(status for status, _ in results) == ["http", "ok"]
        assert next(value for status, value in results if status == "http") == 429

        with postgres_sessions() as db:
            assert _active_resource_count(db, user_id, resource) == 1
            with pytest.raises(HTTPException) as error:
                _create_resource(db, actor, resource, 3)
            assert error.value.status_code == 429
            db.rollback()

            record = db.get(_resource_model(resource), successful_ids[0])
            assert record is not None
            record.deleted_at = datetime.now(UTC)
            db.commit()

            replacement_id = _create_resource(db, actor, resource, 4)
            assert replacement_id != successful_ids[0]
            assert _active_resource_count(db, user_id, resource) == 1
    finally:
        _cleanup_user_data(postgres_sessions, user_id)
        get_settings.cache_clear()


def _create_test_user(postgres_sessions: sessionmaker, label: str) -> str:
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        user = create_user(db, f"phase16-{label}-{suffix}@example.test", token=f"token-{suffix}")
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


def _create_resource(db: Session, actor: UserContext, resource: str, index: int) -> str:
    if resource == "saved_theses":
        response = create_thesis(
            db,
            actor,
            ThesisCreateRequest(
                title=f"Concurrent thesis {index}",
                strategy_text="A sufficiently long concurrent resource strategy.",
                protocols=["aave"],
                visibility="private",
            ),
        )
        return response.id
    response = create_watchlist_item(
        WatchlistItemCreate(
            item_type="market",
            title=f"Concurrent watchlist {index}",
            rules={},
            snapshot={},
        ),
        db,
        actor,
    )
    return response.item.id


def _active_resource_count(db: Session, user_id: str, resource: str) -> int:
    model = _resource_model(resource)
    return db.execute(
        select(func.count())
        .select_from(model)
        .where(model.owner_user_id == user_id)
        .where(model.deleted_at.is_(None))
    ).scalar_one()


def _resource_model(resource: str):
    return SavedThesisModel if resource == "saved_theses" else WatchlistItemModel


def _cleanup_user_data(postgres_sessions: sessionmaker, user_id: str) -> None:
    with postgres_sessions() as db:
        db.execute(delete(SavedThesisModel).where(SavedThesisModel.owner_user_id == user_id))
        db.execute(delete(WatchlistItemModel).where(WatchlistItemModel.owner_user_id == user_id))
        db.execute(delete(UsageQuotaModel).where(UsageQuotaModel.subject_id == user_id))
        db.execute(delete(UserModel).where(UserModel.id == user_id))
        db.commit()
