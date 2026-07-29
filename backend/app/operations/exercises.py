"""Fail-closed, fixed Phase 19H failure-exercise catalog.

The catalog is deliberately test-only: it accepts no caller-supplied command,
does not persist exercise data, and refuses production or real-provider modes.
The actual incident record remains in the approved private operations system.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence
import os
import subprocess
import tempfile
import time
from xml.etree import ElementTree

from app.core.config import Settings


@dataclass(frozen=True)
class ExerciseDefinition:
    id: str
    summary: str
    runbook_id: str
    working_directory: str
    command: tuple[str, ...]
    requires_postgres: bool = False
    max_duration_seconds: int = 180


@dataclass(frozen=True)
class ExerciseResult:
    id: str
    status: str
    duration_seconds: float
    timeout_seconds: int
    test_cases: int
    runbook_id: str


EXERCISES: tuple[ExerciseDefinition, ...] = (
    # Run integrity repair first against only the migration baseline. Later
    # worker/admission tests intentionally create broad durable-job fixtures.
    ExerciseDefinition(
        "pgvector-corruption-recovery",
        "Corrupt derived retrieval state is repaired or rolled back without tenant leakage.",
        "retrieval.vector-corruption",
        "backend",
        ("python", "-m", "pytest", "-q", "app/tests/test_phase18f_lifecycle.py", "app/tests/test_phase18g_public_corpus.py", "app/tests/test_phase18_final_retrieval.py"),
    ),
    ExerciseDefinition(
        "rate-limit-saturation",
        "Burst and bounded-compute saturation retain one-winner shared-limit behavior.",
        "queue.duplication",
        "backend",
        ("python", "-m", "pytest", "-q", "app/tests/test_phase19_rate_limits.py", "app/tests/test_phase19b_postgres_rate_limits.py"),
        requires_postgres=True,
    ),
    ExerciseDefinition(
        "queue-admission",
        "Admission limits and capacity reservations reject excess durable work safely.",
        "queue.duplication",
        "backend",
        ("python", "-m", "pytest", "-q", "app/tests/test_phase17b_postgres_control_plane.py"),
        requires_postgres=True,
    ),
    ExerciseDefinition(
        "worker-loss-recovery",
        "Lease expiry, stale mutation rejection, cancellation, and recovery remain controlled.",
        "workers.compromised",
        "backend",
        ("python", "-m", "pytest", "-q", "app/tests/test_phase17c_worker_protocol.py", "app/tests/test_phase17c_postgres_claims.py"),
        requires_postgres=True,
    ),
    ExerciseDefinition(
        "provider-timeout-failure",
        "Fake/dry-run provider failures retain conservative cost and cleanup behavior.",
        "provider.cost",
        "backend",
        ("python", "-m", "pytest", "-q", "app/tests/test_phase17e_vast_jobs.py", "app/tests/test_vast_provider.py"),
    ),
    ExerciseDefinition(
        "storage-outage",
        "Private storage and upload-scanner failures reject access before unsafe persistence.",
        "operations.database-storage",
        "backend",
        ("python", "-m", "pytest", "-q", "app/tests/test_phase18_storage_adapter.py", "app/tests/test_phase19c_security.py"),
    ),
    ExerciseDefinition(
        "migration-rollback",
        "Reversible migration rehearsals preserve seeded data and fail closed when required.",
        "deployment.failed-migration",
        "backend",
        ("python", "-m", "pytest", "-q", "app/tests/test_phase16_migration_hardening.py", "app/tests/test_phase17_migration.py", "app/tests/test_phase18_migration.py"),
    ),
    ExerciseDefinition(
        "authorization-negative",
        "Adversarial tenant and organization access attempts remain denied.",
        "tenant.exposure",
        "backend",
        ("python", "-m", "pytest", "-q", "app/tests/test_phase16_knowledge_scope.py", "app/tests/test_phase18_final_retrieval.py"),
    ),
    ExerciseDefinition(
        "database-recovery",
        "Isolated metadata-only restore verification detects recovery mismatches safely.",
        "operations.database-storage",
        "backend",
        ("python", "-m", "pytest", "-q", "app/tests/test_phase19e_recovery_operations.py"),
    ),
    ExerciseDefinition(
        "frontend-accessibility",
        "Core semantic and keyboard-visible browser contracts remain present.",
        "identity.account-takeover",
        "frontend",
        ("npm", "run", "test:accessibility"),
    ),
)


def catalog_payload() -> list[dict[str, object]]:
    """Return safe catalog metadata without exposing environment or commands."""
    return [
        {
            "id": exercise.id,
            "summary": exercise.summary,
            "runbook_id": exercise.runbook_id,
            "requires_postgres": exercise.requires_postgres,
        }
        for exercise in EXERCISES
    ]


def select_exercises(exercise_ids: Sequence[str] | None = None) -> tuple[ExerciseDefinition, ...]:
    requested = set(exercise_ids or ())
    known = {exercise.id for exercise in EXERCISES}
    unknown = sorted(requested - known)
    if unknown:
        raise ValueError(f"Unknown Phase 19 exercise IDs: {', '.join(unknown)}")
    return tuple(exercise for exercise in EXERCISES if not requested or exercise.id in requested)


def require_safe_exercise_environment(settings: Settings) -> None:
    """Refuse mutable, production, or real-provider exercise execution."""
    if not settings.operations_exercises_enabled:
        raise RuntimeError("Phase 19 exercises are disabled")
    if not settings.operations_exercises_isolated:
        raise RuntimeError("Phase 19 exercises require an isolated environment")
    if settings.app_env == "production":
        raise RuntimeError("Phase 19 exercises are blocked in production")
    if not settings.vast_dry_run or settings.vast_real_rentals_enabled:
        raise RuntimeError("Phase 19 exercises require Vast dry-run mode with real rentals disabled")


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def run_exercises(
    repository_root: Path,
    settings: Settings,
    *,
    exercise_ids: Sequence[str] | None = None,
    runner: CommandRunner = subprocess.run,
) -> list[ExerciseResult]:
    """Run only fixed synthetic test commands after fail-closed validation."""
    require_safe_exercise_environment(settings)
    results: list[ExerciseResult] = []
    environment = _exercise_environment()
    for exercise in select_exercises(exercise_ids):
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="phase19-exercise-") as temporary_directory:
            junit_path = Path(temporary_directory) / "results.xml"
            command = _command_with_safe_test_report(exercise.command, junit_path)
            timeout_seconds = min(settings.operations_exercise_timeout_seconds, exercise.max_duration_seconds)
            try:
                completed = runner(
                    command,
                    cwd=repository_root / exercise.working_directory,
                    env=environment,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(
                    f"Phase 19 exercise timed out: {exercise.id} after {timeout_seconds}s"
                ) from exc
            test_cases, failed_tests = _junit_metrics(junit_path)
        duration = round(time.monotonic() - started, 3)
        if duration > timeout_seconds:
            raise RuntimeError(f"Phase 19 exercise exceeded its time bound: {exercise.id}")
        if completed.returncode != 0:
            detail = f" (failed tests: {', '.join(failed_tests)})" if failed_tests else ""
            raise RuntimeError(f"Phase 19 exercise failed: {exercise.id}{detail}")
        results.append(
            ExerciseResult(
                id=exercise.id,
                status="passed",
                duration_seconds=duration,
                timeout_seconds=timeout_seconds,
                test_cases=test_cases,
                runbook_id=exercise.runbook_id,
            )
        )
    return results


def _exercise_environment() -> dict[str, str]:
    """Retain runtime tooling paths but force safe application/provider settings."""
    environment = os.environ.copy()
    environment.update(
        {
            "APP_ENV": "exercise",
            "VAST_DRY_RUN": "true",
            "VAST_REAL_RENTALS_ENABLED": "false",
            "VAST_ENABLED": "false",
            # The parent runner has already validated these gates. Individual
            # tests must remain free to construct production settings as a
            # negative case without inheriting a conflicting enabled flag.
            "OPERATIONS_EXERCISES_ENABLED": "false",
            "OPERATIONS_EXERCISES_ISOLATED": "false",
        }
    )
    return environment


def _command_with_safe_test_report(command: tuple[str, ...], junit_path: Path) -> tuple[str, ...]:
    """Ask pytest for identifiers only; never surface captured test output."""
    if command[:4] != ("python", "-m", "pytest", "-q"):
        return command
    return (*command, f"--junitxml={junit_path}")


def _junit_metrics(junit_path: Path) -> tuple[int, tuple[str, ...]]:
    """Return bounded test counts and non-sensitive failure identifiers."""
    if not junit_path.exists():
        return 0, ()
    try:
        root = ElementTree.parse(junit_path).getroot()
    except ElementTree.ParseError:
        return 0, ()

    failures: list[str] = []
    testcases = tuple(root.iter("testcase"))
    for testcase in testcases:
        if testcase.find("failure") is None and testcase.find("error") is None:
            continue
        classname = testcase.get("classname", "unknown")
        name = testcase.get("name", "unknown")
        failures.append(f"{classname}::{name}")
        if len(failures) == 3:
            break
    return len(testcases), tuple(failures)
