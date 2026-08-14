from __future__ import annotations

import argparse
import json
import logging
import time

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.scheduling.service import dispatch_due_schedules


logger = logging.getLogger("defi_copilot.schedule_dispatcher")


def dispatch_once() -> dict[str, int | str]:
    with SessionLocal() as db:
        return dispatch_due_schedules(db).model_dump(mode="json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch due durable monitoring schedules.")
    parser.add_argument("--once", action="store_true", help="Dispatch one bounded batch and exit.")
    args = parser.parse_args()

    while True:
        result = dispatch_once()
        print(json.dumps(result, sort_keys=True), flush=True)
        if args.once:
            return 0
        time.sleep(get_settings().schedule_dispatch_poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
