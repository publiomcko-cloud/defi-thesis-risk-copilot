from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


NotificationCategory = Literal["monitoring.risk_alert", "schedule.status", "job.status", "account.lifecycle"]
NotificationSeverity = Literal["informational", "warning", "critical"]

CATEGORIES: tuple[NotificationCategory, ...] = (
    "monitoring.risk_alert",
    "schedule.status",
    "job.status",
    "account.lifecycle",
)
SEVERITIES: tuple[NotificationSeverity, ...] = ("informational", "warning", "critical")
SEVERITY_RANK = {"informational": 0, "warning": 1, "critical": 2}
SUPPRESSIBLE_CATEGORIES = {"monitoring.risk_alert", "schedule.status", "job.status"}
MANDATORY_CATEGORIES = {"account.lifecycle"}


@dataclass(frozen=True)
class NotificationTemplate:
    template_id: str
    category: NotificationCategory
    severity: NotificationSeverity
    title: str
    body: str
    source_type: str
    path: str


TEMPLATES: dict[str, NotificationTemplate] = {
    "monitoring.risk_alert.opened": NotificationTemplate(
        template_id="monitoring.risk_alert.opened",
        category="monitoring.risk_alert",
        severity="warning",
        title="Watchlist risk alert",
        body="A monitored watchlist rule opened a risk alert.",
        source_type="alert_event",
        path="/watchlist",
    ),
    "monitoring.risk_alert.critical": NotificationTemplate(
        template_id="monitoring.risk_alert.critical",
        category="monitoring.risk_alert",
        severity="critical",
        title="Critical watchlist risk alert",
        body="A monitored watchlist rule opened a critical risk alert.",
        source_type="alert_event",
        path="/watchlist",
    ),
    "schedule.status.queued": NotificationTemplate(
        template_id="schedule.status.queued",
        category="schedule.status",
        severity="informational",
        title="Scheduled monitoring queued",
        body="A scheduled watchlist evaluation was queued.",
        source_type="monitoring_schedule_occurrence",
        path="/schedules",
    ),
    "schedule.status.missed": NotificationTemplate(
        template_id="schedule.status.missed",
        category="schedule.status",
        severity="warning",
        title="Scheduled monitoring skipped",
        body="A scheduled evaluation was skipped after becoming too overdue.",
        source_type="monitoring_schedule_occurrence",
        path="/schedules",
    ),
    "schedule.status.denied": NotificationTemplate(
        template_id="schedule.status.denied",
        category="schedule.status",
        severity="warning",
        title="Scheduled monitoring not run",
        body="A scheduled evaluation could not run after server-side revalidation.",
        source_type="monitoring_schedule_occurrence",
        path="/schedules",
    ),
    "schedule.status.completed": NotificationTemplate(
        template_id="schedule.status.completed",
        category="schedule.status",
        severity="informational",
        title="Scheduled monitoring completed",
        body="A scheduled watchlist evaluation completed.",
        source_type="monitoring_schedule_occurrence",
        path="/schedules",
    ),
    "schedule.status.failed": NotificationTemplate(
        template_id="schedule.status.failed",
        category="schedule.status",
        severity="warning",
        title="Scheduled monitoring failed",
        body="A scheduled watchlist evaluation failed.",
        source_type="monitoring_schedule_occurrence",
        path="/schedules",
    ),
    "job.status.completed": NotificationTemplate(
        template_id="job.status.completed",
        category="job.status",
        severity="informational",
        title="Job completed",
        body="A durable job completed.",
        source_type="job",
        path="/jobs",
    ),
    "job.status.failed": NotificationTemplate(
        template_id="job.status.failed",
        category="job.status",
        severity="warning",
        title="Job failed",
        body="A durable job failed before completion.",
        source_type="job",
        path="/jobs",
    ),
    "job.status.cancelled": NotificationTemplate(
        template_id="job.status.cancelled",
        category="job.status",
        severity="informational",
        title="Job cancelled",
        body="A durable job was cancelled.",
        source_type="job",
        path="/jobs",
    ),
    "job.status.dead_letter": NotificationTemplate(
        template_id="job.status.dead_letter",
        category="job.status",
        severity="warning",
        title="Job needs review",
        body="A durable job reached its final attempt.",
        source_type="job",
        path="/jobs",
    ),
    "account.lifecycle.exported": NotificationTemplate(
        template_id="account.lifecycle.exported",
        category="account.lifecycle",
        severity="informational",
        title="Account export created",
        body="Your account export was generated.",
        source_type="account",
        path="/account",
    ),
    "account.lifecycle.deletion_requested": NotificationTemplate(
        template_id="account.lifecycle.deletion_requested",
        category="account.lifecycle",
        severity="critical",
        title="Account deletion requested",
        body="Your application account deletion lifecycle started.",
        source_type="account",
        path="/account",
    ),
    "account.lifecycle.mfa_changed": NotificationTemplate(
        template_id="account.lifecycle.mfa_changed",
        category="account.lifecycle",
        severity="warning",
        title="Account security changed",
        body="A multi-factor authentication setting changed.",
        source_type="mfa_factor",
        path="/account/security",
    ),
}


def template_for(template_id: str) -> NotificationTemplate:
    return TEMPLATES[template_id]
