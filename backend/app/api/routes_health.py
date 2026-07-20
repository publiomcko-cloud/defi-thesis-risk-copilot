from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.rag.vector_store import JsonVectorStore

router = APIRouter(tags=["health"])


@router.get("/")
def root() -> dict[str, str]:
    settings = get_settings()
    return {
        "service": settings.app_name,
        "status": "online",
        "version": settings.app_version,
        "health": "/health",
        "readiness": "/ready",
        "deployment_status": "/api/deployment/status",
        "docs": "/docs",
        "frontend": "https://defi-thesis-risk-copilot.vercel.app",
    }


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.app_env,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/ready")
def readiness(db: Session = Depends(get_db)) -> dict[str, str | bool]:
    settings = get_settings()
    try:
        db.execute(text("select 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is not ready") from exc

    rag_ready = JsonVectorStore().path.exists()
    if settings.public_demo_mode and not rag_ready:
        raise HTTPException(status_code=503, detail="RAG index is not ready")

    return {
        "status": "ready",
        "database": True,
        "rag_index": rag_ready,
        "timestamp": datetime.now(UTC).isoformat(),
    }
