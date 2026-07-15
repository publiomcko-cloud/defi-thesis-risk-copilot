from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.demo.seed_data import get_demo_status

router = APIRouter(tags=["deployment"])


class DeploymentStatus(BaseModel):
    status: str
    app_environment: str
    public_demo_mode: bool
    database_connected: bool
    demo_seeded: bool
    auth_enabled: bool
    llm_synthesis_enabled: bool
    llm_provider: str
    vast_enabled: bool
    vast_dry_run: bool
    rag_semantic_enabled: bool
    version: str
    commit: str | None
    timestamp: str


@router.get("/deployment/status", response_model=DeploymentStatus)
def read_deployment_status(db: Session = Depends(get_db)) -> DeploymentStatus:
    settings = get_settings()
    database_connected = _database_connected(db)
    demo_seeded = False
    if database_connected:
        try:
            demo_seeded = get_demo_status(db).seeded
        except Exception:
            demo_seeded = False

    return DeploymentStatus(
        status="ok" if database_connected else "degraded",
        app_environment=settings.app_env,
        public_demo_mode=settings.public_demo_mode,
        database_connected=database_connected,
        demo_seeded=demo_seeded,
        auth_enabled=settings.auth_enabled,
        llm_synthesis_enabled=settings.llm_synthesis_enabled,
        llm_provider=settings.llm_provider,
        vast_enabled=settings.vast_enabled,
        vast_dry_run=settings.vast_dry_run,
        rag_semantic_enabled=settings.rag_semantic_enabled,
        version=settings.app_version,
        commit=settings.deployment_commit[:12] if settings.deployment_commit else None,
        timestamp=datetime.now(UTC).isoformat(),
    )


def _database_connected(db: Session) -> bool:
    try:
        db.execute(text("select 1"))
        return True
    except Exception:
        return False
