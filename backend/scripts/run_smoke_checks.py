from __future__ import annotations

import json
import os
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen

REQUEST_TIMEOUT_SECONDS = 240


def main() -> int:
    base_url = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

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

        demo_status = _get_json(f"{base_url}/api/demo/status")
        demo_scenarios = _get_json(f"{base_url}/api/demo/scenarios")
        if not isinstance(demo_scenarios, list) or len(demo_scenarios) < 4:
            print(f"Smoke check failed: demo scenarios mismatch: {demo_scenarios}", file=sys.stderr)
            return 1

        demo_seed = _post_json(f"{base_url}/api/demo/seed", {})
        if not demo_seed.get("seeded") or demo_seed.get("counts", {}).get("reports", 0) < 5:
            print(f"Smoke check failed: demo seed mismatch: {demo_seed}", file=sys.stderr)
            return 1

        demo_report = _get_json(f"{base_url}/api/reports/demo_report_pendle_pt_loop")
        if demo_report.get("report_id") != "demo_report_pendle_pt_loop":
            print(f"Smoke check failed: demo report retrieval mismatch: {demo_report}", file=sys.stderr)
            return 1

        deployment_status = _get_json(f"{base_url}/api/deployment/status")
        if not deployment_status.get("database_connected"):
            print(f"Smoke check failed: deployment status mismatch: {deployment_status}", file=sys.stderr)
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

        simulation = _post_json(
            f"{base_url}/api/simulation/run",
            {
                "strategy_description": "Pendle PT strategy using Morpho borrow",
                "protocols": ["pendle", "morpho"],
                "implied_apy": 0.12,
                "borrow_apy": 0.05,
                "incentive_apy": 0.01,
                "ltv": 0.5,
                "lltv": 0.86,
                "liquidity_usd": 1000000,
                "pt_price": 0.95,
            },
        )
        if simulation.get("status") != "completed" or len(simulation.get("scenarios", [])) < 7:
            print(f"Smoke check failed: simulation mismatch: {simulation}", file=sys.stderr)
            return 1

        watch = _post_json(
            f"{base_url}/api/watchlist/items",
            {
                "item_type": "strategy",
                "title": "Smoke spread watch",
                "protocol": "pendle",
                "rules": {
                    "borrow_apy_above_threshold": 0.08,
                    "net_spread_below_threshold": 0.02,
                    "liquidity_below_threshold": 500000,
                },
                "snapshot": {
                    "borrow_apy": 0.1,
                    "net_spread_apy": 0.01,
                    "liquidity_usd": 250000,
                },
            },
        )
        watch_id = watch.get("item", {}).get("id")
        if not watch_id:
            print(f"Smoke check failed: watchlist creation mismatch: {watch}", file=sys.stderr)
            return 1

        watch_eval = _post_json(f"{base_url}/api/watchlist/items/{watch_id}/evaluate", {})
        if not watch_eval.get("created_alerts"):
            print(f"Smoke check failed: watchlist evaluation mismatch: {watch_eval}", file=sys.stderr)
            return 1

        alerts = _get_json(f"{base_url}/api/watchlist/alerts")
        if not alerts.get("items"):
            print(f"Smoke check failed: alert list empty: {alerts}", file=sys.stderr)
            return 1

        alert_id = alerts["items"][0]["id"]
        updated_alert = _patch_json(
            f"{base_url}/api/watchlist/alerts/{alert_id}",
            {"status": "acknowledged"},
        )
        if updated_alert.get("alert", {}).get("status") != "acknowledged":
            print(f"Smoke check failed: alert update mismatch: {updated_alert}", file=sys.stderr)
            return 1

        options = _post_json(
            f"{base_url}/api/options/analyze",
            {
                "option_type": "call",
                "underlying_asset": "ETH",
                "underlying_price": 3000,
                "strike_price": 3200,
                "premium": 150,
                "implied_volatility": 0.75,
                "bid": 145,
                "ask": 155,
                "scenario_prices": [2800, 3200, 3500],
            },
        )
        if options.get("breakeven_price") != 3350 or len(options.get("scenarios", [])) != 3:
            print(f"Smoke check failed: options analysis mismatch: {options}", file=sys.stderr)
            return 1
    except URLError as exc:
        print(f"Smoke check failed: API request failed: {exc}", file=sys.stderr)
        return 1

    print(
        "Smoke checks passed: /health, /api/protocols, demo seed/status/scenarios, "
        "deployment status, /api/analyze, "
        "report retrieval, markdown export, monitoring, evaluation, review queue, "
        "evaluation report retrieval, simulation, watchlist, alert events, and options"
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
