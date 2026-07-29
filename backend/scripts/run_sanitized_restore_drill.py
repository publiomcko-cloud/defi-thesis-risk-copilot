"""Create or verify a safe metadata manifest for an isolated restore drill.

This command is disabled by default and refuses production execution. It does
not create a database/object backup and must not be used to copy production data
into local development. Use the Phase 19E runbook for provider backup/restore.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.operations.backup_restore import (
    SanitizedRestoreManifest,
    create_sanitized_restore_manifest,
    verify_sanitized_restore_manifest,
)


_MAX_MANIFEST_BYTES = 1_000_000


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write-manifest", type=Path)
    group.add_argument("--verify-manifest", type=Path)
    args = parser.parse_args()
    settings = get_settings()
    if not settings.backup_restore_drill_enabled:
        print(json.dumps({"status": "disabled", "detail": "Restore drills are disabled by configuration."}))
        return 2
    if settings.app_env == "production":
        print(json.dumps({"status": "blocked", "detail": "Run restore drills only against an isolated target."}))
        return 2
    try:
        if args.write_manifest:
            return _write_manifest(args.write_manifest)
        return _verify_manifest(args.verify_manifest)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "invalid", "detail": str(exc)}))
        return 2


def _write_manifest(path: Path) -> int:
    _validate_manifest_path(path)
    if path.exists():
        raise ValueError("Refusing to overwrite an existing manifest")
    with SessionLocal() as db:
        manifest = create_sanitized_restore_manifest(db)
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    print(json.dumps({"status": "created", "resource_counts": manifest.resource_counts}, sort_keys=True))
    return 0


def _verify_manifest(path: Path) -> int:
    _validate_manifest_path(path)
    if not path.exists():
        raise ValueError("Manifest file does not exist")
    if path.stat().st_size > _MAX_MANIFEST_BYTES:
        raise ValueError("Manifest exceeds the maximum supported size")
    manifest = SanitizedRestoreManifest.model_validate_json(path.read_text(encoding="utf-8"))
    with SessionLocal() as db:
        result = verify_sanitized_restore_manifest(manifest, db)
    print(json.dumps(result.model_dump(mode="json"), sort_keys=True))
    return 0 if result.passed else 1


def _validate_manifest_path(path: Path) -> None:
    if path.suffix != ".json":
        raise ValueError("Manifest path must use a .json extension")
    if path.exists() and not path.is_file():
        raise ValueError("Manifest path must be a file")
    if not path.parent.exists():
        raise ValueError("Manifest parent directory does not exist")


if __name__ == "__main__":
    raise SystemExit(main())
