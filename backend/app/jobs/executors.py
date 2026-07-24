from __future__ import annotations

from typing import Protocol

from app.jobs.analysis_executor import AnalysisJobExecutor
from app.jobs.schemas import JobResultEnvelope, WorkerClaimedJob


class JobExecutor(Protocol):
    def execute(self, job: WorkerClaimedJob) -> JobResultEnvelope: ...


EXECUTORS: dict[str, JobExecutor] = {"analysis.generate": AnalysisJobExecutor()}


def get_executor(job_type: str) -> JobExecutor:
    executor = EXECUTORS.get(job_type)
    if executor is None:
        raise ValueError(f"No local executor is allowlisted for {job_type}.")
    return executor
