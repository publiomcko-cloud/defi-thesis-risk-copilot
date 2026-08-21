from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.auth.service import create_user
from app.db.session import create_database_engine
from app.entitlements.service import emit_usage, resolve_entitlements, reverse_usage
from app.models.entitlement import EntitlementAssignmentModel, UsageEventModel
from app.models.user import UserModel

pytestmark = pytest.mark.postgres_integration


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 20F PostgreSQL tests require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("Phase 20F PostgreSQL tests require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_postgres_resolution_is_read_only_and_usage_and_reversal_have_one_winner(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        user = create_user(db, f"phase20f-{suffix}@example.test", token=f"phase20f-{suffix}")
        user_id = user.id
        db.commit()
    barrier = Barrier(2)

    def resolve() -> str:
        with postgres_sessions() as db:
            barrier.wait()
            return resolve_entitlements(db, user_id)["provenance"]

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            assert list(executor.map(lambda _: resolve(), range(2))) == ["implicit_server_default", "implicit_server_default"]
        with postgres_sessions() as db:
            assert not db.execute(select(EntitlementAssignmentModel).where(EntitlementAssignmentModel.subject_id == user_id)).scalars().all()
        barrier = Barrier(2)
        def meter() -> str:
            with postgres_sessions() as db:
                barrier.wait()
                event = emit_usage(db, owner_user_id=user_id, unit_key="usage.analysis.completed.v1", source_type="job", source_id="same-job")
                db.commit()
                return event.id
        with ThreadPoolExecutor(max_workers=2) as executor:
            event_ids = list(executor.map(lambda _: meter(), range(2)))
        assert len(set(event_ids)) == 1
        barrier = Barrier(2)
        def reverse() -> str:
            with postgres_sessions() as db:
                barrier.wait()
                event = reverse_usage(db, event_id=event_ids[0], correction_code="operator_test_cleanup")
                db.commit()
                return event.id
        with ThreadPoolExecutor(max_workers=2) as executor:
            assert len(set(executor.map(lambda _: reverse(), range(2)))) == 1
    finally:
        with postgres_sessions() as db:
            db.execute(delete(UsageEventModel).where(UsageEventModel.owner_user_id == user_id))
            db.execute(delete(EntitlementAssignmentModel).where(EntitlementAssignmentModel.subject_id == user_id))
            db.execute(delete(UserModel).where(UserModel.id == user_id))
            db.commit()


def test_postgres_assignment_overlap_is_rejected_and_corrupt_catalog_falls_back(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        user = create_user(db, f"phase20f-overlap-{suffix}@example.test")
        user_id = user.id
        first = EntitlementAssignmentModel(id=f"assignment_{suffix}", subject_type="user", subject_id=user_id, plan_version_id="plan_free_v1", effective_from=datetime(2026, 8, 21, tzinfo=UTC), source="test")
        db.add(first)
        db.commit()
        db.add(EntitlementAssignmentModel(id=f"assignment_second_{suffix}", subject_type="user", subject_id=user_id, plan_version_id="plan_free_v1", effective_from=datetime(2026, 8, 22, tzinfo=UTC), source="test"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        assert resolve_entitlements(db, user_id)["shadow"] == "parity"
        db.execute(delete(EntitlementAssignmentModel).where(EntitlementAssignmentModel.subject_id == user_id))
        db.execute(delete(UserModel).where(UserModel.id == user_id))
        db.commit()
