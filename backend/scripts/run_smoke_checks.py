from __future__ import annotations

import json
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen

REQUEST_TIMEOUT_SECONDS = 20


def main() -> int:
    base_url = "http://127.0.0.1:8000"

    try:
        health = _get_json(f"{base_url}/health")
        if health.get("status") != "healthy":
            print(f"Smoke check failed: unexpected /health payload: {health}", file=sys.stderr)
            return 1

        protocols = _get_json(f"{base_url}/api/protocols")
        protocol_ids = {item["id"] for item in protocols.get("protocols", [])}
        expected_protocols = {"pendle", "morpho", "aave"}
        if not expected_protocols.issubset(protocol_ids):
            print(
                f"Smoke check failed: protocols missing {expected_protocols - protocol_ids}",
                file=sys.stderr,
            )
            return 1

        analysis = _post_json(
            f"{base_url}/api/analyze",
            {
                "strategy_description": "Analyze a Pendle PT strategy using Morpho borrow.",
                "protocols": ["pendle", "morpho"],
                "manual_inputs": {},
                "analysis_depth": "standard",
            },
        )
        report_id = analysis.get("report_id")
        if not report_id:
            print(f"Smoke check failed: missing report_id: {analysis}", file=sys.stderr)
            return 1

        report = _get_json(f"{base_url}/api/reports/{report_id}")
        if report.get("report_id") != report_id:
            print(f"Smoke check failed: report retrieval mismatch: {report}", file=sys.stderr)
            return 1

        export = _post_json(f"{base_url}/api/reports/{report_id}/export", {})
        markdown = export.get("markdown", "")
        if export.get("report_id") != report_id or "# Strategy Risk Report" not in markdown:
            print(f"Smoke check failed: markdown export mismatch: {export}", file=sys.stderr)
            return 1
    except URLError as exc:
        print(f"Smoke check failed: API request failed: {exc}", file=sys.stderr)
        return 1

    print(
        "Smoke checks passed: /health, /api/protocols, /api/analyze, "
        "report retrieval, and markdown export"
    )
    return 0


def _get_json(url: str) -> dict:
    with urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
