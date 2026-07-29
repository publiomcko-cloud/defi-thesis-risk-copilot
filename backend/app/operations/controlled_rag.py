"""Fail-closed checks for the narrow Phase 19I durable-RAG rollout.

These checks expose configuration and readiness booleans only. They never
create tenant data, enumerate knowledge records, return storage locations, or
activate a retrieval mode. Operators record the resulting JSON in the approved
private evidence system after a separately approved synthetic exercise.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.rag.vector_store import JsonVectorStore


ControlledRagMode = Literal["shadow", "primary_synthetic"]


@dataclass(frozen=True)
class ControlledRagCheck:
    name: str
    status: Literal["passed", "failed"]


@dataclass(frozen=True)
class ControlledRagReadiness:
    mode: ControlledRagMode
    status: Literal["ready", "blocked"]
    checks: tuple[ControlledRagCheck, ...]

    def payload(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "status": self.status,
            "checks": [asdict(check) for check in self.checks],
        }


def controlled_rag_readiness(
    db: Session,
    settings: Settings,
    *,
    mode: ControlledRagMode,
) -> ControlledRagReadiness:
    """Assess a rollout mode without mutating database, storage, or flags."""

    checks = [
        _check("validation_enabled", settings.controlled_rag_validation_enabled),
        _check("database_ready", _database_ready(db)),
        _check("pgvector_ready", _pgvector_ready(db)),
        _check("json_fallback_ready", JsonVectorStore().path.exists()),
        _check("knowledge_storage_enabled", settings.knowledge_storage_enabled),
        _check("document_ingest_enabled", settings.document_ingest_enabled),
        _check("jobs_enabled", settings.jobs_enabled),
        _check("worker_api_enabled", settings.worker_api_enabled),
        _check("embeddings_enabled", settings.knowledge_embeddings_enabled),
        _check("shadow_retrieval_enabled", settings.knowledge_shadow_retrieval_enabled),
        _check("vast_dry_run", settings.vast_dry_run),
        _check("vast_real_rentals_disabled", not settings.vast_real_rentals_enabled),
    ]
    if mode == "shadow":
        checks.append(_check("pgvector_primary_disabled", not settings.knowledge_pgvector_primary_enabled))
    else:
        checks.extend(
            [
                _check("isolated_validation", settings.controlled_rag_validation_isolated),
                _check("non_production_environment", settings.app_env != "production"),
                _check("pgvector_primary_enabled", settings.knowledge_pgvector_primary_enabled),
            ]
        )

    status: Literal["ready", "blocked"] = "ready" if all(
        check.status == "passed" for check in checks
    ) else "blocked"
    return ControlledRagReadiness(mode=mode, status=status, checks=tuple(checks))


def _check(name: str, passed: bool) -> ControlledRagCheck:
    return ControlledRagCheck(name=name, status="passed" if passed else "failed")


def _database_ready(db: Session) -> bool:
    try:
        db.execute(text("select 1"))
    except Exception:
        return False
    return True


def _pgvector_ready(db: Session) -> bool:
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return False
    try:
        return bool(db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).scalar())
    except Exception:
        return False
