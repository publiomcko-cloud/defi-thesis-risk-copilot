from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import sessionmaker

from app.auth.schemas import UserContext
from app.auth.service import create_user, user_context
from app.core.config import get_settings
from app.db.session import create_database_engine
from app.jobs.control_service import release_running_capacity, submit_job
from app.jobs.schemas import JobSubmissionRequest, WorkerCredentialCreateRequest, WorkerRegistrationRequest
from app.jobs.worker_protocol import authenticate_worker, claim_next_job
from app.jobs.worker_service import issue_worker_credential, register_worker
from app.models.access_audit_event import AccessAuditEventModel
from app.models.job import JobAttemptModel, JobEventModel, JobModel
from app.models.usage_quota import UsageQuotaModel
from app.models.user import UserModel
from app.models.worker import WorkerCredentialModel, WorkerModel


pytestmark = pytest.mark.postgres_integration


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("PostgreSQL worker claim tests require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL worker claim tests require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_postgres_skip_locked_claim_has_one_winner(
    postgres_sessions: sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("WORKER_API_ENABLED", "true")
    monkeypatch.setenv("WORKER_TOKEN_PEPPER", "phase17c-postgres-pepper")
    get_settings.cache_clear()
    suffix = uuid4().hex[:12]
    user_id = ""
    worker_ids: list[str] = []
    try:
        with postgres_sessions() as db:
            owner = create_user(db, f"phase17c-{suffix}@example.test", token=f"owner-{suffix}")
            admin = create_user(db, f"phase17c-admin-{suffix}@example.test", role="admin", token=f"admin-{suffix}")
            user_id = owner.id
            owner_actor = UserContext(
                id=owner.id,
                email=owner.email,
                role="common",
                platform_role="user",
                plan="free",
                auth_enabled=True,
                email_verified=True,
            )
            job, _ = submit_job(
                db,
                owner_actor,
                JobSubmissionRequest(
                    job_type="analysis.generate",
                    input_schema_version="analysis.generate.v1",
                    input_json={"analysis_request": {"strategy_description": "PostgreSQL SKIP LOCKED claim test.", "protocols": ["aave"], "manual_inputs": {}, "analysis_depth": "standard"}},
                ),
                f"phase17c-claim-{suffix}",
            )
            job_id = job.id
            credentials = []
            for index in range(2):
                worker = register_worker(
                    db,
                    user_context(admin),
                    WorkerRegistrationRequest(
                        name=f"phase17c-claim-{suffix}-{index}",
                        protocol_version="v1",
                        allowed_job_types=["analysis.generate"],
                    ),
                )
                worker_ids.append(worker.id)
                credentials.append(issue_worker_credential(db, user_context(admin), worker.id, WorkerCredentialCreateRequest()).token)
            db.commit()

        barrier = Barrier(2)

        def claim(token: str) -> str | None:
            with postgres_sessions() as db:
                identity = authenticate_worker(db, token, "v1")
                barrier.wait()
                result = claim_next_job(db, identity)
                return result.job.id if result.job else None

        with ThreadPoolExecutor(max_workers=2) as executor:
            winners = list(executor.map(claim, credentials))
        assert winners.count(job_id) == 1
        assert winners.count(None) == 1
    finally:
        if user_id:
            with postgres_sessions() as db:
                jobs = db.execute(select(JobModel).where(JobModel.owner_user_id == user_id)).scalars().all()
                for job in jobs:
                    if job.status in {"leased", "running", "cancel_requested"}:
                        release_running_capacity(db, job)
                job_ids = [job.id for job in jobs]
                db.execute(delete(JobEventModel).where(JobEventModel.job_id.in_(job_ids)))
                db.execute(delete(JobAttemptModel).where(JobAttemptModel.job_id.in_(job_ids)))
                db.execute(delete(JobModel).where(JobModel.id.in_(job_ids)))
                db.execute(delete(WorkerCredentialModel).where(WorkerCredentialModel.worker_id.in_(worker_ids)))
                db.execute(delete(WorkerModel).where(WorkerModel.id.in_(worker_ids)))
                db.execute(delete(UsageQuotaModel).where(UsageQuotaModel.subject_id == user_id))
                db.execute(delete(AccessAuditEventModel).where(AccessAuditEventModel.actor_user_id == user_id))
                db.execute(delete(UserModel).where(UserModel.id == user_id))
                db.commit()
        get_settings.cache_clear()
