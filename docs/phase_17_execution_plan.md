# V1 Phase 17 Execution Plan — Durable Jobs and Hybrid Workers

Status: **Planned**

This execution plan turns the Phase 17 contract in
[`future_phase_contracts.md`](future_phase_contracts.md) into reviewable implementation
increments. It is an implementation plan only: no job, worker, artifact, or hosted-worker
behavior is claimed by this document.

Phase 17 starts from Phase 16 as merged in `main`. All job resources must use the
existing actor, ownership, organization, visibility, quota, audit, and public-demo rules.

## 1. Scope and initial job types

Phase 17 creates a durable control plane for these initial job types:

| Job type | Submitter | Purpose | Boundary |
| --- | --- | --- | --- |
| `analysis.generate` | authenticated owner or authorized organization member | Generate a saved analysis/report outside the web request | The user-facing authenticated analysis path becomes asynchronous. The bounded anonymous public-demo path remains synchronous and must not gain access to worker or GPU controls. |
| `vast.session.start` | platform administrator only | Start an explicitly requested, guarded Vast.ai session | A job does not authorize a rental by itself. Existing allowlists, cost/runtimes, verified-host requirements, dry-run mode, startup polling, and cleanup remain mandatory. |

Document ingestion, embedding generation, notification delivery, scheduled monitoring, and
tenant vector retrieval are deliberately not implemented in Phase 17. Phase 18 will consume
the job platform for durable ingestion and storage.

## 2. Non-negotiable invariants

- A job identifier never grants access. Every list, detail, event, cancel, retry, and artifact
  lookup derives authorization from the current actor and the persisted resource scope.
- A worker credential is not a user session or a platform-user token. It is scoped, hashed,
  revocable, rotation-ready, and limited to explicit job types.
- Job input, progress, errors, and audit metadata contain no provider secrets or raw provider
  responses. Persisted errors are redacted and bounded.
- Leasing is atomic on PostgreSQL. A lease has one worker, an expiry, a bounded heartbeat
  extension, and an abandoned-work recovery path.
- Retrying the same idempotency boundary must not create a second report, artifact, charge, or
  Vast rental. Cancellation is idempotent and is checked at safe executor boundaries.
- The API/control plane exposes no worker inbound port. Workers poll or claim outbound over
  authenticated HTTPS in hosted operation; the local Compose topology may use the internal
  backend network only.
- Public-demo visitors cannot submit privileged jobs, operate workers, view private job data,
  or trigger a GPU rental. No ordinary analysis request rents a GPU.
- Phase 17 establishes durable artifact *records*. Phase 18 supplies durable object/vector
  storage; a temporary local file must never be represented as a completed durable artifact.

## 3. Proposed execution slices

### 17A — Durable schema, state machine, and worker identity

**Goal:** establish the persistent contracts before exposing execution endpoints.

Deliverables:

- Add `jobs`, `job_events`, `worker_credentials`, and `artifacts` SQLAlchemy models plus one
  Alembic migration. `jobs` includes every required Phase 17 field, owner/organization scope,
  visibility, a unique idempotency boundary, and PostgreSQL indexes for claim and tenant
  queries.
- Define the closed job status transition table: `queued`, `leased`, `running`,
  `retry_wait`, `completed`, `failed`, `cancel_requested`, `cancelled`, and `dead_letter`.
  Transitions occur in a service, never through arbitrary client input.
- Add typed job, worker, artifact, and event schemas. Bound payload, error summary, and
  progress-message sizes at the API boundary.
- Add worker-credential creation, verification, revocation, and rotation primitives. Store
  only token hashes and safe labels/scopes; return a plaintext token exactly once to the
  platform administrator who created it.
- Extend settings with explicit job lease, heartbeat, retry/backoff, concurrency, cost-budget,
  and worker authentication settings. Production validation fails closed when worker routes
  are enabled without their required secret/configuration.
- Emit redacted audit events for credential lifecycle and job-state changes.

Checkpoint:

- upgrade/downgrade/upgrade succeeds on PostgreSQL;
- model and migration tests prove constraints and indexes;
- invalid state transitions, unauthorized credential use, and cross-tenant resource lookup are
  rejected;
- existing Phase 16 authorization and quota tests continue to pass.

### 17B — Tenant-aware job control plane

**Goal:** make durable job submission and observation safe before a worker can execute work.

Deliverables:

- Implement authenticated `POST /api/jobs`, `GET /api/jobs`, `GET /api/jobs/{id}`,
  `POST /api/jobs/{id}/cancel`, and `GET /api/jobs/{id}/events` endpoints.
- Derive owner, organization, visibility, allowed job type, priority ceiling, cost estimate,
  quota subject, and idempotency scope on the server. Client input cannot set another user or
  organization.
- Apply per-user, per-organization, global, and provider-specific pending/running limits
  before a job is queued. Return an explicit backpressure response rather than silently
  accepting unserviceable work.
- Treat duplicate idempotency requests as a lookup of the authorized existing job. Do not
  enqueue a duplicate and do not consume a second quota/cost allocation.
- Persist bounded job events for queued, cancellation-requested, and rejected/backpressure
  outcomes. Keep event listing tenant-filtered and cursor-friendly.

Checkpoint:

- two users and two organizations cannot list, read, cancel, or infer each other's jobs/events;
- duplicate concurrent submissions return one job;
- quotas/concurrency/cost limits and public-demo denial are covered by tests;
- the old synchronous APIs retain their documented Phase 16 behavior until 17D migrates the
  authenticated analysis UI.

### 17C — Atomic claims, leases, and worker protocol

**Goal:** let a scoped worker safely acquire and report work without an inbound worker port.

Deliverables:

- Implement worker-only claim, heartbeat, progress, complete, and fail endpoints following
  the Phase 17 contract. Authenticate the worker on every call and enforce its allowed job
  types.
- Use a PostgreSQL transaction with `FOR UPDATE SKIP LOCKED` (or an equivalently proven
  atomic strategy) to claim one eligible queued/retry job. A worker can never hold two active
  leases for the same job.
- Add lease expiry recovery, stale-worker detection, bounded heartbeat extension, and an
  operator-safe recovery/replay path. Recovery records an event and preserves attempt history.
- Implement a typed retry policy with retryable/permanent error classification, exponential
  bounded backoff, maximum attempts, and dead-letter transition. Redact external error text.
- Make completion/failure messages lease-token and job-state aware so a stale worker cannot
  overwrite a newer lease or completed result.

Checkpoint:

- PostgreSQL concurrent-claim tests show one winning worker;
- lease expiry makes work claimable again exactly once;
- heartbeat, stale completion, retry/backoff, permanent failure, and dead-letter paths pass;
- revoked or wrongly-scoped worker credentials receive no payload or state-changing access.

### 17D — Bounded executors, idempotent results, and artifact references

**Goal:** connect the queue to the selected useful work without leaking Phase 18 scope.

Deliverables:

- Add a worker executor registry that accepts only the two Phase 17 job types and validates a
  versioned, secret-free input schema before execution.
- Implement `analysis.generate` as an asynchronous authenticated workflow. It creates or
  reuses one analysis request/report according to the job's idempotency boundary, preserves
  deterministic scoring and report safety rules, and publishes bounded progress events.
- Migrate the authenticated frontend analysis submission to create a job, poll its permitted
  job detail/events, and open the resulting report when complete. Keep the anonymous demo
  flow visibly bounded and synchronous.
- Wrap the existing guarded Vast startup service in `vast.session.start`; submission remains
  platform-admin-only and no worker executor runs a real rental in CI. Dry-run remains the
  default.
- Create artifact records for generated report/export references with checksum, content type,
  size, retention, owner/organization scope, and storage status. A record without Phase 18
  storage is pending/incomplete, never a public download. Failed/cancelled jobs clean up or
  mark their partial artifacts incomplete.

Checkpoint:

- an authenticated analysis survives API restart after queueing and produces only one report
  after retry;
- a cancelled analysis has no completed report/artifact;
- a duplicate/replayed Vast-start job does not create a second provider request;
- deterministic report fields remain authoritative and no job result supplies advice,
  transaction execution, or a wallet action.

### 17E — Local Docker worker, shutdown, and operational controls

**Goal:** make the worker operable locally and safely deployable as an outbound process.

Deliverables:

- Add a worker command with explicit `WORKER_ID`, bounded concurrency, allowed job types,
  polling interval, and graceful shutdown behavior. On shutdown it stops claiming, finishes
  safe work or releases its lease, and records the outcome.
- Add an optional Compose worker service with no published port. It uses the internal backend
  address and a separately configured worker credential; normal public-demo Compose operation
  remains usable with the worker disabled.
- Document equivalent hosted-worker deployment as an outbound process/service, including
  configuration, credential rotation/revocation, health/readiness signal, restart behavior,
  and the rule that no provider credentials belong in job payloads.
- Enforce global worker concurrency, per-job maximum runtime/deadline, cost estimates/budgets,
  provider caps, queue priority, and backpressure inside the control plane rather than in the
  browser.

Checkpoint:

- the local worker completes a fake analysis job using Compose without exposed inbound ports;
- a shutdown test proves it stops claiming and safely releases/finishes leases;
- disabled worker configuration leaves the existing public demo functional;
- cost and provider caps reject work before execution.

### 17F — Job workspace, documentation, and full validation

**Goal:** make the durable workflow understandable, observable, and ready for Phase 18.

Deliverables:

- Add an authenticated jobs workspace or account section with queued/running/retry/completed/
  failed/cancelled/dead-letter states, progress, safe retry guidance, authorized cancellation,
  report/artifact references, and no cross-tenant leakage.
- Add frontend error, loading, polling, and empty states; do not expose worker credentials,
  raw provider errors, or internal payloads.
- Update `README.md`, `current_state.md`, `architecture.md`, `deployment.md`, `testing.md`,
  `.env.example`, Compose files, and the Phase 17 contract if an implementation-discovered
  invariant requires clarification. Record what is locally tested versus externally verified.
- Add CI coverage for migration, PostgreSQL leasing, worker fake execution, browser job flow,
  and Compose configuration. CI must use fake Ollama/Vast providers and perform no rental.

Completion checkpoint:

- every Phase 17.15 completion gate is backed by code and automated evidence;
- required commands in `agent_execution_guide.md`, plus PostgreSQL concurrency and worker
  lifecycle tests, pass;
- deployment/operator runbook is current;
- Phase 17 may move from **Planned** to **Complete** only after the final audit confirms each
  of the above. Phase 18 remains unimplemented.

## 4. Implementation order and commit discipline

Implement one slice at a time in this order: 17A, 17B, 17C, 17D, 17E, then 17F. Each slice
gets a focused commit only after its checkpoint passes. A correction pass follows the same
branch and must not merge it.

Suggested branch: `agent/v1-phase-17-durable-jobs`.

Before each slice, compare the working tree to current `origin/main`, read the Phase 17
contract and the Phase 16 archive, and preserve all completed behavior. Do not add Phase 18
object storage, vector search, durable ingestion, billing, scheduling, or autonomous compute
as convenience work.

## 5. Pre-implementation decisions recorded for 17A

The following choices are intentionally settled early so later work does not create an
incompatible queue:

- PostgreSQL is the queue authority; in-memory queues and background tasks are not durable
  substitutes.
- API worker endpoints are the cross-environment protocol. A worker may share the database
  deployment for its executor dependencies, but job claiming and state transitions remain
  control-plane-authorized and atomic.
- Worker tokens are opaque random credentials stored only as hashes. A database token value is
  never recoverable, logged, embedded in a job, or reused as a browser/session token.
- Job events are durable, bounded records. The first UI uses polling; realtime subscriptions
  are not required for Phase 17.
- Artifact metadata is durable in Phase 17, while durable object storage and signed delivery
  are Phase 18 responsibilities. An artifact cannot be labeled `available` without a durable
  storage reference and authorization path.
- Production worker deployment is documented and configurable, but no real Vast.ai rental is
  necessary to complete automated validation. It remains opt-in and administrator-controlled.

## 6. Phase 17 exit review

Before proposing a merge, audit the branch against sections 17.1–17.16 of
[`future_phase_contracts.md`](future_phase_contracts.md). The review must explicitly cover:

1. authorization on every job/worker/artifact endpoint;
2. PostgreSQL atomicity and recovery under contention;
3. idempotency across reports and provider work;
4. cancellation, partial-output cleanup, and error redaction;
5. public-demo and Phase 16 regression behavior;
6. worker shutdown, no-inbound-port topology, and configuration validation;
7. cost/concurrency limits and no automatic GPU rental;
8. documentation accuracy and Phase 18 handoff boundaries.
