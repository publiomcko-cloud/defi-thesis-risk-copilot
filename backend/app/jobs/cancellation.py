from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Event

from app.jobs.errors import JobErrorCategory, JobExecutionError


@dataclass
class CancellationContext:
    """Cooperative, worker-owned cancellation state for one claimed attempt."""

    deadline_at: datetime | None = None
    _event: Event = field(default_factory=Event)
    _reason: str | None = None

    def cancel(self, reason: str) -> None:
        if not self._event.is_set():
            self._reason = reason
            self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set() or self.deadline_exceeded

    @property
    def deadline_exceeded(self) -> bool:
        return self.deadline_at is not None and datetime.now(UTC) >= self.deadline_at

    @property
    def reason(self) -> str:
        if self.deadline_exceeded and not self._event.is_set():
            return "execution_deadline"
        return self._reason or "cancelled"

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            code = "execution_deadline" if self.deadline_exceeded else "job_cancelled"
            raise JobExecutionError(JobErrorCategory.CANCELLATION, code, "Controlled job execution was cancelled.")
