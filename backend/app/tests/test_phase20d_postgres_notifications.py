from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import sessionmaker

from app.auth.service import create_user
from app.db.session import create_database_engine
from app.models.notification import NotificationModel, NotificationPreferenceModel
from app.models.user import UserModel
from app.notifications.service import emit_notification_intent


pytestmark = pytest.mark.postgres_integration


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("PostgreSQL notification tests require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL notification tests require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_postgres_concurrent_notification_emit_creates_one_logical_notification(postgres_sessions: sessionmaker) -> None:
    user_id = _create_test_user(postgres_sessions, "notification-race")
    barrier = Barrier(2)

    def emit() -> bool:
        with postgres_sessions() as db:
            barrier.wait()
            _record, duplicate = emit_notification_intent(
                db,
                owner_user_id=user_id,
                template_id="job.status.completed",
                source_id="job_postgres_race",
                idempotency_key="job:job_postgres_race:completed",
                commit=True,
            )
            return duplicate

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = sorted(executor.map(lambda _: emit(), range(2)))
        assert results == [False, True]
        with postgres_sessions() as db:
            assert db.scalar(
                select(func.count()).select_from(NotificationModel).where(
                    NotificationModel.owner_user_id == user_id
                )
            ) == 1
            notification = db.execute(
                select(NotificationModel).where(NotificationModel.owner_user_id == user_id)
            ).scalars().one()
            assert notification.idempotency_key == "job:job_postgres_race:completed"
            assert notification.policy_outcome == "suppressed_by_preference"
            assert db.scalar(
                select(func.count()).select_from(NotificationPreferenceModel).where(
                    NotificationPreferenceModel.user_id == user_id
                )
            ) == 1
    finally:
        _cleanup_user_data(postgres_sessions, user_id)


def _create_test_user(postgres_sessions: sessionmaker, label: str) -> str:
    with postgres_sessions() as db:
        user = create_user(
            db,
            f"phase20d-postgres-{label}@example.test",
            token=f"phase20d-postgres-{label}",
        )
        return user.id


def _cleanup_user_data(postgres_sessions: sessionmaker, user_id: str) -> None:
    with postgres_sessions() as db:
        db.execute(delete(NotificationModel).where(NotificationModel.owner_user_id == user_id))
        db.execute(delete(NotificationPreferenceModel).where(NotificationPreferenceModel.user_id == user_id))
        db.execute(delete(UserModel).where(UserModel.id == user_id))
        db.commit()
