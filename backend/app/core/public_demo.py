from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request

from app.core.config import get_settings

_RATE_WINDOWS: dict[str, deque[float]] = defaultdict(deque)
_RATE_LOCK = Lock()
_WINDOW_SECONDS = 60.0


def block_public_demo_mutation() -> None:
    """Block state-changing or privileged operations in the hosted public demo."""

    if get_settings().public_demo_mode:
        raise HTTPException(
            status_code=403,
            detail="This mutation is disabled in public demo mode.",
        )


def enforce_public_compute_rate_limit(request: Request) -> None:
    """Apply a lightweight per-client limit to public compute endpoints.

    This in-process limiter is intentionally dependency-free for the current
    single-instance portfolio deployment. A shared limiter belongs in the
    multi-instance production roadmap.
    """

    settings = get_settings()
    if not settings.public_demo_mode:
        return

    limit = max(int(getattr(settings, "public_compute_rate_limit_per_minute", 20)), 1)
    now = monotonic()
    key = f"{_client_identifier(request)}:{request.url.path}"

    with _RATE_LOCK:
        window = _RATE_WINDOWS[key]
        cutoff = now - _WINDOW_SECONDS
        while window and window[0] <= cutoff:
            window.popleft()
        if len(window) >= limit:
            raise HTTPException(
                status_code=429,
                detail="Public demo rate limit exceeded. Try again in a minute.",
                headers={"Retry-After": "60"},
            )
        window.append(now)


def reset_public_rate_limits() -> None:
    """Clear limiter state for deterministic tests."""

    with _RATE_LOCK:
        _RATE_WINDOWS.clear()


def _client_identifier(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    if request.client is not None:
        return request.client.host
    return "unknown"
