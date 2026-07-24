from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import sessionmaker

from app.auth.schemas import UserContext
from app.auth.service import create_user
from app.core.config import get_settings
from app.db.session import create_database_engine
from app.jobs.control_service import submit_job
from app.jobs.schemas import JobSubmissionRequest
from app.models.job import JobCapacityReservationModel, JobEventModel, JobModel
from app.models.usage_quota import UsageQuotaModel
from app.models.user import UserModel


pytestmark = pytest.mark.postgres_integration


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("PostgreSQL control-plane tests require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL control-plane tests require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_postgres_concurrent_duplicate_submission_reserves_one_job(
    postgres_sessions: sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("JOB_USER_PENDING_LIMIT", "5")
    get_settings.cache_clear()
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        user = create_user(db, f"phase17b-{suffix}@example.test", token=f"phase17b-{suffix}")
        user_id = user.id
    actor = UserContext(
        id=user_id,
        email=f"phase17b-{suffix}@example.test",
        role="common",
        platform_role="user",
        plan="free",
        auth_enabled=True,
        email_verified=True,
    )
    request = JobSubmissionRequest(
        job_type="analysis.generate",
        input_schema_version="analysis.generate.v1",
        input_json={"analysis_request": {"strategy_description": "Concurrent idempotency check.", "protocols": ["aave"], "manual_inputs": {}, "analysis_depth": "standard"}},
    )
    barrier = Barrier(2)

    def submit() -> tuple[str, bool]:
        with postgres_sessions() as db:
            barrier.wait()
            job, duplicate = submit_job(db, actor, request, "phase17b-duplicate-key")
            return job.id, duplicate

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: submit(), range(2)))
        assert len({job_id for job_id, _ in results}) == 1
        assert sorted(duplicate for _, duplicate in results) == [False, True]

        with postgres_sessions() as db:
            jobs = db.execute(select(JobModel).where(JobModel.owner_user_id == user_id)).scalars().all()
            assert len(jobs) == 1
            quota = db.execute(
                select(UsageQuotaModel)
                .where(UsageQuotaModel.subject_id == user_id)
                .where(UsageQuotaModel.action == "analysis")
            ).scalars().one()
            assert quota.used == 1
            capacity = db.execute(
                select(JobCapacityReservationModel)
                .where(JobCapacityReservationModel.scope_type == "user")
                .where(JobCapacityReservationModel.scope_id == user_id)
            ).scalars().one()
            assert capacity.pending_count == 1
    finally:
        with postgres_sessions() as db:
            job_ids = select(JobModel.id).where(JobModel.owner_user_id == user_id)
            db.execute(delete(JobEventModel).where(JobEventModel.job_id.in_(job_ids)))
            db.execute(delete(JobModel).where(JobModel.owner_user_id == user_id))
            db.execute(
                delete(JobCapacityReservationModel).where(
                    (JobCapacityReservationModel.scope_type == "user")
                    & (JobCapacityReservationModel.scope_id == user_id)
                )
            )
            db.execute(delete(UsageQuotaModel).where(UsageQuotaModel.subject_id == user_id))
            db.execute(delete(UserModel).where(UserModel.id == user_id))
            db.commit()
        get_settings.cache_clear()
