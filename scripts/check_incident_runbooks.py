"""Validate the versioned Phase 19G incident-response runbook registry.

The check intentionally validates only documentation structure and stable IDs.
Incident records and evidence stay in the approved private operations system.
"""

from __future__ import annotations

import argparse
from pathlib import Path


REQUIRED_RUNBOOKS = {
    "security.credential-exposure": "credential_exposure.md",
    "identity.account-takeover": "account_takeover.md",
    "tenant.exposure": "tenant_data_exposure.md",
    "knowledge.malicious-source": "malicious_source.md",
    "queue.duplication": "queue_duplication.md",
    "provider.cost": "runaway_provider_cost.md",
    "operations.database-storage": "database_or_storage_outage.md",
    "retrieval.vector-corruption": "vector_corruption.md",
    "deployment.failed-migration": "failed_migration.md",
    "workers.compromised": "compromised_worker.md",
}

REQUIRED_SECTIONS = (
    "## Detection",
    "## Immediate containment",
    "## Eradication and scope",
    "## Recovery and rollback",
    "## Communications",
    "## Evidence",
    "## Retrospective",
)


def validate_incident_runbooks(repository_root: Path) -> list[str]:
    """Return safe structural errors without reading any operational evidence."""
    incidents = repository_root / "docs" / "operations" / "incidents"
    errors: list[str] = []
    registry = incidents / "README.md"
    tabletop = incidents / "tabletop_exercises.md"
    for required in (registry, tabletop):
        if not required.is_file():
            errors.append(f"missing required incident document: {required.relative_to(repository_root)}")
    if registry.is_file():
        registry_text = registry.read_text(encoding="utf-8")
        for runbook_id, filename in REQUIRED_RUNBOOKS.items():
            if runbook_id not in registry_text or filename not in registry_text:
                errors.append(f"registry is missing {runbook_id} -> {filename}")
    if tabletop.is_file():
        tabletop_text = tabletop.read_text(encoding="utf-8")
        for scenario in range(1, len(REQUIRED_RUNBOOKS) + 1):
            scenario_id = f"TT-19G-{scenario:02d}"
            if scenario_id not in tabletop_text:
                errors.append(f"tabletop script is missing {scenario_id}")
    for runbook_id, filename in REQUIRED_RUNBOOKS.items():
        path = incidents / filename
        if not path.is_file():
            errors.append(f"missing runbook {runbook_id}: {filename}")
            continue
        text = path.read_text(encoding="utf-8")
        if runbook_id not in text:
            errors.append(f"runbook {filename} is missing stable ID {runbook_id}")
        if "Owner roles:" not in text or "Communication\nauthority:" not in text:
            errors.append(f"runbook {filename} is missing owner or communication authority")
        for section in REQUIRED_SECTIONS:
            if section not in text:
                errors.append(f"runbook {filename} is missing section {section}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 19G incident-runbook structure.")
    parser.add_argument("--repository-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = validate_incident_runbooks(args.repository_root.resolve())
    if errors:
        print("Incident runbook validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Incident runbook validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
