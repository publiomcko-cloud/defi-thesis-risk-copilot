from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.knowledge.lifecycle_service import cleanup_tombstoned_knowledge


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Retry bounded physical cleanup for tombstoned knowledge versions."
    )
    parser.add_argument("--dry-run", action="store_true", help="Report eligible cleanup tasks only.")
    parser.add_argument("--limit", type=int, default=100, help="Maximum tasks to inspect or process.")
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 1_000:
        parser.error("--limit must be between 1 and 1000")
    with SessionLocal() as db:
        counts = cleanup_tombstoned_knowledge(db, dry_run=args.dry_run, limit=args.limit)
        if args.dry_run:
            db.rollback()
        else:
            db.commit()
    print(json.dumps({"dry_run": args.dry_run, **counts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
