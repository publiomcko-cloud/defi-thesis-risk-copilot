"""Run the fixed, fail-closed Phase 19H exercise catalog in isolation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import get_settings
from app.operations.exercises import catalog_payload, run_exercises, select_exercises


def main() -> int:
    parser = argparse.ArgumentParser(description="Run isolated Phase 19H failure exercises.")
    parser.add_argument("--list", action="store_true", help="Print the safe exercise catalog.")
    parser.add_argument("--exercise", action="append", default=[], help="Run one fixed catalog exercise by ID.")
    parser.add_argument("--run", action="store_true", help="Run selected fixed commands after safety checks.")
    parser.add_argument(
        "--evidence-file",
        type=Path,
        help="Write safe isolated-run metrics only after every selected exercise passes.",
    )
    args = parser.parse_args()

    if args.list:
        print(json.dumps({"exercises": catalog_payload()}, sort_keys=True))
        return 0
    if not args.run:
        selected = select_exercises(args.exercise)
        print(json.dumps({"dry_run": True, "exercise_ids": [item.id for item in selected]}, sort_keys=True))
        return 0
    try:
        results = run_exercises(
            Path(__file__).resolve().parents[2],
            get_settings(),
            exercise_ids=args.exercise,
        )
    except (RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "blocked", "detail": str(exc)}, sort_keys=True))
        return 2
    payload = {
        "schema_version": 2,
        "status": "passed",
        "execution_scope": "isolated-synthetic",
        "results": [result.__dict__ for result in results],
    }
    if args.evidence_file is not None:
        args.evidence_file.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
