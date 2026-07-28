# V1 Phase 17 Validation and Correction Summary

Status: **Complete on `main`**

Phase 17 was merged by commit `7d934d6` through pull request `#3`. The merged
implementation includes durable job, attempt, event, worker, credential,
artifact, provider-cost, and capacity records; PostgreSQL-safe claim and
recovery; authenticated asynchronous analysis; cooperative cancellation;
tenant-scoped job access; private job UI; retention; and dry-run Vast job
controls.

## Correction history

The final branch corrections covered:

- execution supervision, heartbeat horizons, lease-loss handling, and
  no-overlap worker claims;
- non-destructive membership and organization authorization revocation under
  PostgreSQL row locks;
- reconstruction of missing global, provider, user, and organization capacity
  rows, including budget periods and completed provider spend;
- conservative provider-cost finalization for uncertain outcomes;
- server-owned retry classification and real Vast.ai fail-closed checks;
- BFF rejection of `/internal/workers/*`;
- completion cleanup of stale retry error fields.

Git history preserves the individual correction commits and review sequence.
No historical evidence was deleted during Phase 18 preparation.

## Validation evidence

- Repository CI passed on the current `main` head before Phase 18 branching:
  workflow run `30257655381` for commit `0c31d7f`.
- The merged PostgreSQL CI suite covers claim contention, authorization
  revocation races, capacity reconstruction, provider spend, and migration
  safety.
- Production manual-dispatch worker runs successfully claimed and completed
  scoped `analysis.generate` jobs without an inbound worker port.
- The production BFF rejected worker-internal routes, private job access
  required authentication, cancellation completed safely, and completed jobs
  linked to durable reports.
- Real Vast.ai rentals remain disabled and unverified.

## Remaining external validation

Phase 22 retains the real-provider, reliable custom SMTP, deployed multi-user
identity/MFA, legal, backup/restore, and final launch-approval gates.

The low-cost scheduled GitHub worker is not a continuously available worker.
Recent scheduled runs can fail while the free Render service cold-starts
because the worker's claim request has a bounded timeout. This is an
operational limitation, not a repository CI failure, and remains part of the
Phase 22 deployment validation and operations review.
