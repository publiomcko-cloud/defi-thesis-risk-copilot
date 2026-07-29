"""Run safe Phase 19D HTTP synthetics without logging response bodies or tokens.

The command is off by default. Operators must enable it explicitly and provide
an origin-only target. Optional authenticated checks read a server-side bearer
token from the environment, never a command-line argument or command output.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


@dataclass(frozen=True)
class SyntheticResult:
    name: str
    status: str
    http_status: int | None
    latency_ms: int


def run_synthetic_checks(
    base_url: str,
    *,
    timeout_seconds: float,
    authenticated: bool = False,
    bearer_token: str | None = None,
) -> list[SyntheticResult]:
    origin = _validated_origin(base_url)
    checks = [("health", "/health"), ("readiness", "/ready"), ("demo_status", "/api/demo/status")]
    if authenticated:
        if not bearer_token:
            raise ValueError("Authenticated synthetic checks require SYNTHETIC_CHECK_BEARER_TOKEN")
        checks.append(("authenticated_identity", "/api/auth/me"))
    opener = build_opener(_NoRedirect())
    results: list[SyntheticResult] = []
    for name, path in checks:
        started = perf_counter()
        request = Request(
            f"{origin}{path}",
            headers={"Authorization": f"Bearer {bearer_token}"} if authenticated and name == "authenticated_identity" else {},
            method="GET",
        )
        try:
            with opener.open(request, timeout=timeout_seconds) as response:
                response.read(1)
                status = response.status
            results.append(SyntheticResult(name, "passed" if 200 <= status < 300 else "failed", status, _elapsed_ms(started)))
        except HTTPError as exc:
            results.append(SyntheticResult(name, "failed", exc.code, _elapsed_ms(started)))
        except (URLError, OSError, TimeoutError):
            results.append(SyntheticResult(name, "failed", None, _elapsed_ms(started)))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Origin-only HTTP(S) target")
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--authenticated", action="store_true")
    args = parser.parse_args()
    if args.timeout_seconds <= 0 or args.timeout_seconds > 30:
        parser.error("--timeout-seconds must be between 0 and 30")
    settings = get_settings()
    if not settings.operations_synthetic_checks_enabled:
        print(json.dumps({"status": "disabled", "detail": "Synthetic checks are disabled by configuration."}))
        return 2
    try:
        origin = _validated_origin(args.base_url)
        allowed_origins = _configured_origins(settings.operations_synthetic_allowed_origins)
        if origin not in allowed_origins:
            raise ValueError("--base-url must exactly match OPERATIONS_SYNTHETIC_ALLOWED_ORIGINS")
        results = run_synthetic_checks(
            origin,
            timeout_seconds=args.timeout_seconds,
            authenticated=args.authenticated,
            bearer_token=os.getenv("SYNTHETIC_CHECK_BEARER_TOKEN"),
        )
    except ValueError as exc:
        print(json.dumps({"status": "invalid", "detail": str(exc)}))
        return 2
    payload = {
        "status": "passed" if all(result.status == "passed" for result in results) else "failed",
        "checks": [result.__dict__ for result in results],
    }
    print(json.dumps(payload, sort_keys=True))
    return 0 if payload["status"] == "passed" else 1


def _validated_origin(value: str) -> str:
    parsed = urlparse(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("--base-url must be an origin-only HTTP(S) URL without credentials")
    return f"{parsed.scheme}://{parsed.netloc}"


def _configured_origins(value: str) -> set[str]:
    return {_validated_origin(item.strip()) for item in value.split(",") if item.strip()}


def _elapsed_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))


if __name__ == "__main__":
    raise SystemExit(main())
