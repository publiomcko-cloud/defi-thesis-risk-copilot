"""Execution ownership checks for inline research runs."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
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


class OwnerLockLost(RuntimeError):
    """The request can no longer prove that it owns its advisory fence."""


@dataclass
class ResearchOwnerFence:
    acquired: bool
    connection: Connection | None = None
    transaction: object | None = None
    _lost: bool = field(default=False, init=False)

    def __bool__(self) -> bool:
        return self.acquired

    def assert_alive(self) -> None:
        if not self.acquired or self._lost:
            raise OwnerLockLost("research ownership could not be verified")
        if self.connection is None:
            # SQLite uses only the process-local fallback lock.
            return
        if (
            self.connection.closed
            or self.connection.invalidated
            or self.transaction is None
            or not getattr(self.transaction, "is_active", False)
        ):
            self._lost = True
            raise OwnerLockLost("research ownership could not be verified")
        try:
            # This query runs on the same dedicated connection and open
            # transaction that owns pg_try_advisory_xact_lock.
            self.connection.execute(text("SELECT 1")).scalar_one()
        except Exception:
            self._lost = True
            raise OwnerLockLost("research ownership could not be verified") from None


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
def hold_research_owner_lock(db: Session, owner_user_id: str) -> Iterator[ResearchOwnerFence]:
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
            yield ResearchOwnerFence(acquired=acquired)
        finally:
            if acquired:
                local_lock.release()
        return

    independent_bind = bind.engine if isinstance(bind, Connection) else bind
    connection = independent_bind.connect()
    transaction = None
    acquired = False
    fence: ResearchOwnerFence | None = None
    try:
        transaction = connection.begin()
        acquired = bool(
            connection.execute(
                text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
                {"lock_id": _owner_lock_id(owner_user_id)},
            ).scalar_one()
        )
        fence = ResearchOwnerFence(acquired=acquired, connection=connection, transaction=transaction)
        yield fence
    finally:
        # Keep the transaction open for the complete guarded operation. Rollback
        # releases the xact lock on normal exit, exception, cancellation, or
        # connection cleanup after process failure.
        if transaction is not None and transaction.is_active:
            try:
                transaction.rollback()
            except Exception:
                # A terminated PostgreSQL backend already released the
                # transaction advisory lock. Cleanup must not mask the
                # fail-closed request outcome with a driver exception.
                if fence is not None:
                    fence._lost = True
        try:
            connection.close()
        except Exception:
            if fence is not None:
                fence._lost = True


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
