from typing import Final


JOB_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "queued",
        "leased",
        "running",
        "retry_wait",
        "completed",
        "failed",
        "cancel_requested",
        "cancelled",
        "dead_letter",
    }
)
TERMINAL_JOB_STATUSES: Final[frozenset[str]] = frozenset(
    {"completed", "failed", "cancelled", "dead_letter"}
)
SUPPORTED_JOB_TYPES: Final[frozenset[str]] = frozenset(
    {"analysis.generate", "vast.session.start"}
)
JOB_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    "queued": frozenset({"leased", "cancel_requested", "failed"}),
    "leased": frozenset({"running", "retry_wait", "cancel_requested", "failed"}),
    "running": frozenset({"completed", "retry_wait", "failed", "cancel_requested"}),
    "retry_wait": frozenset({"leased", "cancel_requested", "dead_letter"}),
    "cancel_requested": frozenset({"cancelled"}),
    "completed": frozenset(),
    "failed": frozenset(),
    "cancelled": frozenset(),
    "dead_letter": frozenset(),
}
WORKER_STATUSES: Final[frozenset[str]] = frozenset({"active", "disabled", "stale", "revoked"})
WORKER_CREDENTIAL_STATUSES: Final[frozenset[str]] = frozenset({"active", "revoked", "expired"})
