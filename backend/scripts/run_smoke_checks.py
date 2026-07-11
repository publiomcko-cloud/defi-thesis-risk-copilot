from __future__ import annotations

import json
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen

REQUEST_TIMEOUT_SECONDS = 240


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

        monitoring = _post_json(f"{base_url}/api/monitoring/run", {})
        if monitoring.get("status") not in {"completed", "partial"}:
            print(f"Smoke check failed: monitoring mismatch: {monitoring}", file=sys.stderr)
            return 1

        discovered = _get_json(f"{base_url}/api/monitoring/discovered-items")
        discovered_items = discovered.get("items", [])
        if not discovered_items:
            print("Smoke check failed: no discovered items returned", file=sys.stderr)
            return 1

        discovered_item_id = discovered_items[0]["id"]
        evaluation = _post_json(
            f"{base_url}/api/evaluation/discovered-items/{discovered_item_id}/evaluate",
            {},
        )
        evaluation_report_id = (
            evaluation.get("evaluation_result", {}).get("report_id")
        )
        review_item_id = evaluation.get("review_item", {}).get("id")
        if not evaluation_report_id or not review_item_id:
            print(f"Smoke check failed: evaluation mismatch: {evaluation}", file=sys.stderr)
            return 1

        evaluation_report = _get_json(f"{base_url}/api/reports/{evaluation_report_id}")
        if evaluation_report.get("report_id") != evaluation_report_id:
            print(
                f"Smoke check failed: evaluation report retrieval mismatch: {evaluation_report}",
                file=sys.stderr,
            )
            return 1

        review_items = _get_json(f"{base_url}/api/evaluation/review-items")
        if not review_items.get("items"):
            print(f"Smoke check failed: review queue empty: {review_items}", file=sys.stderr)
            return 1

        updated_review = _patch_json(
            f"{base_url}/api/evaluation/review-items/{review_item_id}",
            {
                "status": "needs_more_data",
                "reviewer_notes": "Smoke check marked this item for more research.",
            },
        )
        if updated_review.get("review_item", {}).get("status") != "needs_more_data":
            print(
                f"Smoke check failed: review status update mismatch: {updated_review}",
                file=sys.stderr,
            )
            return 1
    except URLError as exc:
        print(f"Smoke check failed: API request failed: {exc}", file=sys.stderr)
        return 1

    print(
        "Smoke checks passed: /health, /api/protocols, /api/analyze, "
        "report retrieval, markdown export, monitoring, evaluation, review queue, "
        "and evaluation report retrieval"
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


def _patch_json(url: str, payload: dict) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="PATCH",
    )
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
