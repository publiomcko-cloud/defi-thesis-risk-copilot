from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user, user_context
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.models import (
    AnalysisRequestModel,
    ArtifactModel,
    JobModel,
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeSourceModel,
    ReportModel,
)
from app.operations.backup_restore import (
    create_sanitized_restore_manifest,
    verify_sanitized_restore_manifest,
)
from app.providers.credential_service import (
    create_provider_credential,
    disable_provider_credential,
    get_enabled_credential_secret,
    update_provider_credential,
)
from app.providers.schemas import ProviderCredentialCreateRequest, ProviderCredentialUpdateRequest
from scripts.cleanup_expired_data import _require_backup_evidence
from scripts import run_sanitized_restore_drill as restore_script


@pytest.fixture()
def recovery_session(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", "phase19e-test-encryption-key")
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


def test_sanitized_manifest_verifies_restore_metadata_without_sensitive_data(recovery_session) -> None:
    with recovery_session() as db:
        _seed_restore_inventory(db)
        manifest = create_sanitized_restore_manifest(db, fingerprint_salt="phase19e-test-salt")
        serialized = manifest.model_dump_json()

        assert manifest.resource_counts["reports"] == 1
        assert manifest.resource_counts["jobs"] == 1
        assert manifest.resource_counts["knowledge_versions"] == 1
        assert verify_sanitized_restore_manifest(manifest, db).passed is True
        for forbidden in (
            "owner@example.test",
            "Sensitive strategy details",
            "Sensitive report summary",
            "private/owner/super-secret-object-key.pdf",
            "Sensitive chunk content",
            "owner-token",
        ):
            assert forbidden not in serialized

    target_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(target_engine)
    TargetSession = sessionmaker(bind=target_engine, autoflush=False, autocommit=False)
    with TargetSession() as restored_db:
        _seed_restore_inventory(restored_db)
        assert verify_sanitized_restore_manifest(manifest, restored_db).passed is True

    with recovery_session() as db:
        report = db.get(ReportModel, "report_phase19e")
        assert report is not None
        report.risk_rating = "high"
        db.commit()
        verification = verify_sanitized_restore_manifest(manifest, db)

    assert verification.passed is False
    assert verification.mismatched_collections == ["reports"]


def test_recovery_configuration_and_retention_guard_are_fail_closed() -> None:
    with pytest.raises(ValidationError, match="BACKUP_RESTORE_EVIDENCE_REFERENCE"):
        Settings(backup_retention_guard_enabled=True)
    with pytest.raises(ValidationError, match="BACKUP_RPO_HOURS"):
        Settings(backup_rpo_hours=0)
    with pytest.raises(RuntimeError, match="backup/restore evidence"):
        _require_backup_evidence("")
    _require_backup_evidence("restore-drill-2026-07-28")


def test_restore_drill_command_is_disabled_and_blocks_production(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path,
) -> None:
    target = tmp_path / "manifest.json"
    monkeypatch.setattr("sys.argv", ["run_sanitized_restore_drill.py", "--write-manifest", str(target)])
    monkeypatch.setattr(restore_script, "get_settings", lambda: Settings())
    assert restore_script.main() == 2
    assert '"status": "disabled"' in capsys.readouterr().out

    monkeypatch.setattr(
        restore_script,
        "get_settings",
        lambda: Settings(backup_restore_drill_enabled=True, app_env="production"),
    )
    assert restore_script.main() == 2
    assert '"status": "blocked"' in capsys.readouterr().out


def test_provider_credential_rotation_and_emergency_disable_are_auditable(recovery_session) -> None:
    with recovery_session() as db:
        admin = create_user(db, "phase19e-admin@example.test", role="admin", token="admin-token")
        actor = user_context(admin)
        created = create_provider_credential(
            ProviderCredentialCreateRequest(provider="openai_compatible", name="phase19e", secret="old-service-secret"),
            db,
            actor,
        )
        rotated = update_provider_credential(
            created.id,
            ProviderCredentialUpdateRequest(secret="new-service-secret"),
            db,
            actor,
        )
        assert get_enabled_credential_secret(db, "openai_compatible", "phase19e") == "new-service-secret"
        disabled = disable_provider_credential(rotated.id, db, actor)

    assert disabled.enabled is False
    assert "service-secret" not in str(created)
    assert "service-secret" not in str(rotated)


def _seed_restore_inventory(db) -> None:
    now = datetime.now(UTC)
    owner = create_user(db, "owner@example.test", token="owner-token")
    job = JobModel(
        id="job_phase19e",
        job_type="analysis.generate",
        status="completed",
        priority_class="standard",
        owner_user_id=owner.id,
        created_by_user_id=owner.id,
        visibility="private",
        input_schema_version="analysis.generate.v1",
        input_json={"strategy": "Sensitive strategy details"},
        request_fingerprint="phase19e-request",
        attempt_count=1,
        max_attempts=3,
        available_at=now,
        progress_percent=100,
        idempotency_subject_type="user",
        idempotency_subject_id=owner.id,
        idempotency_key="phase19e-key",
        estimated_cost_microusd=0,
        reserved_cost_microusd=0,
        actual_cost_microusd=0,
        created_at=now,
        updated_at=now,
    )
    request = AnalysisRequestModel(
        id="request_phase19e",
        strategy_description="Sensitive strategy details",
        protocols=["aave"],
        manual_inputs_json={"token": "sensitive-manual-input"},
        analysis_depth="standard",
        owner_user_id=owner.id,
        visibility="private",
        created_at=now,
    )
    report = ReportModel(
        id="report_phase19e",
        analysis_request_id=request.id,
        title="Sensitive report title",
        risk_rating="medium",
        summary="Sensitive report summary",
        report_markdown="Sensitive report markdown",
        report_json={"token": "sensitive-report-value"},
        source_job_id=job.id,
        owner_user_id=owner.id,
        visibility="private",
        created_at=now,
    )
    artifact = ArtifactModel(
        id="artifact_phase19e",
        job_id=job.id,
        artifact_type="report_markdown",
        status="available",
        owner_user_id=owner.id,
        visibility="private",
        storage_backend="supabase_private",
        storage_key="private/owner/super-secret-object-key.pdf",
        created_at=now,
        updated_at=now,
    )
    source = KnowledgeSourceModel(
        id="ksrc_phase19e",
        owner_user_id=owner.id,
        visibility="private",
        source_type="upload",
        source_uri="https://private.example.test/sensitive",
        title="Sensitive knowledge title",
        status="ingested",
        trust_state="approved_for_rag",
        created_by_user_id=owner.id,
        created_at=now,
        updated_at=now,
    )
    document = KnowledgeDocumentModel(
        id="kdoc_phase19e",
        knowledge_source_id=source.id,
        current_version_id="kver_phase19e",
        filename="sensitive.pdf",
        media_type="application/pdf",
        status="ready",
        created_at=now,
        updated_at=now,
    )
    version = KnowledgeDocumentVersionModel(
        id="kver_phase19e",
        document_id=document.id,
        version_number=1,
        storage_key="private/owner/super-secret-object-key.pdf",
        size_bytes=123,
        parser_version="pdf.v1",
        chunker_version="chunker.v1",
        status="ready",
        created_at=now,
    )
    chunk = KnowledgeChunkModel(
        id="kchunk_phase19e",
        document_version_id=version.id,
        chunk_index=0,
        heading_path=["Sensitive heading"],
        content="Sensitive chunk content",
        content_checksum="a" * 64,
        token_count=3,
        metadata_json={"secret": "chunk-secret"},
        created_at=now,
    )
    db.add_all([job, request, report, artifact, source, document, version, chunk])
    db.commit()
