"""Safe Phase 19A correlation and operational-readiness helpers.

This module deliberately does not export telemetry to a third party.  It keeps
correlation local, structured, bounded, and redacted while later Phase 19 work
selects an approved exporter and retention policy.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, Iterator
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings

CORRELATION_HEADER = "X-Correlation-ID"
REQUEST_ID_HEADER = "X-Request-ID"
_CORRELATION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")
_SENSITIVE_KEY_PARTS = frozenset(
    {
        "authorization",
        "cookie",
        "credential",
        "password",
        "secret",
        "token",
        "api_key",
        "private_key",
        "storage_key",
    }
)
_SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)(bearer\s+\S+|(?:api[_-]?key|token|secret|password|cookie|authorization)\s*[=:]\s*\S+)"
)
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_operation: ContextVar[str | None] = ContextVar("observability_operation", default=None)
_job_id: ContextVar[str | None] = ContextVar("observability_job_id", default=None)


def new_correlation_id(prefix: str = "corr") -> str:
    return f"{prefix}_{uuid4().hex}"


def normalize_correlation_id(value: str | None, *, prefix: str = "corr") -> str:
    candidate = (value or "").strip()
    return candidate if _CORRELATION_PATTERN.fullmatch(candidate) else new_correlation_id(prefix)


@contextmanager
def correlation_context(
    correlation_id: str | None = None,
    *,
    operation: str | None = None,
    job_id: str | None = None,
) -> Iterator[str]:
    normalized = normalize_correlation_id(correlation_id)
    correlation_token = _correlation_id.set(normalized)
    operation_token = _operation.set(operation)
    job_token = _job_id.set(job_id)
    try:
        yield normalized
    finally:
        _job_id.reset(job_token)
        _operation.reset(operation_token)
        _correlation_id.reset(correlation_token)


def current_correlation_id() -> str | None:
    return _correlation_id.get()


def current_log_context() -> dict[str, str]:
    context: dict[str, str] = {}
    if correlation_id := _correlation_id.get():
        context["correlation_id"] = correlation_id
    if operation := _operation.get():
        context["operation"] = operation
    if job_id := _job_id.get():
        context["job_id"] = job_id
    return context


def correlation_headers(correlation_id: str | None = None) -> dict[str, str]:
    value = normalize_correlation_id(correlation_id or current_correlation_id())
    return {CORRELATION_HEADER: value, REQUEST_ID_HEADER: value}


def correlation_id_from_job_input(payload: object) -> str:
    if isinstance(payload, dict):
        context = payload.get("_server_context")
        if isinstance(context, dict) and isinstance(context.get("correlation_id"), str):
            return normalize_correlation_id(context["correlation_id"])
    return new_correlation_id("jobcorr")


def redact_value(value: Any, *, field_name: str | None = None) -> Any:
    """Return bounded JSON-compatible log data without sensitive values."""

    normalized_name = (field_name or "").lower().replace("-", "_")
    if any(part in normalized_name for part in _SENSITIVE_KEY_PARTS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(key)[:80]: redact_value(item, field_name=str(key)) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [redact_value(item) for item in list(value)[:50]]
    if isinstance(value, str):
        if _SENSITIVE_VALUE_PATTERN.search(value):
            return "[REDACTED]"
        return value[:512]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return "[REDACTED]"


def safe_log_fields(**fields: Any) -> dict[str, Any]:
    return {key: redact_value(value, field_name=key) for key, value in fields.items()}


def operational_readiness(db: Session, settings: Settings | None = None) -> dict[str, Any]:
    """Return a safe, read-only Phase 19A readiness projection."""

    settings = settings or get_settings()
    database_ready = False
    try:
        db.execute(text("select 1"))
        database_ready = True
    except Exception:
        database_ready = False

    from app.rag.vector_store import JsonVectorStore

    return {
        "status": "ready" if database_ready and JsonVectorStore().path.exists() else "degraded",
        "checked_at": datetime.now(UTC).isoformat(),
        "database_ready": database_ready,
        "json_fallback_ready": JsonVectorStore().path.exists(),
        "structured_logging": True,
        "correlation_headers": True,
        "observability_mode": "local_only" if settings.observability_enabled else "local_baseline",
        "telemetry_export": "not_implemented",
        "shared_rate_limiting": "disabled" if not settings.rate_limiting_enabled else settings.rate_limiting_mode,
        "release_id_configured": bool(settings.observability_release_id),
        "knowledge_pgvector_primary_enabled": settings.knowledge_pgvector_primary_enabled,
        "vast_dry_run": settings.vast_dry_run,
        "vast_real_rentals_enabled": settings.vast_real_rentals_enabled,
    }
