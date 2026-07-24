from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.auth.security import redact_sensitive


class JobErrorCategory(StrEnum):
    PERMANENT_INPUT = "permanent_input"
    PERMANENT_AUTHORIZATION = "permanent_authorization"
    RETRYABLE_INFRASTRUCTURE = "retryable_infrastructure"
    RETRYABLE_PROVIDER = "retryable_provider"
    UNCERTAIN_EXTERNAL_SIDE_EFFECT = "uncertain_external_side_effect"
    CANCELLATION = "cancellation"
    LEASE_LOSS = "lease_ownership_loss"


@dataclass
class JobExecutionError(RuntimeError):
    category: JobErrorCategory
    code: str
    summary: str

    @property
    def retryable(self) -> bool:
        return self.category in {
            JobErrorCategory.RETRYABLE_INFRASTRUCTURE,
            JobErrorCategory.RETRYABLE_PROVIDER,
        }

    @property
    def safe_summary(self) -> str:
        return str(redact_sensitive(self.summary))[:512]


def classify_exception(exc: Exception) -> JobExecutionError:
    if isinstance(exc, JobExecutionError):
        return exc
    return JobExecutionError(
        JobErrorCategory.RETRYABLE_INFRASTRUCTURE,
        "worker_infrastructure_error",
        "The controlled worker encountered a transient infrastructure error.",
    )
