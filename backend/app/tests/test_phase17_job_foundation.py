from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.schemas import UserContext
from app.auth.service import create_user
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.jobs.access import get_visible_job
from app.jobs.lifecycle import (
    dispose_jobs_for_account_deletion,
    dispose_jobs_for_organization_deletion,
)
from app.jobs.schemas import WorkerCredentialCreateRequest, WorkerRegistrationRequest
from app.jobs.state import JobTransitionError, append_job_event, transition_job
from app.jobs.worker_service import (
    issue_worker_credential,
    register_worker,
    revoke_worker_credential,
    rotate_worker_credential,
    verify_worker_credential,
)
from app.models.artifact import ArtifactModel
from app.models.access_audit_event import AccessAuditEventModel
from app.models.job import JobEventModel, JobModel
from app.models.organization import OrganizationModel
from app.models.worker import WorkerCredentialModel, WorkerModel
from app.main import app
from scripts.cleanup_expired_data import cleanup_expired_data


@pytest.fixture
def phase17_session(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET_KEY", "phase17-auth-secret")
    monkeypatch.setenv("WORKER_TOKEN_PEPPER", "phase17-worker-pepper")
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


@pytest.fixture
def phase17_client(phase17_session, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "legacy_local")
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()

    def override_get_db():
        db = phase17_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), phase17_session
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_job_transitions_are_closed_and_events_are_append_only(phase17_session) -> None:
    with phase17_session() as db:
        actor = _create_actor(db, "transition-owner")
        job = _job(actor.id)
        db.add(job)
        db.commit()

        transition_job(db, job, "leased", actor_user_id=actor.id)
        transition_job(db, job, "running", actor_user_id=actor.id)
        append_job_event(db, job, event_type="job.progress", message="Processing strategy input.")
        transition_job(db, job, "completed", actor_user_id=actor.id)
        db.commit()

        events = db.execute(
            select(JobEventModel)
            .where(JobEventModel.job_id == job.id)
            .order_by(JobEventModel.sequence_number)
        ).scalars().all()
        assert [event.sequence_number for event in events] == [1, 2, 3, 4]
        assert job.completed_at is not None
        assert job.failed_at is None
        with pytest.raises(JobTransitionError, match="Terminal jobs are immutable"):
            transition_job(db, job, "queued")


def test_job_visibility_never_uses_identifier_as_authority(phase17_session) -> None:
    with phase17_session() as db:
        owner = _create_actor(db, "job-owner")
        outsider = _create_actor(db, "job-outsider")
        job = _job(owner.id)
        db.add(job)
        db.commit()

        assert get_visible_job(db, owner, job.id).id == job.id
        with pytest.raises(HTTPException) as exc:
            get_visible_job(db, outsider, job.id)
        assert exc.value.status_code == 404


def test_worker_credentials_are_hashed_scoped_rotatable_and_revocable(phase17_session) -> None:
    with phase17_session() as db:
        admin = _create_actor(db, "worker-admin", role="admin")
        worker = register_worker(
            db,
            admin,
            WorkerRegistrationRequest(
                name="local-analysis-worker",
                protocol_version="v1",
                software_version="test",
                allowed_job_types=["analysis.generate"],
            ),
        )
        issued = issue_worker_credential(
            db,
            admin,
            worker.id,
            WorkerCredentialCreateRequest(allowed_job_types=["analysis.generate"]),
        )
        db.commit()

        persisted = db.get(WorkerCredentialModel, issued.credential.id)
        assert persisted is not None
        assert issued.token not in persisted.token_hash
        assert issued.token not in persisted.token_prefix
        credential_audit = db.execute(
            select(AccessAuditEventModel).where(AccessAuditEventModel.resource_id == issued.credential.id)
        ).scalars().one()
        assert issued.token not in str(credential_audit.metadata_json)
        assert verify_worker_credential(db, issued.token, required_job_type="analysis.generate") is not None
        assert verify_worker_credential(db, issued.token, required_job_type="vast.session.start") is None
        assert verify_worker_credential(db, "wrk_not-the-issued-token") is None

        rotated = rotate_worker_credential(
            db,
            admin,
            issued.credential.id,
            WorkerCredentialCreateRequest(),
            revoke_previous=True,
        )
        db.commit()
        assert rotated.credential.rotated_from_id == issued.credential.id
        assert verify_worker_credential(db, issued.token) is None
        assert verify_worker_credential(db, rotated.token) is not None

        revoked = revoke_worker_credential(db, admin, rotated.credential.id)
        db.commit()
        assert revoked.status == "revoked"
        assert verify_worker_credential(db, rotated.token) is None


def test_admin_worker_registry_returns_plaintext_credential_once(phase17_client) -> None:
    client, Session = phase17_client
    with Session() as db:
        create_user(db, "worker-admin-route@example.test", role="admin", token="worker-admin-route-token")
        create_user(db, "worker-common-route@example.test", token="worker-common-route-token")

    payload = {
        "name": "route-worker",
        "protocol_version": "v1",
        "allowed_job_types": ["analysis.generate"],
    }
    denied = client.post(
        "/api/admin/workers",
        json=payload,
        headers={"Authorization": "Bearer worker-common-route-token"},
    )
    assert denied.status_code == 403
    created = client.post(
        "/api/admin/workers",
        json=payload,
        headers={"Authorization": "Bearer worker-admin-route-token"},
    )
    assert created.status_code == 200
    worker_id = created.json()["id"]
    issued = client.post(
        f"/api/admin/workers/{worker_id}/credentials",
        json={},
        headers={"Authorization": "Bearer worker-admin-route-token"},
    )
    assert issued.status_code == 200
    raw_token = issued.json()["token"]
    listed = client.get(
        f"/api/admin/workers/{worker_id}/credentials",
        headers={"Authorization": "Bearer worker-admin-route-token"},
    )
    assert listed.status_code == 200
    assert "token" not in listed.json()["items"][0]
    assert raw_token not in str(listed.json())


def test_worker_credential_scope_cannot_exceed_registered_worker_scope(phase17_session) -> None:
    with phase17_session() as db:
        admin = _create_actor(db, "scope-admin", role="admin")
        worker = register_worker(
            db,
            admin,
            WorkerRegistrationRequest(
                name="analysis-only-worker",
                protocol_version="v1",
                allowed_job_types=["analysis.generate"],
            ),
        )
        with pytest.raises(HTTPException) as exc:
            issue_worker_credential(
                db,
                admin,
                worker.id,
                WorkerCredentialCreateRequest(allowed_job_types=["vast.session.start"]),
            )
        assert exc.value.status_code == 422


def test_account_and_organization_disposal_hide_jobs_and_disable_org_workers(phase17_session) -> None:
    with phase17_session() as db:
        owner = _create_actor(db, "disposal-owner")
        org = OrganizationModel(
            id="org_phase17_disposal",
            name="Phase 17 Disposal",
            slug="phase17-disposal",
            status="active",
            created_by_user_id=owner.id,
        )
        db.add(org)
        db.flush()
        account_job = _job(owner.id, job_id="job_account_disposal")
        org_job = _job(
            owner.id,
            job_id="job_org_disposal",
            organization_id=org.id,
            visibility="organization",
        )
        db.add_all([account_job, org_job])
        db.flush()
        artifact = ArtifactModel(
            id="artifact_disposal",
            job_id=account_job.id,
            artifact_type="report_reference",
            status="pending_storage",
            owner_user_id=owner.id,
            visibility="private",
        )
        worker = WorkerModel(
            id="worker_org_disposal",
            name="org-disposal-worker",
            status="active",
            protocol_version="v1",
            capabilities_json={},
            allowed_job_types=["analysis.generate"],
            organization_id=org.id,
            max_concurrency=1,
        )
        credential = WorkerCredentialModel(
            id="workercred_org_disposal",
            worker_id=worker.id,
            token_prefix="wrk_org_disposal_prefix",
            token_hash="hash",
            allowed_job_types=["analysis.generate"],
            status="active",
        )
        db.add_all([artifact, worker, credential])
        db.commit()

        assert dispose_jobs_for_account_deletion(db, owner.id) == 2
        db.commit()
        assert account_job.status == "failed"
        assert account_job.deleted_at is not None
        assert artifact.status == "incomplete"

        # A deleted account disposition is idempotent; organization cleanup still disables workers.
        assert dispose_jobs_for_organization_deletion(db, org.id) == 0
        db.commit()
        assert worker.status == "disabled"
        assert credential.status == "revoked"


def test_job_retention_expires_credentials_and_removes_terminal_records(phase17_session, monkeypatch) -> None:
    with phase17_session() as db:
        owner = _create_actor(db, "retention-owner")
        old_terminal = _job(owner.id, job_id="job_terminal_retention", status="completed")
        old_terminal.completed_at = datetime.now(UTC) - timedelta(days=40)
        old_terminal.updated_at = old_terminal.completed_at
        pending = _job(owner.id, job_id="job_artifact_retention")
        worker = WorkerModel(
            id="worker_retention",
            name="retention-worker",
            status="active",
            protocol_version="v1",
            capabilities_json={},
            allowed_job_types=["analysis.generate"],
            max_concurrency=1,
        )
        credential = WorkerCredentialModel(
            id="workercred_retention",
            worker_id=worker.id,
            token_prefix="wrk_retention_prefix",
            token_hash="retention-hash",
            allowed_job_types=["analysis.generate"],
            status="active",
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        artifact = ArtifactModel(
            id="artifact_retention",
            job_id=pending.id,
            artifact_type="binary_export",
            status="pending_storage",
            owner_user_id=owner.id,
            visibility="private",
            retention_until=datetime.now(UTC) - timedelta(minutes=1),
        )
        db.add_all([old_terminal, pending, worker, credential, artifact])
        db.flush()
        append_job_event(
            db,
            old_terminal,
            event_type="job.completed",
            message="Completed.",
        ).created_at = datetime.now(UTC) - timedelta(days=100)
        db.commit()

    monkeypatch.setattr("scripts.cleanup_expired_data.SessionLocal", phase17_session)
    counts = cleanup_expired_data(dry_run=True)
    assert counts["terminal_jobs_ready_for_retention"] == 1
    assert counts["expired_worker_credentials"] == 1
    assert counts["expired_artifacts"] == 1
    cleanup_expired_data(dry_run=False)

    with phase17_session() as db:
        assert db.get(JobModel, "job_terminal_retention") is None
        assert db.get(WorkerCredentialModel, "workercred_retention").status == "expired"
        retained_artifact = db.get(ArtifactModel, "artifact_retention")
        assert retained_artifact.status == "deleted"
        assert retained_artifact.deleted_at is not None


def test_phase17_configuration_fails_closed_for_production_worker_routes() -> None:
    with pytest.raises(ValueError, match="WORKER_TOKEN_PEPPER"):
        Settings(
            app_env="production",
            jobs_enabled=True,
            worker_api_enabled=True,
            auth_enabled=False,
        )
    with pytest.raises(ValueError, match="ASYNC_ANALYSIS_ENABLED requires JOBS_ENABLED"):
        Settings(async_analysis_enabled=True)
    assert Settings(
        app_env="production",
        jobs_enabled=True,
        worker_api_enabled=True,
        worker_token_pepper="worker-pepper",
        auth_enabled=False,
    ).worker_api_enabled


def _create_actor(db, label: str, role: str = "common") -> UserContext:
    record = create_user(db, f"{label}@example.test", role=role, token=f"{label}-token")
    return UserContext(
        id=record.id,
        email=record.email,
        role=record.role,
        platform_role=record.platform_role,
        plan=record.plan,
        auth_enabled=True,
        email_verified=True,
    )


def _job(
    owner_user_id: str,
    *,
    job_id: str | None = None,
    status: str = "queued",
    organization_id: str | None = None,
    visibility: str = "private",
) -> JobModel:
    now = datetime.now(UTC)
    return JobModel(
        id=job_id or f"job_{owner_user_id[-8:]}",
        job_type="analysis.generate",
        status=status,
        priority_class="standard",
        owner_user_id=owner_user_id,
        organization_id=organization_id,
        created_by_user_id=owner_user_id,
        visibility=visibility,
        input_schema_version="v1",
        input_json={"strategy": "test"},
        request_fingerprint=f"fingerprint-{job_id or owner_user_id}",
        attempt_count=0,
        max_attempts=3,
        available_at=now,
        progress_percent=0,
        idempotency_subject_type="user",
        idempotency_subject_id=owner_user_id,
        idempotency_key=f"key-{job_id or owner_user_id}",
        estimated_cost_microusd=0,
        reserved_cost_microusd=0,
        actual_cost_microusd=0,
        created_at=now,
        updated_at=now,
    )
