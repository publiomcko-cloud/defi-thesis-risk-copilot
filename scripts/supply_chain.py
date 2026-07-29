#!/usr/bin/env python3
"""Offline Phase 19F checks for workflow policy, lockfiles, and source SBOMs.

The script intentionally uses only the standard library so CI can validate its
own workflow policy before installing project dependencies. It never reads
environment variables or writes secret-bearing data.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote


SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
USES_PATTERN = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.MULTILINE)
PINNED_REQUIREMENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*(?:\[[^]]+\])?==[^\s;]+$")


def workflow_files(repo_root: Path) -> list[Path]:
    return sorted((repo_root / ".github" / "workflows").glob("*.y*ml"))


def check_workflow_policy(repo_root: Path) -> list[str]:
    """Return policy violations without interpreting untrusted workflow YAML."""

    errors: list[str] = []
    for workflow in workflow_files(repo_root):
        content = workflow.read_text(encoding="utf-8")
        relative = workflow.relative_to(repo_root)
        if not re.search(r"^\s*permissions\s*:", content, re.MULTILINE):
            errors.append(f"{relative}: workflow must declare default permissions")
        if re.search(r"^\s*pull_request_target\s*:", content, re.MULTILINE):
            errors.append(f"{relative}: pull_request_target is not permitted")
        if re.search(r"^\s*pull_request\s*:", content, re.MULTILINE) and re.search(
            r"\bsecrets\.", content
        ):
            errors.append(f"{relative}: pull-request workflows must not reference secrets")
        if re.search(r"permissions:\s*write-all\b", content):
            errors.append(f"{relative}: write-all permissions are not permitted")
        for action in USES_PATTERN.findall(content):
            if action.startswith(("./", "docker://")):
                continue
            if "@" not in action:
                errors.append(f"{relative}: action {action!r} has no immutable revision")
                continue
            reference = action.rsplit("@", 1)[1]
            if not SHA_PATTERN.fullmatch(reference):
                errors.append(f"{relative}: action {action!r} is not pinned to a full commit SHA")
        if "actions/checkout@" in content and "persist-credentials: false" not in content:
            errors.append(f"{relative}: checkout must disable persisted credentials")
    return errors


def parse_python_requirements(requirements_path: Path) -> list[tuple[str, str]]:
    components: list[tuple[str, str]] = []
    for raw in requirements_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not PINNED_REQUIREMENT_PATTERN.fullmatch(line):
            raise ValueError(f"unlocked Python requirement: {line}")
        name, version = line.split("==", 1)
        components.append((name.split("[", 1)[0].lower(), version))
    return sorted(components)


def parse_node_packages(lockfile_path: Path) -> list[tuple[str, str]]:
    lock = json.loads(lockfile_path.read_text(encoding="utf-8"))
    if lock.get("lockfileVersion") != 3:
        raise ValueError("frontend/package-lock.json must use lockfileVersion 3")
    packages = lock.get("packages")
    if not isinstance(packages, dict):
        raise ValueError("frontend/package-lock.json has no packages map")

    components: list[tuple[str, str]] = []
    for package_path, package in packages.items():
        if not package_path.startswith("node_modules/"):
            continue
        if not isinstance(package, dict):
            raise ValueError(f"invalid lockfile package entry: {package_path}")
        name = package_path.removeprefix("node_modules/")
        version = package.get("version")
        resolved = package.get("resolved")
        integrity = package.get("integrity")
        if not isinstance(version, str):
            raise ValueError(f"node package has no version: {name}")
        if resolved and not str(resolved).startswith("https://registry.npmjs.org/"):
            raise ValueError(f"node package has unsupported source: {name}")
        if resolved and not integrity:
            raise ValueError(f"node package has no integrity digest: {name}")
        components.append((name, version))
    return sorted(components)


def check_lockfiles(repo_root: Path) -> list[str]:
    errors: list[str] = []
    try:
        parse_python_requirements(repo_root / "backend" / "requirements.txt")
    except (OSError, ValueError) as error:
        errors.append(str(error))
    try:
        parse_node_packages(repo_root / "frontend" / "package-lock.json")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        errors.append(str(error))
    return errors


def component(name: str, version: str, ecosystem: str) -> dict[str, str]:
    purl_type = "pypi" if ecosystem == "python" else "npm"
    return {
        "type": "library",
        "name": name,
        "version": version,
        "purl": f"pkg:{purl_type}/{quote(name, safe='@/') }@{quote(version, safe='.+-_')}",
    }


def generate_sbom(repo_root: Path) -> dict[str, Any]:
    python_components = [component(name, version, "python") for name, version in parse_python_requirements(repo_root / "backend" / "requirements.txt")]
    node_components = [component(name, version, "node") for name, version in parse_node_packages(repo_root / "frontend" / "package-lock.json")]
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": "urn:uuid:phase19f-source-lockfile-sbom",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "defi-thesis-risk-copilot",
                "version": "source-lockfiles",
            },
            "properties": [
                {"name": "de.fi.supply-chain.scope", "value": "pinned Python requirements and npm lockfile"},
                {"name": "de.fi.supply-chain.content", "value": "no environment values, credentials, or build-time secrets"},
            ],
        },
        "components": sorted(python_components + node_components, key=lambda item: item["purl"]),
    }


def audit_summary(audit_path: Path) -> dict[str, int]:
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    metadata = payload.get("metadata", {})
    vulnerabilities = metadata.get("vulnerabilities", {}) if isinstance(metadata, dict) else {}
    return {severity: int(vulnerabilities.get(severity, 0)) for severity in ("critical", "high", "moderate", "low", "info")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check-workflows", "check-lockfiles", "generate-sbom", "audit-summary"))
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--audit-file", type=Path)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()

    if args.command == "check-workflows":
        errors = check_workflow_policy(repo_root)
        if errors:
            print("Workflow policy failed:", *errors, sep="\n", file=sys.stderr)
            return 1
        print("Workflow policy passed.")
        return 0
    if args.command == "check-lockfiles":
        errors = check_lockfiles(repo_root)
        if errors:
            print("Lockfile policy failed:", *errors, sep="\n", file=sys.stderr)
            return 1
        print("Lockfile policy passed.")
        return 0
    if args.command == "generate-sbom":
        if args.output is None:
            parser.error("generate-sbom requires --output")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(generate_sbom(repo_root), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"SBOM generated with {len(generate_sbom(repo_root)['components'])} components.")
        return 0
    if args.audit_file is None:
        parser.error("audit-summary requires --audit-file")
    print(json.dumps(audit_summary(args.audit_file), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
