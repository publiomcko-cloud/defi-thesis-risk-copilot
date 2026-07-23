from __future__ import annotations

import hashlib
import json
from typing import Protocol

from app.jobs.schemas import WorkerClaimedJob


class JobExecutor(Protocol):
    def execute(self, job: WorkerClaimedJob) -> dict: ...


class FakeDeterministicExecutor:
    """Lifecycle-only executor; it never performs analysis or provider side effects."""

    def execute(self, job: WorkerClaimedJob) -> dict:
        normalized = json.dumps(job.input_json, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return {
            "execution_mode": "fake_deterministic",
            "job_type": job.job_type,
            "input_fingerprint": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            "message": "Fake executor completed queue lifecycle validation.",
        }


EXECUTORS: dict[str, JobExecutor] = {"analysis.generate": FakeDeterministicExecutor()}


def get_executor(job_type: str) -> JobExecutor:
    executor = EXECUTORS.get(job_type)
    if executor is None:
        raise ValueError(f"No local executor is allowlisted for {job_type}.")
    return executor
