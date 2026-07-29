"""Phase 19F repository policy checks remain independent from app runtime."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_SPEC = importlib.util.spec_from_file_location(
    "phase19f_supply_chain", REPO_ROOT / "scripts" / "supply_chain.py"
)
assert MODULE_SPEC and MODULE_SPEC.loader
supply_chain = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(supply_chain)


def test_repository_workflows_are_pinned_and_lockfiles_are_reproducible() -> None:
    assert supply_chain.check_workflow_policy(REPO_ROOT) == []
    assert supply_chain.check_lockfiles(REPO_ROOT) == []


def test_workflow_policy_rejects_mutable_actions_and_unsafe_trigger(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "unsafe.yml").write_text(
        "on:\n  pull_request_target:\njobs:\n  check:\n    steps:\n      - uses: actions/checkout@v4\n",
        encoding="utf-8",
    )

    errors = supply_chain.check_workflow_policy(tmp_path)

    assert any("pull_request_target" in error for error in errors)
    assert any("full commit SHA" in error for error in errors)
    assert any("persisted credentials" in error for error in errors)
    assert any("default permissions" in error for error in errors)


def test_workflow_policy_rejects_pull_request_secrets(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "unsafe-pr.yml").write_text(
        "on:\n  pull_request:\npermissions:\n  contents: read\njobs:\n"
        "  check:\n    env:\n      TOKEN: ${{ secrets.DEPLOYMENT_TOKEN }}\n",
        encoding="utf-8",
    )

    errors = supply_chain.check_workflow_policy(tmp_path)

    assert errors == [".github/workflows/unsafe-pr.yml: pull-request workflows must not reference secrets"]


def test_lockfile_policy_rejects_unpinned_python_requirement(tmp_path: Path) -> None:
    backend = tmp_path / "backend"
    frontend = tmp_path / "frontend"
    backend.mkdir()
    frontend.mkdir()
    (backend / "requirements.txt").write_text("fastapi>=0.1\n", encoding="utf-8")
    (frontend / "package-lock.json").write_text(
        json.dumps({"lockfileVersion": 3, "packages": {}}), encoding="utf-8"
    )

    errors = supply_chain.check_lockfiles(tmp_path)

    assert errors == ["unlocked Python requirement: fastapi>=0.1"]


def test_source_sbom_is_deterministic_and_contains_no_environment_values(tmp_path: Path) -> None:
    sbom = supply_chain.generate_sbom(REPO_ROOT)
    rendered = json.dumps(sbom, sort_keys=True)

    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.5"
    assert sbom["components"] == sorted(sbom["components"], key=lambda item: item["purl"])
    assert "DATABASE_URL" not in rendered
    assert "WORKER_CREDENTIAL" not in rendered
