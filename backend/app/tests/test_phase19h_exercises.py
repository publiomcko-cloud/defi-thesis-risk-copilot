from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.operations.exercises import EXERCISES, run_exercises, select_exercises


def _settings(**overrides):
    values = {
        "operations_exercises_enabled": True,
        "operations_exercises_isolated": True,
        "operations_exercise_timeout_seconds": 30,
        "app_env": "exercise",
        "vast_dry_run": True,
        "vast_real_rentals_enabled": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_phase19h_catalog_covers_each_contract_exercise_and_uses_fixed_commands() -> None:
    exercise_ids = {exercise.id for exercise in EXERCISES}

    assert exercise_ids == {
        "rate-limit-saturation",
        "queue-admission",
        "worker-loss-recovery",
        "provider-timeout-failure",
        "storage-outage",
        "pgvector-corruption-recovery",
        "migration-rollback",
        "authorization-negative",
        "database-recovery",
        "frontend-accessibility",
    }
    assert all(exercise.command[0] in {"python", "npm"} for exercise in EXERCISES)
    assert all("VAST" not in " ".join(exercise.command) for exercise in EXERCISES)


def test_phase19h_runner_forces_safe_environment_and_never_accepts_custom_commands(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def successful_runner(*args, **kwargs):
        captured.update(kwargs)
        captured["command"] = args[0]
        return SimpleNamespace(returncode=0)

    results = run_exercises(
        tmp_path,
        _settings(),
        exercise_ids=["frontend-accessibility"],
        runner=successful_runner,
    )

    assert results[0].status == "passed"
    assert captured["command"] == ("npm", "run", "test:accessibility")
    environment = captured["env"]
    assert environment["APP_ENV"] == "exercise"
    assert environment["VAST_DRY_RUN"] == "true"
    assert environment["VAST_REAL_RENTALS_ENABLED"] == "false"
    assert environment["OPERATIONS_EXERCISES_ENABLED"] == "false"
    assert environment["OPERATIONS_EXERCISES_ISOLATED"] == "false"
    with pytest.raises(ValueError, match="Unknown Phase 19 exercise"):
        select_exercises(["pytest arbitrary-command"])


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"operations_exercises_enabled": False}, "disabled"),
        ({"operations_exercises_isolated": False}, "isolated"),
        ({"app_env": "production"}, "production"),
        ({"vast_dry_run": False}, "dry-run"),
        ({"vast_real_rentals_enabled": True}, "real rentals"),
    ],
)
def test_phase19h_runner_fails_closed_for_unsafe_environment(tmp_path: Path, overrides: dict, message: str) -> None:
    with pytest.raises(RuntimeError, match=message):
        run_exercises(tmp_path, _settings(**overrides), exercise_ids=["database-recovery"])


def test_phase19h_runner_surfaces_failed_fixed_exercise_without_test_output(tmp_path: Path) -> None:
    def failed_runner(*_args, **_kwargs):
        return SimpleNamespace(returncode=1, stdout="sensitive test output", stderr="sensitive stderr")

    with pytest.raises(RuntimeError, match="database-recovery"):
        run_exercises(tmp_path, _settings(), exercise_ids=["database-recovery"], runner=failed_runner)


def test_phase19h_runner_reports_only_failed_junit_identifiers(tmp_path: Path) -> None:
    def failed_runner(command, *_args, **_kwargs):
        junit_argument = next(argument for argument in command if argument.startswith("--junitxml="))
        junit_path = Path(junit_argument.removeprefix("--junitxml="))
        junit_path.write_text(
            "<testsuite><testcase classname=\"app.tests.safe\" name=\"failure_case\">"
            "<failure>secret captured output</failure></testcase></testsuite>",
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=1, stdout="sensitive test output", stderr="sensitive stderr")

    with pytest.raises(RuntimeError, match=r"app\.tests\.safe::failure_case") as error:
        run_exercises(tmp_path, _settings(), exercise_ids=["database-recovery"], runner=failed_runner)

    assert "secret captured output" not in str(error.value)
    assert "sensitive" not in str(error.value)


def test_phase19h_settings_require_isolation_and_reject_production_or_real_vast() -> None:
    with pytest.raises(ValidationError, match="ISOLATED"):
        Settings(operations_exercises_enabled=True)
    with pytest.raises(ValidationError, match="production"):
        Settings(
            app_env="production",
            operations_exercises_enabled=True,
            operations_exercises_isolated=True,
        )
    with pytest.raises(ValidationError, match="TIMEOUT"):
        Settings(operations_exercise_timeout_seconds=601)
