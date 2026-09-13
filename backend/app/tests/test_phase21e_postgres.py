from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from app.auth.service import create_user, user_context
from app.core.config import get_settings
from app.db.session import create_database_engine
from app.jobs.control_service import cancel_job
from app.models.job import JobCapacityReservationModel
from app.models.training_governance import TrainingRunModel
from app.models.user import UserModel
from app.training_governance.service import submit_training_run


pytestmark = pytest.mark.postgres_integration


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 21E PostgreSQL tests require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("Phase 21E PostgreSQL tests require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_postgres_local_fake_profile_has_one_durable_compute_slot(postgres_sessions: sessionmaker, monkeypatch) -> None:
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        admin = create_user(db, f"phase21e-compute-{suffix}@example.test", role="admin")
        admin_id = admin.id
    barrier = Barrier(2)

    def submit(index: int) -> tuple[str, str | int]:
        with postgres_sessions() as db:
            actor = user_context(db.get(UserModel, admin_id))
            barrier.wait(timeout=10)
            try:
                run, _ = submit_training_run(
                    db,
                    actor,
                    dataset_key=None,
                    execution_mode="dry_run",
                    idempotency_key=f"phase21e-slot-{suffix}-{index}",
                )
                return "accepted", run.id
            except HTTPException as error:
                db.rollback()
                return "rejected", error.status_code

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(submit, range(2)))
        assert sorted(outcome[0] for outcome in outcomes) == ["accepted", "rejected"]
        assert [outcome[1] for outcome in outcomes if outcome[0] == "rejected"] == [429]
        accepted_run_id = next(str(outcome[1]) for outcome in outcomes if outcome[0] == "accepted")
        with postgres_sessions() as db:
            run = db.get(TrainingRunModel, accepted_run_id)
            assert run is not None and run.status == "queued"
            capacity = db.execute(
                select(JobCapacityReservationModel)
                .where(JobCapacityReservationModel.scope_type == "provider")
                .where(JobCapacityReservationModel.scope_id == "training_compute:local_fake_v1")
            ).scalars().one()
            assert (capacity.pending_count, capacity.running_count) == (1, 0)
            cancel_job(db, user_context(db.get(UserModel, admin_id)), run.job_id)
            db.refresh(capacity)
            assert (capacity.pending_count, capacity.running_count) == (0, 0)
            replacement, _ = submit_training_run(
                db,
                user_context(db.get(UserModel, admin_id)),
                dataset_key=None,
                execution_mode="local_fake",
                idempotency_key=f"phase21e-slot-replacement-{suffix}",
            )
            assert replacement.status == "queued"
            cancel_job(db, user_context(db.get(UserModel, admin_id)), replacement.job_id)
    finally:
        get_settings.cache_clear()


def test_postgres_rejects_manifest_and_execution_snapshot_mutation(postgres_sessions: sessionmaker, monkeypatch) -> None:
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    suffix = uuid4().hex[:12]
    try:
        with postgres_sessions() as db:
            admin = create_user(db, f"phase21e-immutable-{suffix}@example.test", role="admin")
            admin_id = admin.id
            run, _ = submit_training_run(
                db,
                user_context(admin),
                dataset_key=None,
                execution_mode="dry_run",
                idempotency_key=f"phase21e-immutable-{suffix}",
            )
            run_id = run.id
            manifest_id = run.manifest_id
        with postgres_sessions() as db:
            with pytest.raises(DBAPIError, match="immutable"):
                db.execute(text("UPDATE training_dataset_manifests SET manifest_checksum = :checksum WHERE id = :id"), {"checksum": "0" * 64, "id": manifest_id})
                db.commit()
            db.rollback()
            with pytest.raises(DBAPIError, match="immutable"):
                db.execute(text("UPDATE training_runs SET execution_snapshot = CAST(:snapshot AS json) WHERE id = :id"), {"snapshot": '{"schema_version":"forged"}', "id": run_id})
                db.commit()
            db.rollback()
            run = db.get(TrainingRunModel, run_id)
            assert run is not None and run.execution_snapshot["schema_version"] == "training.execution.v1"
            cancel_job(db, user_context(db.get(UserModel, admin_id)), run.job_id)
    finally:
        get_settings.cache_clear()
