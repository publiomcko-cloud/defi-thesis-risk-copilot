"""Non-mutating Phase 19A operational readiness inspection.

The output contains no exporter URL, credential, object key, tenant data, or
source content. It does not call external telemetry providers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.observability import operational_readiness
from app.db.session import SessionLocal


def main() -> int:
    with SessionLocal() as db:
        result = operational_readiness(db)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
