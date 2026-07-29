"""Shared database rate limiting with server-derived, privacy-safe scopes."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import ceil
from uuid import uuid4

from fastapi import HTTPException, Request, Response
from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth.policies import WRITE_ORG_ROLES, has_org_role
from app.auth.schemas import UserContext
from app.core.config import Settings, get_settings
from app.core.observability import safe_log_fields
from app.models.rate_limit import RateLimitBucketModel

logger = logging.getLogger("defi_copilot.rate_limits")

ACTION_PUBLIC_COMPUTE = "compute.public"
ACTION_AUTHENTICATED_COMPUTE = "compute.authenticated"
ACTION_JOB_SUBMISSION = "jobs.submit"


@dataclass(frozen=True)
class RateLimitWindow:
    limit: int
    window_seconds: int


@dataclass(frozen=True)
class RateLimitScope:
    scope_type: str
    identifier: str


@dataclass(frozen=True)
class RateLimitDecision:
    action: str
    mode: str
    limited: bool
    remaining: int | None
    reset_at: datetime | None
    would_block: bool = False


def enforce_public_compute_rate_limit(
    request: Request,
    response: Response,
    db: Session,
    actor: UserContext,
) -> None:
    """FastAPI dependency for bounded analysis, simulation, options, and data calls."""

    settings = get_settings()
    if _shared_limiter_enabled(settings):
        action = ACTION_PUBLIC_COMPUTE if actor.anonymous_session_id else ACTION_AUTHENTICATED_COMPUTE
        decision = enforce_rate_limit(
            db,
            request,
            actor,
            action=action,
            settings=settings,
        )
        _write_rate_limit_headers(response, decision)
        return

    # Preserve the original public-demo behavior until a shared limiter has an
    # explicit shadow/enforce rollout. This is intentionally not described as
    # distributed protection.
    if not settings.public_demo_mode:
        return
    _enforce_legacy_public_demo_limit(request, settings)


def enforce_job_submission_rate_limit(
    db: Session,
    request: Request,
    actor: UserContext,
    organization_id: str | None,
) -> RateLimitDecision | None:
    """Limit cost-bearing durable job admission before a reservation is created."""

    settings = get_settings()
    if not _shared_limiter_enabled(settings):
        return None
    if organization_id and not has_org_role(db, actor.id, organization_id, WRITE_ORG_ROLES):
        # Match the existing job service behavior and never trust a submitted
        # organization id merely to construct a less-contended limiter key.
        raise HTTPException(status_code=404, detail="Organization not found")
    return enforce_rate_limit(
        db,
        request,
        actor,
        action=ACTION_JOB_SUBMISSION,
        organization_id=organization_id,
        settings=settings,
    )


def enforce_rate_limit(
    db: Session,
    request: Request,
    actor: UserContext,
    *,
    action: str,
    organization_id: str | None = None,
    settings: Settings | object | None = None,
    now: datetime | None = None,
) -> RateLimitDecision:
    """Apply all server-derived scopes atomically enough to fail closed safely."""

    settings = settings or get_settings()
    mode = str(getattr(settings, "rate_limiting_mode", "shadow"))
    windows = _windows_for(action, settings)
    current_time = now or _database_now(db)
    scopes = _scopes_for_request(request, actor, organization_id, settings)
    try:
        decision = _consume_scopes(db, scopes, action, windows, current_time, settings, mode)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "Shared rate limiter unavailable",
            extra={
                "event": "rate_limit.backend_unavailable",
                "observability": safe_log_fields(action=action, mode=mode, exception_type=type(exc).__name__),
            },
        )
        if mode == "enforce":
            raise HTTPException(
                status_code=503,
                detail="Request protection is temporarily unavailable. Retry shortly.",
                headers={"Retry-After": "5"},
            ) from None
        return RateLimitDecision(action=action, mode=mode, limited=False, remaining=None, reset_at=None)

    if decision.would_block:
        logger.warning(
            "Rate limit threshold reached",
            extra={
                "event": "rate_limit.threshold_reached",
                "observability": safe_log_fields(
                    action=action,
                    mode=mode,
                    retry_after_seconds=_retry_after_seconds(decision.reset_at, current_time),
                ),
            },
        )
        if mode == "enforce":
            raise HTTPException(
                status_code=429,
                detail="Request rate limit exceeded. Retry later.",
                headers=_rate_limit_headers(decision, current_time),
            )
    return decision


def rate_limit_summary(db: Session) -> dict:
    """Return aggregate metadata only; rate-limit scope identifiers stay hashed."""

    now = _database_now(db)
    rows = db.execute(
        select(
            RateLimitBucketModel.action,
            func.count(RateLimitBucketModel.id),
            func.coalesce(func.sum(RateLimitBucketModel.request_count), 0),
        )
        .where(RateLimitBucketModel.expires_at > now)
        .group_by(RateLimitBucketModel.action)
        .order_by(RateLimitBucketModel.action)
    ).all()
    return {
        "mode": "disabled" if not _shared_limiter_enabled(get_settings()) else get_settings().rate_limiting_mode,
        "active_bucket_count": sum(int(row[1]) for row in rows),
        "actions": [
            {"action": str(row[0]), "active_bucket_count": int(row[1]), "request_count": int(row[2])}
            for row in rows
        ],
    }


def _consume_scopes(
    db: Session,
    scopes: list[RateLimitScope],
    action: str,
    windows: tuple[RateLimitWindow, RateLimitWindow],
    now: datetime,
    settings: Settings | object,
    mode: str,
) -> RateLimitDecision:
    outcomes: list[tuple[int, datetime, bool]] = []
    try:
        with db.begin_nested():
            for scope in scopes:
                for window in windows:
                    count, reset_at, allowed = _increment_bucket(
                        db, scope, action, window, now, settings
                    )
                    outcomes.append((window.limit - count if allowed else 0, reset_at, allowed))
            if not all(allowed for _, _, allowed in outcomes):
                # A rejected request consumes no partial set of scope buckets.
                raise _RateLimitExceeded(outcomes)
        db.commit()
    except _RateLimitExceeded as exc:
        db.rollback()
        remaining = min((remaining for remaining, _, _ in exc.outcomes), default=0)
        reset_at = max((reset for _, reset, allowed in exc.outcomes if not allowed), default=None)
        return RateLimitDecision(
            action=action,
            mode=mode,
            limited=True,
            remaining=max(remaining, 0),
            reset_at=reset_at,
            would_block=True,
        )

    remaining = min((remaining for remaining, _, _ in outcomes), default=None)
    reset_at = min((reset for _, reset, _ in outcomes), default=None)
    return RateLimitDecision(
        action=action,
        mode=mode,
        limited=True,
        remaining=max(remaining, 0) if remaining is not None else None,
        reset_at=reset_at,
    )


class _RateLimitExceeded(Exception):
    def __init__(self, outcomes: list[tuple[int, datetime, bool]]) -> None:
        self.outcomes = outcomes


def _increment_bucket(
    db: Session,
    scope: RateLimitScope,
    action: str,
    window: RateLimitWindow,
    now: datetime,
    settings: Settings | object,
) -> tuple[int, datetime, bool]:
    window_started_at = _window_start(now, window.window_seconds)
    reset_at = window_started_at + timedelta(seconds=window.window_seconds)
    scope_key_hash = _scope_key_hash(scope, settings)
    unique = {
        "scope_type": scope.scope_type,
        "scope_key_hash": scope_key_hash,
        "action": action,
        "window_seconds": window.window_seconds,
        "window_started_at": window_started_at,
    }
    expires_at = reset_at + timedelta(seconds=int(getattr(settings, "rate_limit_retention_seconds", 86_400)))
    _insert_bucket_if_missing(db, unique, window, expires_at, now)
    updated = db.execute(
        update(RateLimitBucketModel)
        .where(*(getattr(RateLimitBucketModel, key) == value for key, value in unique.items()))
        .where(RateLimitBucketModel.request_count < window.limit)
        .values(request_count=RateLimitBucketModel.request_count + 1, updated_at=now)
        .returning(RateLimitBucketModel.request_count)
    ).scalar_one_or_none()
    return (int(updated or window.limit), reset_at, updated is not None)


def _insert_bucket_if_missing(
    db: Session,
    unique: dict[str, object],
    window: RateLimitWindow,
    expires_at: datetime,
    now: datetime,
) -> None:
    values = {
        "id": f"rlb_{uuid4().hex[:20]}",
        **unique,
        "request_count": 0,
        "limit_value": window.limit,
        "expires_at": expires_at,
        "created_at": now,
        "updated_at": now,
    }
    dialect = db.bind.dialect.name if db.bind is not None else ""
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    elif dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    else:
        existing = db.execute(
            select(RateLimitBucketModel.id).where(
                *(getattr(RateLimitBucketModel, key) == value for key, value in unique.items())
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(RateLimitBucketModel(**values))
            db.flush()
        return
    db.execute(insert(RateLimitBucketModel).values(**values).on_conflict_do_nothing())


def _windows_for(action: str, settings: Settings | object) -> tuple[RateLimitWindow, RateLimitWindow]:
    prefix = {
        ACTION_PUBLIC_COMPUTE: "rate_limit_public_compute",
        ACTION_AUTHENTICATED_COMPUTE: "rate_limit_authenticated_compute",
        ACTION_JOB_SUBMISSION: "rate_limit_job_submit",
    }.get(action)
    if prefix is None:
        raise ValueError(f"Unsupported rate-limit action: {action}")
    return (
        RateLimitWindow(
            int(getattr(settings, f"{prefix}_burst_limit")),
            int(getattr(settings, f"{prefix}_burst_window_seconds")),
        ),
        RateLimitWindow(
            int(getattr(settings, f"{prefix}_sustained_limit")),
            int(getattr(settings, f"{prefix}_sustained_window_seconds")),
        ),
    )


def _scopes_for_request(
    request: Request,
    actor: UserContext,
    organization_id: str | None,
    settings: Settings | object,
) -> list[RateLimitScope]:
    scopes = [RateLimitScope("ip", client_identifier(request, settings))]
    if actor.anonymous_session_id:
        scopes.append(RateLimitScope("session", actor.anonymous_session_id))
    else:
        scopes.append(RateLimitScope("user", actor.id))
    if organization_id:
        scopes.append(RateLimitScope("organization", organization_id))
    return scopes


def client_identifier(request: Request, settings: Settings | object) -> str:
    """Derive an IP scope only from the connection or an explicit trusted proxy."""

    client_host = request.client.host if request.client is not None else "unknown"
    if _is_trusted_proxy(client_host, str(getattr(settings, "rate_limit_trusted_proxy_cidrs", ""))):
        forwarded = request.headers.get("x-forwarded-for", "")
        candidate = forwarded.split(",", 1)[0].strip()
        if _is_ip_address(candidate):
            return candidate
    return client_host if _is_ip_address(client_host) else "unknown"


def _is_trusted_proxy(host: str, configured_cidrs: str) -> bool:
    if not _is_ip_address(host):
        return False
    address = ipaddress.ip_address(host)
    for candidate in (item.strip() for item in configured_cidrs.split(",")):
        if not candidate:
            continue
        try:
            if address in ipaddress.ip_network(candidate, strict=False):
                return True
        except ValueError:
            continue
    return False


def _is_ip_address(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def _scope_key_hash(scope: RateLimitScope, settings: Settings | object) -> str:
    pepper = str(getattr(settings, "rate_limit_key_pepper", "") or "development-rate-limit-pepper")
    payload = f"{scope.scope_type}:{scope.identifier}".encode("utf-8")
    return hmac.new(pepper.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _window_start(now: datetime, window_seconds: int) -> datetime:
    normalized = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
    epoch = int(normalized.timestamp())
    return datetime.fromtimestamp(epoch - (epoch % window_seconds), tz=UTC)


def _database_now(db: Session) -> datetime:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        value = db.execute(select(func.now())).scalar_one()
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return datetime.now(UTC)


def _shared_limiter_enabled(settings: Settings | object) -> bool:
    return bool(getattr(settings, "rate_limiting_enabled", False))


def _retry_after_seconds(reset_at: datetime | None, now: datetime) -> int:
    if reset_at is None:
        return 1
    return max(1, ceil((reset_at - now).total_seconds()))


def _rate_limit_headers(decision: RateLimitDecision, now: datetime) -> dict[str, str]:
    headers = {
        "Retry-After": str(_retry_after_seconds(decision.reset_at, now)),
        "X-RateLimit-Remaining": str(decision.remaining or 0),
        "X-RateLimit-Policy": decision.action,
    }
    if decision.reset_at is not None:
        headers["X-RateLimit-Reset"] = str(int(decision.reset_at.timestamp()))
    return headers


def _write_rate_limit_headers(response: Response, decision: RateLimitDecision) -> None:
    response.headers["X-RateLimit-Mode"] = decision.mode
    response.headers["X-RateLimit-Policy"] = decision.action
    if decision.remaining is not None:
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
    if decision.reset_at is not None:
        response.headers["X-RateLimit-Reset"] = str(int(decision.reset_at.timestamp()))
