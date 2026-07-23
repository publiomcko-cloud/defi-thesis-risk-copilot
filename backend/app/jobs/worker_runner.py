from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import time
from dataclasses import dataclass
from threading import Event
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.jobs.executors import get_executor
from app.jobs.schemas import WorkerClaimedJob


logger = logging.getLogger("defi_copilot.worker")


@dataclass
class ActiveLease:
    job_id: str
    lease_generation: int
    lease_token: str


class WorkerClient:
    def __init__(self, base_url: str, credential: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.credential = credential

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.credential}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=20) as response:  # noqa: S310 - URL is operator configured.
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:256]
            raise RuntimeError(f"Worker control plane returned HTTP {exc.code}: {detail}") from None
        except URLError as exc:
            raise RuntimeError("Worker control plane is unavailable") from exc


def run_worker(*, once: bool = False) -> int:
    base_url = os.getenv("WORKER_CONTROL_PLANE_URL", "http://127.0.0.1:8000")
    credential = os.getenv("WORKER_CREDENTIAL", "")
    protocol_version = os.getenv("WORKER_PROTOCOL_VERSION", "v1")
    poll_seconds = max(float(os.getenv("WORKER_POLL_SECONDS", "2")), 0.1)
    if not credential.startswith("wrk_"):
        raise RuntimeError("WORKER_CREDENTIAL must contain a worker-only credential.")

    stop_event = Event()
    active: ActiveLease | None = None

    def request_stop(*_args) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    client = WorkerClient(base_url, credential)
    while not stop_event.is_set():
        try:
            claimed = client.request("POST", "/internal/workers/v1/claim", {"protocol_version": protocol_version})
            payload = claimed.get("job")
            if payload is None:
                if once:
                    return 0
                stop_event.wait(poll_seconds)
                continue
            job = WorkerClaimedJob.model_validate(payload)
            active = ActiveLease(job.id, job.lease_generation, job.lease_token)
            lease_payload = {"lease_generation": job.lease_generation, "lease_token": job.lease_token}
            client.request("POST", f"/internal/workers/v1/jobs/{job.id}/start", lease_payload)
            client.request(
                "POST",
                f"/internal/workers/v1/jobs/{job.id}/progress",
                {**lease_payload, "progress_percent": 25, "progress_message": "Fake executor started controlled lifecycle validation."},
            )
            if stop_event.is_set():
                client.request("POST", f"/internal/workers/v1/jobs/{job.id}/release", lease_payload)
                active = None
                return 0
            cancelled = client.request("GET", f"/internal/workers/v1/jobs/{job.id}/cancellation")
            if cancelled.get("cancellation_requested"):
                client.request("POST", f"/internal/workers/v1/jobs/{job.id}/release", lease_payload)
            else:
                result = get_executor(job.job_type).execute(job)
                client.request(
                    "POST",
                    f"/internal/workers/v1/jobs/{job.id}/complete",
                    {**lease_payload, "result": {"result_schema_version": "fake_executor.v1", "result_json": result}},
                )
            active = None
            if once:
                return 0
        except RuntimeError as exc:
            logger.warning("Worker loop request failed: %s", exc)
            if once:
                return 1
            stop_event.wait(poll_seconds)

    if active is not None:
        try:
            client.request(
                "POST",
                f"/internal/workers/v1/jobs/{active.job_id}/release",
                {"lease_generation": active.lease_generation, "lease_token": active.lease_token},
            )
        except RuntimeError:
            logger.warning("Worker shutdown could not release the active lease.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the outbound-only local Phase 17 fake worker.")
    parser.add_argument("--once", action="store_true", help="Claim and process at most one job.")
    args = parser.parse_args()
    return run_worker(once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())
