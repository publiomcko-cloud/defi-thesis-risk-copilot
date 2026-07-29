from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.operations.controlled_rag import controlled_rag_readiness


def _settings(**overrides) -> Settings:
    values = {
        "app_env": "staging",
        "controlled_rag_validation_enabled": True,
        "controlled_rag_validation_isolated": False,
        "knowledge_storage_enabled": True,
        "document_ingest_enabled": True,
        "jobs_enabled": True,
        "worker_api_enabled": True,
        "knowledge_embeddings_enabled": True,
        "knowledge_shadow_retrieval_enabled": True,
        "knowledge_pgvector_primary_enabled": False,
        "vast_dry_run": True,
        "vast_real_rentals_enabled": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_shadow_rollout_readiness_requires_explicit_safe_configuration_and_hides_secrets(
    monkeypatch: pytest.MonkeyPatch,
    session,
    tmp_path: Path,
) -> None:
    index_path = tmp_path / "index.json"
    index_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("app.operations.controlled_rag._pgvector_ready", lambda _db: True)
    monkeypatch.setattr(
        "app.operations.controlled_rag.JsonVectorStore",
        lambda: SimpleNamespace(path=index_path),
    )
    settings = _settings(supabase_service_role_key="never-return-this")

    with session() as db:
        readiness = controlled_rag_readiness(db, settings, mode="shadow")

    assert readiness.status == "ready"
    assert {check.name for check in readiness.checks} >= {
        "json_fallback_ready",
        "pgvector_primary_disabled",
        "vast_real_rentals_disabled",
    }
    assert "never-return-this" not in str(readiness.payload())
    assert "storage_key" not in str(readiness.payload())


def test_primary_synthetic_readiness_is_blocked_without_isolated_nonproduction_opt_in(
    monkeypatch: pytest.MonkeyPatch,
    session,
    tmp_path: Path,
) -> None:
    index_path = tmp_path / "index.json"
    index_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("app.operations.controlled_rag._pgvector_ready", lambda _db: True)
    monkeypatch.setattr(
        "app.operations.controlled_rag.JsonVectorStore",
        lambda: SimpleNamespace(path=index_path),
    )
    settings = _settings(knowledge_pgvector_primary_enabled=True)

    with session() as db:
        readiness = controlled_rag_readiness(db, settings, mode="primary_synthetic")

    assert readiness.status == "blocked"
    assert next(check for check in readiness.checks if check.name == "isolated_validation").status == "failed"


def test_primary_synthetic_readiness_can_pass_only_in_an_isolated_nonproduction_target(
    monkeypatch: pytest.MonkeyPatch,
    session,
    tmp_path: Path,
) -> None:
    index_path = tmp_path / "index.json"
    index_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("app.operations.controlled_rag._pgvector_ready", lambda _db: True)
    monkeypatch.setattr(
        "app.operations.controlled_rag.JsonVectorStore",
        lambda: SimpleNamespace(path=index_path),
    )
    settings = _settings(
        controlled_rag_validation_isolated=True,
        knowledge_pgvector_primary_enabled=True,
    )

    with session() as db:
        readiness = controlled_rag_readiness(db, settings, mode="primary_synthetic")

    assert readiness.status == "ready"
    assert all(check.status == "passed" for check in readiness.checks)


def test_controlled_primary_can_only_be_configured_in_isolated_nonproduction() -> None:
    with pytest.raises(ValidationError, match="CONTROLLED_RAG_VALIDATION_ENABLED"):
        Settings(_env_file=None, controlled_rag_validation_isolated=True)
    with pytest.raises(ValidationError, match="Phase 22 approval"):
        Settings(
            _env_file=None,
            app_env="production",
            jobs_enabled=True,
            worker_api_enabled=True,
            knowledge_embeddings_enabled=True,
            knowledge_shadow_retrieval_enabled=True,
            knowledge_pgvector_primary_enabled=True,
        )
