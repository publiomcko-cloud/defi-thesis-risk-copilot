"""Execution ownership checks for inline research runs."""

from __future__ import annotations

import threading
from hashlib import sha256

from sqlalchemy import text
from sqlalchemy.orm import Session


_ACTIVE_RUNS: set[str] = set()
_ACTIVE_RUNS_LOCK = threading.Lock()


def mark_local_run_active(run_id: str) -> None:
    with _ACTIVE_RUNS_LOCK:
        _ACTIVE_RUNS.add(run_id)


def mark_local_run_inactive(run_id: str) -> None:
    with _ACTIVE_RUNS_LOCK:
        _ACTIVE_RUNS.discard(run_id)


def is_local_run_active(run_id: str) -> bool:
    with _ACTIVE_RUNS_LOCK:
        return run_id in _ACTIVE_RUNS


def try_acquire_execution_lock(db: Session, run_id: str) -> bool | None:
    """Acquire a transaction lock in PostgreSQL; return None on SQLite."""

    if db.get_bind().dialect.name != "postgresql":
        return None
    lock_id = int.from_bytes(sha256(run_id.encode()).digest()[:8], "big", signed=True)
    return bool(
        db.execute(
            text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
            {"lock_id": lock_id},
        ).scalar_one()
    )
