"""Structural tests for Phase 19G's safe, versioned incident procedures."""

from __future__ import annotations

import importlib.util
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MODULE_SPEC = importlib.util.spec_from_file_location(
    "phase19g_incident_runbooks", REPOSITORY_ROOT / "scripts" / "check_incident_runbooks.py"
)
assert MODULE_SPEC and MODULE_SPEC.loader
incident_runbooks = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(incident_runbooks)


def test_required_incident_runbooks_are_complete_and_registered() -> None:
    assert incident_runbooks.validate_incident_runbooks(REPOSITORY_ROOT) == []


def test_runbook_validator_reports_missing_response_sections(tmp_path: Path) -> None:
    incidents = tmp_path / "docs" / "operations" / "incidents"
    incidents.mkdir(parents=True)
    (incidents / "README.md").write_text("", encoding="utf-8")
    (incidents / "tabletop_exercises.md").write_text("", encoding="utf-8")

    errors = incident_runbooks.validate_incident_runbooks(tmp_path)

    assert any("missing runbook" in error for error in errors)
    assert any("registry is missing" in error for error in errors)
    assert any("tabletop script is missing TT-19G-01" in error for error in errors)
