from __future__ import annotations

import json
import sys
from urllib.error import URLError
from urllib.request import urlopen


def main() -> int:
    base_url = "http://127.0.0.1:8000"
    url = f"{base_url}/health"

    try:
        with urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        print(f"Smoke check failed: could not reach {url}: {exc}", file=sys.stderr)
        return 1

    if payload.get("status") != "healthy":
        print(f"Smoke check failed: unexpected payload: {payload}", file=sys.stderr)
        return 1

    print("Smoke checks passed: /health is healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
