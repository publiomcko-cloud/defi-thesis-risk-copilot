"""Execution ownership checks for inline research runs."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from hashlib import sha256
from collections.abc import Iterator

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session


_ACTIVE_RUNS: set[str] = set()
_ACTIVE_RUNS_LOCK = threading.Lock()
_OWNER_LOCKS: dict[str, threading.Lock] = {}
_OWNER_LOCKS_LOCK = threading.Lock()


def mark_local_run_active(run_id: str) -> None:
    with _ACTIVE_RUNS_LOCK:
        _ACTIVE_RUNS.add(run_id)


def mark_local_run_inactive(run_id: str) -> None:
    with _ACTIVE_RUNS_LOCK:
        _ACTIVE_RUNS.discard(run_id)


def is_local_run_active(run_id: str) -> bool:
    with _ACTIVE_RUNS_LOCK:
        return run_id in _ACTIVE_RUNS


def _owner_lock_id(owner_user_id: str) -> int:
    return int.from_bytes(
        sha256(f"phase22-research-owner:{owner_user_id}".encode()).digest()[:8],
        "big",
        signed=True,
    )


def _local_owner_lock(owner_user_id: str) -> threading.Lock:
    with _OWNER_LOCKS_LOCK:
        return _OWNER_LOCKS.setdefault(owner_user_id, threading.Lock())


@contextmanager
def hold_research_owner_lock(db: Session, owner_user_id: str) -> Iterator[bool]:
    """Hold one owner's PostgreSQL transaction lock across request commits.

    The lock lives on a dedicated, pinned SQLAlchemy connection and its
    transaction is deliberately never committed. Request data can commit on
    ``db`` while this independent transaction continues to own the lock. A
    transaction pooler keeps the backend pinned for that open transaction;
    process/connection loss rolls it back and releases the lock. No session
    advisory lock can leak into a later pool borrower.

    SQLite has no cross-process advisory lock, so its fallback is process-local
    and only supports the existing single-process development/test profile.
    """

    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        local_lock = _local_owner_lock(owner_user_id)
        acquired = local_lock.acquire(blocking=False)
        try:
            yield acquired
        finally:
            if acquired:
                local_lock.release()
        return

    independent_bind = bind.engine if isinstance(bind, Connection) else bind
    connection = independent_bind.connect()
    transaction = None
    acquired = False
    try:
        transaction = connection.begin()
        acquired = bool(
            connection.execute(
                text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
                {"lock_id": _owner_lock_id(owner_user_id)},
            ).scalar_one()
        )
        yield acquired
    finally:
        # Keep the transaction open for the complete guarded operation. Rollback
        # releases the xact lock on normal exit, exception, cancellation, or
        # connection cleanup after process failure.
        if transaction is not None and transaction.is_active:
            transaction.rollback()
        connection.close()


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


def try_acquire_research_owner_lock(db: Session, owner_user_id: str) -> bool:
    """Try the same owner fence while reconciling a persisted run.

    The caller's transaction retains this lock through its reconciliation
    commit. An active request's dedicated transaction holds the conflicting
    lock, so readers leave its running reservation untouched.
    """

    if db.get_bind().dialect.name != "postgresql":
        return False
    try:
        return bool(
            db.execute(
                text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
                {"lock_id": _owner_lock_id(owner_user_id)},
            ).scalar_one()
        )
    except OperationalError:
        db.rollback()
        raise
