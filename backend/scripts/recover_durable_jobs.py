from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.jobs.worker_protocol import recover_durable_jobs


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover expired and unauthorized durable jobs safely.")
    parser.add_argument("--dry-run", action="store_true", help="Calculate recovery changes then roll them back.")
    args = parser.parse_args()
    with SessionLocal() as db:
        counts = recover_durable_jobs(db, dry_run=args.dry_run)
    print(json.dumps({"dry_run": args.dry_run, **counts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
