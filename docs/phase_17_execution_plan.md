# V1 Phase 17 Execution Plan — Durable Jobs and Hybrid Workers

Status: **In Progress — 17A implemented; 17B–17F planned**

Branch: `agent/v1-phase-17-durable-jobs`

This document turns the broad Phase 17 contract in
[`future_phase_contracts.md`](future_phase_contracts.md) into the specific implementation,
security, migration, rollout, and validation plan for this branch. It is a plan only: no job,
worker, artifact, or hosted-worker behavior is claimed until implementation evidence exists.

Phase 17 starts from Phase 16 as merged in `main`. Every job and worker path must preserve the
existing actor, ownership, organization, visibility, quota, audit, consent, retention, and
public-demo boundaries.

Where this plan is more restrictive or more specific than the broad Phase 17 contract, follow
this plan for implementation and update the broad contract during the final documentation pass.

Phase 17A implementation evidence now exists for durable schemas, migration, closed transitions,
sequenced events, a platform-admin worker registry, separately hashed/scoped worker credentials,
deletion disposal, retention cleanup, and focused tests. It does not add job submission, internal
worker protocol endpoints, worker execution, asynchronous analysis, or a browser jobs workspace.

---

## 1. Scope and rollout order

### Required initial job type

| Job type | Submitter | Purpose | Boundary |
| --- | --- | --- | --- |
| `analysis.generate` | authenticated owner or authorized organization member | Generate a saved analysis/report outside the web request | The authenticated analysis path becomes asynchronous only after the queue and worker are proven. The bounded anonymous public-demo path remains synchronous and receives no worker or provider controls. |

### Gated provider job type

| Job type | Submitter | Purpose | Boundary |
| --- | --- | --- | --- |
| `vast.session.start` | platform administrator with required MFA assurance | Start an explicitly approved and guarded Vast.ai session | Disabled and dry-run by default. A queued job is not permission to rent arbitrary hardware. Provider profile, image, model, cost, runtime, and remote-GPU permission are server-controlled. |

`analysis.generate` is the core Phase 17 proof. `vast.session.start` is enabled only after the
queue, lease, retry, cancellation, idempotency, audit, and cleanup paths pass with fake/dry-run
providers.

Document ingestion, embeddings, notification delivery, scheduled monitoring, tenant vector
retrieval, billing, and arbitrary user-defined compute are not implemented in Phase 17. Phase 18
uses the job platform for durable ingestion and storage. Phase 20 adds scheduling and notification
delivery.

---

## 2. Delivery and trust model

### 2.1 At-least-once execution

The queue is explicitly **at least once**. A worker may receive the same logical job again after a
lease expires, a network response is lost, or a process crashes.

The system must not claim exactly-once execution. Instead, it provides effectively-once durable
side effects through:

- unique idempotency constraints;
- preallocated result resource IDs;
- monotonic lease generations;
- per-attempt lease tokens;
- conditional terminal updates;
- provider reconciliation before retry;
- idempotent cleanup and completion services.

### 2.2 Control plane and worker boundary

```text
Browser
  -> Vercel Next.js BFF
  -> Render FastAPI user/control-plane API
     -> PostgreSQL job, attempt, event, worker, quota, and result state

Local/trusted worker
  -> outbound HTTPS to versioned internal worker API
  -> claim bounded execution envelope
  -> execute an allowlisted executor
  -> heartbeat/progress/complete/fail

Optional hosted worker
  -> same outbound protocol
  -> no inbound public port
  -> no browser/user token
```

All job-state transitions are authorized by the FastAPI control plane. The browser-facing BFF must
not proxy the internal worker route family.

A remote worker does not receive general production database credentials by default. Provider and
model secrets are injected into the worker runtime through environment/secret configuration, never
through job payloads. If a trusted co-located execution profile temporarily needs direct database
access, it requires a separately documented least-privilege database role and is not the baseline
hosted-worker design.

### 2.3 No implicit authority

- A job ID never grants access.
- A worker token is not a user session or platform-admin token.
- A job stores actor and tenant scope but does not retain a user bearer token.
- A worker cannot choose another tenant, owner, priority, provider profile, cost limit, or result ID.
- A provider credential never appears in job input, result, progress, event, audit, or error data.
- Public-demo visitors cannot submit jobs, operate workers, inspect private job state, or rent GPUs.

---

## 3. Persistent model

### 3.1 `jobs`

Required fields include:

```text
id
job_type
status
priority_class
owner_user_id
organization_id
created_by_user_id
visibility
input_schema_version
input_json
request_fingerprint
result_schema_version
result_json
result_resource_type
result_resource_id
error_code
error_summary
attempt_count
max_attempts
available_at
queue_expires_at
deadline_at
leased_by_worker_id
lease_generation
lease_token_hash
lease_expires_at
heartbeat_at
progress_percent
progress_message
idempotency_key
cancel_requested_at
started_at
completed_at
failed_at
estimated_cost_microusd
reserved_cost_microusd
actual_cost_microusd
created_at
updated_at
deleted_at
```

Rules:

- money/cost uses integer micro-USD or an equivalent fixed-precision representation, never binary
  floating point;
- `priority_class` is server-derived from a small enum; users cannot submit arbitrary numeric
  priority;
- `input_json`, `result_json`, progress, and errors are schema-versioned, size-bounded, and
  secret-free;
- completed analysis jobs reference a durable database report through
  `result_resource_type=report` and `result_resource_id`;
- `lease_generation` increases on every successful claim;
- only one terminal timestamp may describe the final outcome;
- soft-deleted jobs are excluded from ordinary lists but remain available to required retention or
  audit processes.

### 3.2 `job_attempts`

A separate attempt ledger is required. Do not infer attempt history only from the mutable job row.

```text
id
job_id
attempt_number
worker_id
lease_generation
started_at
heartbeat_at
ended_at
outcome
error_code
error_summary
runtime_ms
estimated_cost_microusd
actual_cost_microusd
created_at
```

Attempt history supports debugging, stale completion rejection, retry accounting, provider
reconciliation, and operator replay review.

### 3.3 `job_events`

```text
id
job_id
sequence_number
event_type
message
metadata_json
actor_user_id
worker_id
created_at
```

Requirements:

- unique `(job_id, sequence_number)`;
- events are append-only, bounded, redacted, and tenant-filtered;
- user-visible messages are separate from internal metadata;
- events use cursor pagination and retention limits;
- no raw provider response, stack trace, token, cookie, email, prompt secret, or credential.

### 3.4 `workers`

```text
id
name
status
protocol_version
software_version
capabilities_json
allowed_job_types
max_concurrency
last_seen_at
disabled_at
created_at
updated_at
```

A durable worker registry is required because `leased_by_worker_id`, health, capabilities,
concurrency, revocation, and operator visibility cannot be represented safely by a credential row
alone.

### 3.5 `worker_credentials`

```text
id
worker_id
token_prefix
token_hash
allowed_job_types
status
expires_at
last_used_at
rotated_from_id
revoked_at
created_by_user_id
created_at
```

Requirements:

- opaque high-entropy token;
- lookup prefix plus constant-time hash verification;
- plaintext returned exactly once;
- platform-admin creation requires the configured MFA assurance;
- overlap-safe rotation with explicit old-token revocation;
- token never appears in logs, URLs, events, audit metadata, or job payloads;
- credential scope cannot exceed the worker's allowed job types.

### 3.6 `artifacts`

Phase 17 distinguishes two artifact classes:

1. **Durable resource references**, such as a database-backed report or export recipe. These may be
   available in Phase 17 because the referenced resource is already durable and authorization is
   enforced by the application.
2. **Binary/object artifacts**, such as generated files. These remain `pending_storage` or
   `incomplete` until Phase 18 provides durable object storage and authorized delivery.

Required metadata:

```text
id
job_id
artifact_type
status
owner_user_id
organization_id
visibility
resource_type
resource_id
storage_backend
storage_key
content_type
size_bytes
checksum
retention_until
created_at
updated_at
deleted_at
```

A temporary local path is never a durable artifact and must not make a job appear successfully
complete.

---

## 4. Closed state machine

Required statuses:

```text
queued
leased
running
retry_wait
completed
failed
cancel_requested
cancelled
dead_letter
```

Only the job service may transition states. Request schemas never accept arbitrary status values.

Minimum allowed transitions:

```text
queued -> leased
queued -> cancel_requested -> cancelled
queued -> failed              # queue expiry or authorization revoked

leased -> running
leased -> retry_wait           # expired/released lease
leased -> cancel_requested
leased -> failed               # permanent pre-execution failure

running -> completed
running -> retry_wait
running -> failed
running -> cancel_requested -> cancelled

retry_wait -> leased
retry_wait -> cancel_requested -> cancelled
retry_wait -> dead_letter

failed -> queued               # operator replay creates a new linked job; original remains terminal

dead_letter -> queued          # operator replay creates a new linked job; original remains terminal
```

Terminal jobs are immutable except for retention metadata. Replay creates a new job with
`replay_of_job_id` or equivalent lineage rather than rewriting terminal history.

---

## 5. Transactional submission and idempotency

### 5.1 Client idempotency contract

Authenticated asynchronous submission uses an `Idempotency-Key` header or an equivalent explicit
client-generated key. The key is bounded and scoped by:

```text
subject type + subject ID + job type + idempotency key
```

The server computes a canonical request fingerprint from the validated, server-normalized input.

- same key and same fingerprint -> return the authorized existing job;
- same key and different fingerprint -> `409 Idempotency conflict`;
- duplicate submission consumes no second quota or budget reservation;
- a caller cannot discover another tenant's job through an idempotency key.

### 5.2 One submission transaction

The following must occur in one PostgreSQL transaction or a proven equivalent:

1. validate the actor and current tenant/resource scope;
2. validate the job type and schema version;
3. derive priority, result IDs, deadline, queue expiry, and cost estimate;
4. obtain the idempotency record/unique boundary;
5. atomically check and reserve product quota, queue capacity, concurrency, and cost budget;
6. create the job and initial event;
7. preallocate analysis/report resource linkage where required;
8. commit once.

Avoid check-then-insert races. PostgreSQL uniqueness, upsert, advisory/row locks, or a documented
combination must protect first-use and concurrent submissions.

### 5.3 Quota and budget semantics

Product quota and compute-budget reservations are separate concepts.

- accepted job submission reserves one action quota and the estimated compute budget;
- an idempotent duplicate reserves nothing additional;
- rejection before creation reserves nothing;
- cancellation before first lease may release the compute reservation according to policy;
- after execution starts, product action quota is not silently refunded;
- unused compute reservation is released on terminal completion/cancellation/failure;
- actual cost is persisted when available;
- platform/provider failure refund behavior is explicit and tested, not accidental.

---

## 6. Authorization lifecycle

Authorization is checked at submission and before execution.

A queued job must not start when, before its first lease:

- the owner account is inactive/deleted;
- the organization is disabled/deleted;
- the submitting membership is removed when that membership is required;
- the referenced thesis/source/resource is deleted or no longer authorized;
- the plan or job-type entitlement is revoked.

Such a job transitions to a controlled terminal state with a redacted event and released compute
reservation.

For already running work, revocation sets `cancel_requested`. The worker stops at the next safe
boundary and performs required cleanup. External side effects that cannot be undone are recorded
honestly; the system must not claim they never occurred.

Account export, account deletion, organization deletion, retention cleanup, and administrator audit
views must include or correctly dispose of jobs, attempts, events, artifacts, worker-created
resources, and reservations.

---

## 7. Versioned internal worker protocol

User APIs remain under `/api/jobs`. Worker APIs use a separate versioned internal route family,
for example:

```text
POST /internal/workers/v1/claim
POST /internal/workers/v1/heartbeat
POST /internal/workers/v1/jobs/{job_id}/progress
POST /internal/workers/v1/jobs/{job_id}/complete
POST /internal/workers/v1/jobs/{job_id}/fail
POST /internal/workers/v1/jobs/{job_id}/release
GET  /internal/workers/v1/jobs/{job_id}/cancellation
```

The Vercel BFF must explicitly reject `/internal/workers/*` and any future worker-only route family.
Workers call the Render control plane directly over HTTPS.

### 7.1 Claim request

The worker sends:

- worker identity/credential;
- protocol and software version;
- allowed capabilities/job types;
- available execution slots;
- optional provider profile availability.

### 7.2 Atomic claim

Use one PostgreSQL transaction with `FOR UPDATE SKIP LOCKED` or an equivalently proven strategy.
The claim query:

- selects only eligible `queued` or due `retry_wait` jobs;
- checks queue expiry, deadline, authorization state, worker scope, and job schema compatibility;
- orders by server priority, `available_at`, aging/fairness, and creation time;
- respects per-tenant and global running caps;
- increments `lease_generation`;
- creates a `job_attempts` row;
- stores only a hash of a new per-attempt lease token;
- sets lease owner/expiry and appends an event;
- returns a bounded execution envelope.

A tenant with many queued jobs must not starve all other tenants. Per-tenant running caps plus stable
ordering/aging are required even if a more advanced scheduler is deferred.

### 7.3 Heartbeat and lease token

Every state-changing worker call supplies:

```text
worker credential + job ID + lease generation + per-attempt lease token
```

The control plane rejects:

- stale generation;
- wrong worker;
- expired/revoked credential;
- expired lease;
- terminal job;
- unsupported job type;
- replayed completion from an earlier attempt.

Heartbeat extension is bounded by the job deadline and maximum runtime. A worker cannot keep a job
leased forever.

### 7.4 Worker freshness

Workers update `last_seen_at` through claims/heartbeats. Operator views distinguish active, stale,
disabled, and revoked workers. Queue acceptance is bounded even when no worker is online; queued
jobs have a maximum age and the UI must state that they are waiting for capacity.

---

## 8. Retry, recovery, and dead-letter behavior

Each executor defines:

- retryable error codes;
- permanent error codes;
- maximum attempts;
- exponential backoff with bounded jitter;
- maximum queue age;
- execution deadline;
- provider reconciliation rule;
- cleanup rule;
- dead-letter handling.

Lease expiry never blindly repeats an external side effect. Before retrying a provider operation,
the executor reconciles durable provider linkage to determine whether the previous attempt succeeded,
failed, or remains uncertain.

An uncertain provider outcome is not treated as a normal clean retry. It enters a controlled
reconciliation or operator-review path.

Dead-letter replay:

- requires an authorized platform operator for privileged jobs;
- creates a new linked job;
- uses a new idempotency boundary or documented replay boundary;
- preserves original attempts/events;
- revalidates current authorization, entitlement, capacity, and budget.

---

## 9. Cancellation race rules

Cancellation is idempotent.

- `queued`/`retry_wait`: cancellation may transition directly through `cancel_requested` to
  `cancelled` and release reservations.
- `leased`/`running`: set `cancel_requested`; the worker checks at safe boundaries.
- completion and cancellation use conditional updates against the current lease generation and
  state.
- if completion committed first, a later cancel request cannot rewrite the completed job.
- if cancellation committed first, a stale completion is rejected.
- external provider resources must be destroyed or reconciled before the cancellation workflow is
  considered finished.
- partial binary artifacts are deleted or marked incomplete; durable reports are not published as
  complete after cancellation.

The UI must distinguish `cancellation requested` from `cancelled`.

---

## 10. Executor contracts

### 10.1 `analysis.generate`

Submission preallocates stable `analysis_request_id` and `report_id` values. The same job retry uses
the same IDs.

Required rules:

- immutable, versioned, secret-free strategy input snapshot;
- server-derived owner/organization/visibility;
- unique linkage from analysis/report to source job;
- deterministic scoring and authoritative report fields remain unchanged;
- optional model wording remains non-authoritative and safely disabled by default;
- progress events contain phases, not raw prompts or retrieved private content;
- completion writes report/result linkage transactionally;
- a retry cannot create a second report;
- cancellation before completion publishes no completed report;
- anonymous public analysis remains synchronous and does not enter the queue.

The authenticated UI cutover is guarded by `ASYNC_ANALYSIS_ENABLED` or an equivalent feature flag.
Before the flag is enabled, existing authenticated synchronous behavior remains available. Rollback
must be possible without deleting queued jobs or corrupting reports.

### 10.2 `vast.session.start`

The current Vast lifecycle performs multiple provider side effects and therefore requires stronger
idempotency than an ordinary database job.

Required changes before enabling the job type:

- use a server-owned provider profile ID instead of arbitrary client image/model/container values;
- require platform administrator plus configured MFA assurance;
- require `VAST_ENABLED=true`, explicit remote-GPU permission, and `VAST_DRY_RUN=false` for a real
  rental;
- keep dry-run/fake provider as the automated-validation default;
- reserve cost before claim and enforce hourly/runtime/active-instance/provider caps;
- persist provider request/session linkage before or immediately around the external side effect;
- reconcile existing instance/contract IDs after timeout or lost response before retry;
- never issue a second rental merely because the worker did not receive the first HTTP response;
- make destroy and cleanup idempotent;
- cancellation requests cleanup and records uncertain/failed cleanup honestly;
- no ordinary analysis, public request, or model fallback automatically submits this job.

A real Vast.ai rental is not required in CI and is not required to prove queue correctness. Any live
provider verification is explicit, budget-limited, manually initiated, and documented without
credentials or raw provider responses.

---

## 11. Configuration and feature flags

Introduce explicit settings such as:

```text
JOBS_ENABLED
WORKER_API_ENABLED
ASYNC_ANALYSIS_ENABLED
VAST_JOB_ENABLED
JOB_DEFAULT_MAX_ATTEMPTS
JOB_LEASE_SECONDS
JOB_HEARTBEAT_SECONDS
JOB_MAX_LEASE_EXTENSION_SECONDS
JOB_MAX_QUEUE_AGE_SECONDS
JOB_EVENT_RETENTION_DAYS
JOB_TERMINAL_RETENTION_DAYS
JOB_MAX_INPUT_BYTES
JOB_MAX_RESULT_BYTES
JOB_MAX_PROGRESS_MESSAGE_LENGTH
JOB_GLOBAL_RUNNING_LIMIT
JOB_USER_PENDING_LIMIT
JOB_USER_RUNNING_LIMIT
JOB_ORG_PENDING_LIMIT
JOB_ORG_RUNNING_LIMIT
JOB_DAILY_COST_BUDGET_MICROUSD
WORKER_PROTOCOL_VERSION
WORKER_TOKEN_PEPPER
```

Requirements:

- disabled-by-default rollout for job execution and Vast jobs;
- production fails closed when worker routes are enabled without required credential/hash settings;
- public demo remains functional with all Phase 17 flags disabled;
- a web deployment can submit jobs only when the queue is enabled;
- worker protocol version mismatch returns a controlled response;
- no secret appears in deployment status.

---

## 12. Execution slices

### 17A — Schema, state machine, worker registry, and credential identity

**Goal:** establish persistent contracts before exposing execution endpoints.

Deliverables:

- add `jobs`, `job_attempts`, `job_events`, `workers`, `worker_credentials`, and `artifacts` models;
- add one or more reviewable Alembic migrations with foreign keys, uniqueness constraints,
  fixed-precision cost fields, and claim/tenant/retention indexes;
- implement the closed transition service;
- implement append-only event sequencing;
- implement worker registration, credential creation, verification, rotation, and revocation;
- add bounded schemas and production configuration validation;
- extend account/organization deletion and retention behavior for new records;
- emit redacted audit events for worker credential and privileged lifecycle operations.

Checkpoint:

- PostgreSQL upgrade/downgrade/upgrade succeeds from the Phase 16 schema;
- model and migration tests prove constraints/indexes;
- invalid transitions and cross-tenant reads fail;
- raw credential is returned once and never persisted;
- Phase 16 authorization/quota/regression tests pass.

### 17B — Transactional tenant-aware control plane

**Goal:** make submission and observation safe before execution exists.

Deliverables:

- implement `POST /api/jobs`, `GET /api/jobs`, `GET /api/jobs/{id}`,
  `POST /api/jobs/{id}/cancel`, and `GET /api/jobs/{id}/events`;
- require scoped idempotency and canonical request fingerprints;
- combine authorization, quota, budget, capacity reservation, job creation, result-ID allocation,
  and initial event in one transaction;
- implement per-user, per-organization, global, and provider-specific pending/running caps;
- implement queue expiry and bounded acceptance when no worker is active;
- add authorized operator replay as a new linked job rather than terminal-state mutation;
- keep event listing tenant-filtered and cursor-paginated.

Checkpoint:

- two users and two organizations cannot list, read, cancel, replay, or infer each other's jobs;
- concurrent duplicate submissions return one job and one reservation;
- same idempotency key with different payload returns `409`;
- public-demo submission is denied;
- old synchronous analysis remains available until 17D rollout.

### 17C — Versioned worker protocol, atomic leasing, and fake executor

**Goal:** prove queue mechanics before connecting valuable side effects.

Deliverables:

- add the `/internal/workers/v1/*` protocol and block it from the Vercel BFF;
- implement atomic claim with `SKIP LOCKED`, fairness/caps, lease generation, attempt row, and
  per-attempt lease token;
- implement heartbeat, progress, complete, fail, release, cancellation check, stale-worker
  detection, lease expiry recovery, retry/backoff, and dead-letter;
- add a fake deterministic executor used only for queue lifecycle tests;
- add the local worker command with allowlisted executor registry, bounded concurrency, protocol
  version, polling backoff, and graceful shutdown;
- add optional Compose worker service with no published port.

Checkpoint:

- concurrent PostgreSQL claim produces one winner;
- lost response and lease expiry are safely recovered;
- stale completion cannot overwrite a newer attempt;
- revoked/wrongly scoped worker receives no payload or mutation access;
- SIGTERM stops claiming and safely finishes/releases work;
- public demo works with worker disabled.

### 17D — Asynchronous authenticated analysis and safe rollout

**Goal:** migrate one valuable workflow after the queue is proven.

Deliverables:

- implement `analysis.generate` with preallocated IDs, immutable input, source-job uniqueness, and
  idempotent transactional completion;
- preserve deterministic scoring, provenance, missing-data visibility, and advice/non-execution
  boundaries;
- update authenticated frontend analysis to submit a job, show queue/progress/cancel state, and
  open the resulting report;
- retain anonymous synchronous analysis;
- add `ASYNC_ANALYSIS_ENABLED` rollout/rollback behavior;
- add waiting-for-worker, queue-expired, retry-wait, failed, cancelled, and completed UX.

Checkpoint:

- authenticated job survives API and worker restart;
- retry produces one report;
- cancellation produces no completed report;
- membership/account revocation before execution prevents work;
- browser flow passes with tokens still confined to HttpOnly cookies;
- disabling the feature flag restores the documented synchronous fallback without data loss.

### 17E — Vast adapter and operational hardening

**Goal:** connect the proven queue to the existing guarded provider lifecycle without creating
uncontrolled spend.

Deliverables:

- refactor Vast startup into an idempotent, reconcilable job executor;
- use server-owned provider profiles and explicit administrator/MFA authorization;
- persist provider linkage and reconcile timeout/lost-response cases before retry;
- enforce cost reservation, runtime, offer, GPU, verified-host, active-instance, startup, and
  cleanup limits;
- keep dry-run/fake mode default and real rental opt-in;
- implement worker/operator views for active/stale workers, queue depth, dead letters, and provider
  cleanup failures;
- document hosted outbound worker deployment, credential rotation, restart, and rollback.

Checkpoint:

- replayed/lost-response fake Vast job creates one provider session request;
- cancel/failure invokes idempotent cleanup;
- cost/provider caps reject work before execution;
- no real rental occurs in CI;
- no ordinary analysis or public route can submit the provider job.

### 17F — Workspace, retention, documentation, and release validation

**Goal:** make the system understandable, supportable, and ready for Phase 18.

Deliverables:

- add authenticated jobs workspace/account section;
- show authorized status, progress, attempts summary, cancellation, safe errors, result references,
  queue waiting, and retry/operator guidance;
- add retention cleanup for jobs, events, attempts, credentials, and incomplete artifacts;
- include user-visible jobs/results in account export and dispose of them correctly on deletion;
- update `README.md`, `current_state.md`, `architecture.md`, `deployment.md`, `testing.md`,
  `.env.example`, Compose, and the broad Phase 17 contract;
- add CI coverage for migrations, PostgreSQL leasing/idempotency/fairness, fake execution, browser
  flow, shutdown, retention, BFF denial, and Compose;
- record local versus externally verified worker/provider behavior accurately.

Completion checkpoint:

- every completion gate below has code and automated evidence;
- required repository checks and PostgreSQL concurrency/worker lifecycle tests pass;
- deployment/operator/credential/recovery runbooks are current;
- Phase 17 moves from **Planned** to **Complete** only after a final branch audit;
- Phase 18 remains unimplemented.

---

## 13. Required validation matrix

### Submission and tenancy

- same-key/same-payload idempotent submission;
- same-key/different-payload conflict;
- concurrent first submission creates one job/reservation;
- owner and organization isolation on list/detail/events/cancel/replay/artifacts;
- public-demo denial;
- removed member, deleted user, and disabled organization before execution;
- queue capacity and queue-expiry behavior.

### Leasing and worker security

- concurrent `SKIP LOCKED` claim;
- wrong scope/job type/protocol version;
- expired/revoked/rotated credential;
- lease-token mismatch;
- stale lease generation completion;
- heartbeat extension limit;
- worker freshness/staleness;
- BFF refuses internal worker routes;
- no token in logs/events/audits.

### Failure and recovery

- worker crash before start;
- worker crash during execution;
- network timeout after completion commit;
- lease expiry and reclaim;
- retryable/permanent error;
- bounded backoff/jitter;
- deadline and queue expiry;
- dead-letter and linked replay;
- cancellation/completion race;
- cleanup failure and uncertain provider result.

### Results and cost

- one analysis/report after retries;
- no completed report after cancellation;
- deterministic report fields remain authoritative;
- quota and compute reservation are not double-counted;
- fixed-precision estimated/reserved/actual cost;
- unused reservation release;
- user/org/global/provider caps;
- artifact/resource authorization and incomplete binary handling.

### Operations

- API restart with queued/running jobs;
- worker restart;
- graceful SIGTERM;
- worker disabled public-demo regression;
- retention dry-run and active cleanup;
- account export/deletion and organization deletion;
- Compose worker has no published port;
- no real Vast rental or paid provider dependency in CI.

---

## 14. Implementation order and commit discipline

Implement in this order:

```text
17A schema and identity
17B submission/control plane
17C worker protocol and fake executor
17D asynchronous authenticated analysis
17E Vast adapter and operations
17F workspace, retention, documentation, and final validation
```

Each slice receives a focused commit only after its checkpoint passes. Corrections remain on the
same branch. Do not merge automatically.

Before each slice:

```bash
git status
git fetch origin
git switch agent/v1-phase-17-durable-jobs
git pull --ff-only origin agent/v1-phase-17-durable-jobs
git log -1 --oneline
git diff origin/main...HEAD --stat
```

Read:

- `docs/current_state.md`;
- `docs/development_plan.md`;
- this execution plan;
- Phase 17 in `docs/future_phase_contracts.md`;
- `docs/architecture.md`;
- `docs/deployment.md`;
- `docs/testing.md`;
- `docs/agent_execution_guide.md`;
- the archived Phase 16 contract and evidence.

Do not add Phase 18 object/vector storage, billing, scheduled notifications, arbitrary containers,
autonomous compute, wallets, transaction signing, custody, trade execution, or capital allocation
as convenience work.

---

## 15. Completion gates

Phase 17 is complete only when all are true:

- `analysis.generate` no longer blocks the authenticated web request;
- anonymous public analysis remains bounded and synchronous;
- accepted jobs survive API and worker restart;
- delivery is documented as at-least-once and side effects are effectively-once;
- transactional idempotency, quota, capacity, and cost reservation pass PostgreSQL contention tests;
- worker registry and credentials are scoped, revocable, rotation-ready, and secret-safe;
- versioned worker protocol is blocked from the browser BFF;
- atomic leasing, lease generations, attempt tokens, heartbeat, expiry, and recovery work;
- stale workers and stale completions cannot mutate a newer attempt;
- retry, backoff, deadline, dead-letter, replay, and cancellation races work;
- authorization revocation prevents queued work and cancels running work safely;
- analysis retries create one report with authoritative deterministic fields;
- local worker runs with no inbound port and shuts down gracefully;
- cost, queue, tenant, global, and provider caps are enforced;
- Vast job remains admin/MFA-only, dry-run by default, idempotent, and cleanup-safe;
- durable database result references are authorized;
- binary artifacts are not falsely labeled durable before Phase 18;
- jobs/attempts/events/artifacts participate in export, deletion, audit, and retention;
- browser job workspace and polling states pass;
- Phase 15 and Phase 16 regression suites pass;
- Alembic upgrade/downgrade/upgrade passes from the Phase 16 PostgreSQL schema;
- backend, frontend, browser, Compose, and worker tests pass;
- documentation and operator runbooks match implementation.

---

## 16. Merge blockers

Treat these as blocking:

- direct background tasks or in-memory queues used as the durable queue;
- claims of exactly-once execution;
- no worker registry or no per-attempt history;
- worker credentials reused as user/admin tokens;
- raw worker/provider secrets in payloads, logs, events, or audit metadata;
- browser BFF can proxy worker-only routes;
- remote worker receives unrestricted production database credentials without an explicit
  least-privilege design review;
- idempotency, quota, or budget checks use race-prone check-then-insert logic;
- stale worker can complete a newer lease;
- membership/account/organization revocation does not affect queued jobs;
- retry after an uncertain provider response can create duplicate spend;
- client controls arbitrary priority, provider image/model, cost, runtime, tenant, owner, or result
  resource;
- cancellation rewrites a completed job or publishes a completed result after cancellation;
- a temporary local file is represented as a durable artifact;
- authenticated analysis cutover has no feature flag or rollback path;
- a normal/public analysis can trigger Vast.ai;
- real Vast rental occurs in CI;
- jobs and events are omitted from retention, account export, or deletion behavior;
- existing Phase 15/16 tests fail;
- documentation claims implementation that only exists as scaffolding or mocks.

---

## 17. Exit review

Before proposing a merge, audit the branch against both this plan and sections 17.1–17.16 of
[`future_phase_contracts.md`](future_phase_contracts.md). The final report must explicitly cover:

1. state model, migrations, constraints, and retention;
2. transactional submission, idempotency, quota, and cost reservation;
3. authorization and tenant isolation across the full job lifecycle;
4. worker registry, credential lifecycle, protocol versioning, and BFF separation;
5. PostgreSQL claim atomicity, lease generations, attempts, heartbeats, and recovery;
6. retry, dead-letter, replay, cancellation races, and partial-output cleanup;
7. analysis result idempotency and deterministic-field preservation;
8. Vast provider reconciliation, spend controls, and cleanup;
9. local worker shutdown and no-inbound-port topology;
10. browser workspace, polling, error states, and resource authorization;
11. every command and automated/manual test result;
12. files and commits created;
13. remaining external worker/provider validation;
14. explicit recommendation on whether the branch is ready for a draft pull request or merge.

Do not merge the branch automatically.
