from __future__ import annotations

from typing import Protocol

from app.jobs.schemas import JobResultEnvelope, WorkerClaimedJob
from app.jobs.registry import executor_for_job_type


class JobExecutor(Protocol):
    def execute(self, job: WorkerClaimedJob) -> JobResultEnvelope: ...


def get_executor(job_type: str) -> JobExecutor:
    return executor_for_job_type(job_type)
