# V1 Future Phase Contracts — Phases 17–21

This document is the authoritative implementation contract for the product phases after V1 Phase 16.

Future implementation prompts should reference this file, [`development_plan.md`](development_plan.md), [`current_state.md`](current_state.md), and the selected phase section instead of restating the entire scope.

Related documents:

- [`phase_16_identity_ownership_contract.md`](phase_16_identity_ownership_contract.md)
- [`agent_execution_guide.md`](agent_execution_guide.md)
- [`architecture.md`](architecture.md)
- [`deployment.md`](deployment.md)
- [`testing.md`](testing.md)

---

## 1. Phase ordering and dependency graph

```text
Phase 16 — identity, ownership, quotas
  -> Phase 17 — durable jobs and workers
     -> Phase 18 — durable RAG and artifacts
        -> Phase 19 — operations and security hardening
           -> Phase 20 — analytics, notifications, commercial readiness
              -> Phase 21 — model and research intelligence expansion
```

Some work may overlap, but completion labels must respect dependencies.

### Dependency rules

- Phase 17 must not bypass Phase 16 actor, tenant, and quota boundaries.
- Phase 18 ingestion and retrieval must execute through Phase 17 jobs for heavy work.
- Phase 19 production claims require Phase 17 and Phase 18 operational paths to exist.
- Phase 20 billing and notifications depend on durable usage, jobs, observability, and identity.
- Phase 21 model automation depends on evaluation, provenance, worker controls, cost controls, and auditability from Phases 17–20.

---

# V1 Phase 17 — Durable Job Queue and Hybrid Workers

Status: **Planned**

## 17.1 Goal

Move heavy, slow, retryable, and provider-dependent work out of the public web process into a durable, observable, tenant-aware job system.

## 17.2 Target architecture

```text
Browser
  -> Vercel Next.js BFF
  -> Render FastAPI control plane
     -> PostgreSQL job queue/state
     -> object-storage references

Local/cloud worker
  -> outbound authenticated polling or claim
  -> lease job
  -> execute bounded task
  -> heartbeat/progress
  -> persist result/artifact
  -> complete, retry, cancel, or dead-letter
```

Workers require no public inbound port.

## 17.3 Job model

Required fields:

```text
id
job_type
status
priority
owner_user_id
organization_id
created_by_user_id
input_json
result_json
error_code
error_summary
attempt_count
max_attempts
available_at
leased_by_worker_id
lease_expires_at
heartbeat_at
progress_percent
progress_message
idempotency_key
cancel_requested_at
started_at
completed_at
failed_at
created_at
updated_at
```

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

## 17.4 Worker identity

Worker credentials are distinct from user sessions.

Requirements:

- scoped worker identity;
- hashed or asymmetric credentials;
- explicit allowed job types;
- organization/tenant scope where required;
- credential rotation and revocation;
- no platform-user bearer token reuse;
- no secret in job payloads;
- audit worker registration, revocation, claims, and completion.

## 17.5 Leasing and heartbeat

Claiming must be atomic.

Requirements:

- one active worker lease per job;
- lease timeout;
- periodic heartbeat;
- abandoned lease recovery;
- stale worker detection;
- bounded lease extension;
- database transaction or `SKIP LOCKED` strategy on PostgreSQL;
- no duplicate execution after ordinary contention.

## 17.6 Idempotency

Every retryable job type defines an idempotency boundary.

Examples:

- analysis generation keyed by request/job ID;
- document ingestion keyed by document version;
- embedding generation keyed by chunk/version/model;
- notification delivery keyed by event/channel/recipient;
- Vast session request keyed by controlled provider task.

Retries must not create duplicate reports, chunks, charges, notifications, or rentals.

## 17.7 Retry and dead-letter policy

Each job type defines:

- retryable errors;
- permanent errors;
- maximum attempts;
- backoff policy;
- deadline/timeout;
- dead-letter action;
- operator replay rules.

Raw provider errors are redacted before persistence or user display.

## 17.8 Cancellation and progress

Requirements:

- users may cancel only authorized jobs;
- workers check cancellation at safe interruption points;
- cancellation is idempotent;
- partial artifacts are removed or marked incomplete;
- progress events are durable and bounded;
- progress messages contain no secrets;
- frontend can poll or subscribe without exposing other tenants.

## 17.9 Local Docker worker

Provide a worker command and Compose service that:

- connects outbound to the control plane/database;
- supports selected job types;
- requires no inbound router configuration;
- has explicit concurrency;
- supports graceful shutdown;
- stops claiming before termination;
- completes or releases leases safely;
- uses local Ollama where configured;
- remains optional for normal public demo operation.

## 17.10 Vast.ai adapter

The adapter builds on existing guardrails:

- platform-admin or explicitly authorized job only;
- GPU allowlist;
- maximum hourly cost;
- maximum runtime;
- maximum active instances;
- verified-host requirement;
- startup timeout;
- health check;
- automatic destroy;
- cleanup after failure;
- idempotent destroy;
- durable provider session/job linkage.

No ordinary public request automatically rents a GPU.

## 17.11 Artifacts

Phase 17 establishes artifact references, while Phase 18 finalizes storage.

Requirements:

- artifact record with owner/organization scope;
- content type, size, checksum, status, storage key, retention;
- temporary local output is not treated as durable completion;
- signed access or BFF download authorization;
- no public bucket assumption;
- cleanup for failed/cancelled jobs.

## 17.12 Capacity and cost controls

- per-job estimated cost;
- per-user/org concurrent job limits;
- global worker concurrency;
- provider-specific caps;
- daily/monthly compute budgets;
- queue priority policy;
- backpressure when capacity is unavailable;
- no unbounded user-controlled resource request.

## 17.13 API and frontend

Suggested APIs:

```text
POST /api/jobs
GET /api/jobs
GET /api/jobs/{id}
POST /api/jobs/{id}/cancel
GET /api/jobs/{id}/events

POST /api/workers/claim
POST /api/workers/{id}/heartbeat
POST /api/workers/jobs/{id}/progress
POST /api/workers/jobs/{id}/complete
POST /api/workers/jobs/{id}/fail
```

Frontend requirements:

- job list;
- queued/running/completed/failed states;
- progress;
- cancel action;
- retry guidance;
- artifact links;
- no cross-tenant job visibility.

## 17.14 Testing

- atomic claim under concurrent workers;
- lease expiration and recovery;
- heartbeat extension;
- retry and backoff;
- dead-letter transition;
- idempotent duplicate submission;
- cancellation;
- worker credential denial/revocation;
- tenant isolation;
- cost/concurrency limits;
- graceful worker shutdown;
- provider fake for Vast/Ollama/remote model;
- PostgreSQL integration tests;
- no real rental in CI.

## 17.15 Completion gates

- heavy selected workflows no longer block the web process;
- jobs survive API/worker restart;
- atomic leasing works in PostgreSQL;
- abandoned work recovers;
- retries are idempotent;
- cancellation and progress work;
- worker auth is scoped and revocable;
- local worker runs without inbound ports;
- cost controls are enforced;
- artifacts have durable references;
- browser job flow passes;
- docs and runbooks are updated.

## 17.16 Out of scope

- final tenant vector architecture;
- billing collection;
- arbitrary remote code execution;
- unbounded user-provided containers;
- autonomous capital execution.

---

# V1 Phase 18 — Production RAG and Knowledge Storage

Status: **Planned**

## 18.1 Goal

Eliminate runtime-filesystem dependence and provide durable, versioned, tenant-aware document, chunk, embedding, retrieval, and artifact storage.

## 18.2 Architecture

```text
approved source or upload
  -> object storage original
  -> document/version record
  -> Phase 17 ingestion job
  -> extraction and normalization
  -> chunk records
  -> embeddings
  -> pgvector or selected vector store
  -> tenant/protocol filtered retrieval
  -> citation-integrity validation
```

## 18.3 Storage choices

Preferred starting point:

- Supabase/PostgreSQL for metadata and pgvector when scale is appropriate;
- S3-compatible object storage for original documents and generated artifacts.

A dedicated vector store requires a documented reason, migration plan, tenant isolation model, cost analysis, and operational ownership.

## 18.4 Data model

### Knowledge source

```text
id
owner_user_id
organization_id
visibility
source_type
source_uri
canonical_uri
protocol
chain
status
trust_state
approved_by_user_id
approved_at
created_at
updated_at
deleted_at
```

### Document

```text
id
knowledge_source_id
current_version_id
filename
media_type
storage_key
checksum
size_bytes
status
created_at
updated_at
deleted_at
```

### Document version

```text
id
document_id
version_number
storage_key
checksum
parser_version
chunker_version
embedding_model
status
created_by_job_id
created_at
superseded_at
```

### Chunk

```text
id
document_version_id
chunk_index
heading_path
content
content_checksum
token_count
metadata_json
embedding
created_at
deleted_at
```

### Retrieval event

```text
id
request_id
user_id
organization_id
query_hash
filters_json
retrieved_chunk_ids
scores
latency_ms
model_version
created_at
```

Do not store raw sensitive queries without an explicit privacy decision.

## 18.5 Tenant isolation

Retrieval filters are server-derived.

A request may retrieve:

- public approved sources;
- the caller's private sources;
- authorized active-organization sources.

The client cannot select another organization by sending an arbitrary organization ID.

Every SQL/vector query applies tenant and deletion filters before ranking.

## 18.6 Trust workflow

Required states:

```text
discovered
needs_review
approved_for_rag
rejected
archived
ingestion_pending
ingesting
ingested
ingestion_failed
deletion_pending
deleted
```

Automatic discovery may create candidates. Only human-approved sources may enter trusted retrieval unless a separate sandbox corpus is explicitly labeled and isolated.

## 18.7 Versioning and rollback

- immutable document versions;
- parser/chunker/embedding versions recorded;
- current version pointer;
- re-ingestion creates a new version;
- retrieval can roll back to a previous known-good version;
- lineage from report citation to chunk, version, document, and source;
- no silent overwrite of source content.

## 18.8 Re-embedding migrations

Requirements:

- create new embeddings beside old embeddings;
- track model and dimensions;
- evaluate before cutover;
- support partial backfill;
- switch active embedding version atomically;
- retain rollback window;
- delete obsolete vectors only after validation.

## 18.9 Deletion and tombstones

Deletion must:

- revoke retrieval immediately;
- tombstone metadata;
- schedule object/vector deletion;
- preserve required audit lineage without serving content;
- prevent stale cache retrieval;
- propagate to generated indexes;
- be idempotent.

## 18.10 Retrieval quality and observability

Track:

- latency;
- filter selectivity;
- top-k scores;
- source diversity;
- citation completeness;
- empty retrieval;
- duplicate chunks;
- stale/superseded content;
- user feedback where consented.

Do not log full private source content by default.

## 18.11 Evaluation

Required datasets:

- public protocol questions;
- tenant-isolation tests;
- known-citation questions;
- negative/no-answer questions;
- superseded-version tests;
- deletion tests;
- adversarial metadata/filter tests.

Metrics:

- recall@k;
- precision@k;
- citation accuracy;
- source coverage;
- no-answer correctness;
- tenant leakage rate, which must be zero;
- latency and cost.

## 18.12 Completion gates

- originals and generated artifacts are durable;
- runtime filesystem is not authoritative;
- tenant filters are enforced in retrieval;
- approved-source lineage is complete;
- document versions and rollback work;
- deletion removes content from retrieval;
- re-embedding migration is tested;
- ingestion runs through durable jobs;
- retrieval evaluation runs in CI or scheduled validation;
- citation-integrity checks pass;
- Phase 15 public curated retrieval remains available.

## 18.13 Out of scope

- autonomous trust of discovered sources;
- training models directly on private tenant data without explicit policy and consent;
- public access to private object-storage keys.

---

# V1 Phase 19 — Production Operations and Security

Status: **Planned**

## 19.1 Goal

Make the deployed control plane, worker system, storage, authentication, and tenant boundaries observable, recoverable, hardened, and operationally supportable.

## 19.2 Threat model

Document assets, actors, trust boundaries, entry points, abuse cases, and mitigations for:

- account takeover;
- session theft;
- broken object authorization;
- tenant data leakage;
- malicious uploads;
- prompt injection and poisoned sources;
- worker credential theft;
- job replay/duplication;
- SSRF through adapters or BFF;
- provider secret exposure;
- quota/rate-limit bypass;
- denial of service;
- supply-chain compromise;
- object-storage exposure;
- audit tampering;
- privileged administrator misuse.

## 19.3 Distributed rate limiting

Replace single-process public limits with shared enforcement.

Requirements:

- Redis, database, or managed limiter selected deliberately;
- per-IP/session/user/org/action keys;
- proxy-header trust configured correctly;
- burst and sustained limits;
- retry metadata;
- safe fail-open/fail-closed decision per endpoint;
- observability and abuse alerts;
- distinct product quota and network rate-limit concepts.

## 19.4 Edge and application security

- WAF policy;
- request-size limits;
- bot/abuse controls;
- CSP;
- HSTS;
- frame, MIME, referrer, and permissions policies;
- secure cookies;
- CORS allowlist;
- CSRF analysis for cookie-backed routes;
- BFF route allowlist tests;
- SSRF prevention;
- upload media-type and malware scanning path;
- dependency pinning and lockfile review.

## 19.5 Observability

Centralize:

- structured logs;
- error reporting;
- traces;
- API latency;
- database latency;
- queue depth;
- job duration/failure/retry;
- worker health;
- retrieval latency/empty rate;
- provider cost and failure;
- auth failures;
- quota/rate-limit events.

Correlation IDs connect:

```text
browser request
  -> BFF request
  -> API request
  -> job
  -> worker execution
  -> artifact/retrieval event
```

Logs must redact tokens, cookies, credentials, source content, and sensitive personal data.

## 19.6 Uptime and alerting

- liveness and readiness probes;
- public synthetic checks;
- authenticated synthetic checks using safe test tenant;
- queue/worker checks;
- object/vector storage checks;
- alert thresholds;
- escalation ownership;
- status-page integration foundation.

## 19.7 Backup and restore

- database backup policy;
- object-storage versioning/retention;
- encryption-at-rest verification;
- restoration procedure;
- recovery-point and recovery-time objectives;
- quarterly or defined restore drills;
- migration backup/rollback procedure;
- evidence retained without secrets.

## 19.8 Secret management

- production secret manager or platform secret storage;
- no repository secrets;
- key inventory and owner;
- rotation cadence;
- emergency rotation;
- service-role minimization;
- worker credential rotation;
- encryption-key migration plan;
- audit secret access where supported.

## 19.9 CI/CD security

- dependency scanning;
- container scanning;
- secret scanning;
- license review as appropriate;
- automated dependency updates;
- pinned actions;
- protected `main`;
- required checks;
- migration validation;
- preview environment safety;
- software bill of materials where practical.

## 19.10 Incident response

Runbooks for:

- credential leak;
- account takeover;
- tenant data exposure;
- malicious upload/source;
- queue duplication;
- runaway provider cost;
- database outage;
- object-storage outage;
- vector corruption;
- failed migration;
- compromised worker.

Each runbook defines detection, containment, eradication, recovery, communication, evidence, and retrospective actions.

## 19.11 Testing

- PostgreSQL integration suite;
- browser E2E suite;
- accessibility automation;
- load tests;
- burst/rate-limit tests;
- queue saturation;
- worker loss;
- database failover/recovery simulation;
- object-storage failure;
- provider timeout/failure;
- migration rollback rehearsal;
- authorization fuzz/negative tests;
- security-header checks;
- dependency/container scans.

## 19.12 Completion gates

- shared rate limiting active;
- WAF/security headers active;
- centralized logs/errors/traces active;
- request-to-job correlation works;
- uptime and queue alerts active;
- backup restore drill succeeds;
- secret rotation process tested;
- dependency/container/security checks required in CI;
- incident runbooks published;
- browser, PostgreSQL, accessibility, load, and failure tests run;
- threat model reviewed;
- unresolved critical/high findings block release.

---

# V1 Phase 20 — Product Analytics, Notifications, and Commercial Readiness

Status: **Planned**

## 20.1 Goal

Add privacy-conscious product measurement, scheduled monitoring, user-controlled notifications, plan enforcement, billing foundations, support operations, and commercial launch readiness.

## 20.2 Analytics principles

- collect only necessary events;
- define purpose and retention;
- avoid raw strategy/source content by default;
- pseudonymize identifiers where possible;
- honor consent and regional/legal requirements;
- separate operational telemetry from product analytics;
- document third-party processors;
- provide deletion/export behavior.

## 20.3 Event taxonomy

Examples:

```text
account_created
email_verified
login_succeeded
analysis_started
analysis_completed
analysis_failed
report_opened
thesis_saved
watchlist_created
alert_triggered
organization_created
member_invited
job_cancelled
quota_exceeded
subscription_started
subscription_changed
```

Events contain bounded metadata and no secrets.

## 20.4 Notifications

Channels may include:

- in-app;
- email;
- webhook;
- Telegram.

Requirements:

- explicit user preference;
- verified destination;
- per-channel enable/disable;
- severity/category filtering;
- quiet hours and timezone;
- rate limiting and digesting;
- signed webhooks;
- delivery retry through Phase 17 jobs;
- dead-letter handling;
- unsubscribe/revocation;
- no trading execution.

## 20.5 Scheduled monitoring

- durable schedules;
- timezone-aware execution;
- owner/org scope;
- next-run calculation;
- pause/resume/delete;
- missed-run policy;
- concurrency/idempotency;
- cost/quota controls;
- notification linkage;
- no browser-dependent scheduler.

## 20.6 Usage metering and plans

Distinguish:

- network rate limits;
- daily product quotas;
- billable usage events;
- hard plan entitlements.

Plans may define:

- analyses;
- simulations/options;
- saved resources;
- organizations/members;
- document/storage capacity;
- job concurrency;
- notification channels;
- retention duration;
- model/provider access.

Entitlements are server-owned and versioned.

## 20.7 Billing foundation

Requirements before accepting payment:

- selected provider and webhook verification;
- customer/subscription mapping;
- idempotent event processing;
- entitlement state machine;
- trial/cancel/past-due/grace behavior;
- invoice/customer portal links;
- no client-controlled plan upgrade;
- audit billing changes;
- tax/legal review appropriate to markets;
- refund/support policy;
- sandbox and production separation.

A UI plan label without verified billing webhooks is not billing completion.

## 20.8 Organization commercial workflows

- invitations with expiration and acceptance;
- seat/member limits;
- organization ownership transfer;
- organization export/deletion;
- plan owner/billing contact;
- audit export;
- workspace settings;
- role administration;
- support impersonation prohibited or strictly controlled/audited.

## 20.9 Customer-facing operations

- public status page;
- support contact/workflow;
- feedback submission;
- issue severity and response targets;
- data/privacy requests;
- abuse reporting;
- onboarding/help content;
- release notes.

## 20.10 Legal and privacy readiness

Requires qualified review of:

- terms;
- privacy policy;
- cookies/analytics consent;
- subprocessors;
- retention/deletion;
- financial-research disclaimers;
- acceptable use;
- jurisdiction and dispute terms;
- billing/refund rules;
- data processing agreements where needed.

Documentation must state that internal drafting is not legal certification.

## 20.11 Testing

- analytics consent and opt-out;
- no sensitive payload leakage;
- notification preferences;
- webhook signature/replay;
- delivery retry/dead-letter;
- schedule timezone/missed run;
- entitlement enforcement;
- billing webhook idempotency/order variation;
- cancellation/grace behavior;
- organization seat limits;
- export/deletion with analytics and billing references;
- status/support flows.

## 20.12 Completion gates

- analytics taxonomy and retention approved;
- privacy controls work;
- scheduled monitoring uses durable jobs;
- notification preferences and delivery work;
- webhook security works;
- usage metering reconciles with quotas;
- billing sandbox end-to-end passes;
- plan entitlements cannot be client-forged;
- organization invitations and seat controls work;
- status/support/privacy request processes exist;
- legal/commercial review completed before paid launch.

---

# V1 Phase 21 — Model and Research Intelligence Expansion

Status: **Planned**

## 21.1 Goal

Expand model-assisted research, provider selection, evaluation, thesis tracking, catalysts, and scenario intelligence without weakening deterministic truth, source provenance, tenant isolation, cost controls, or human oversight.

## 21.2 Provider routing

Provider selection is explicit by task, for example:

```text
strategy parsing
report synthesis
source classification
retrieval reranking
entity extraction
scenario explanation
research summarization
```

Routing considers:

- task capability;
- evaluation score;
- latency;
- cost;
- privacy/data policy;
- tenant plan;
- provider availability;
- local/cloud preference.

No provider is promoted solely because it produces persuasive prose.

## 21.3 Model registry

Track:

```text
provider
model
version
endpoint class
supported tasks
privacy classification
max context
cost metadata
evaluation status
promotion status
created_at
retired_at
```

Prompt and schema versions are stored separately and linked to outputs.

## 21.4 Evaluation-before-promotion

Each task has:

- regression dataset;
- deterministic validation rules;
- human-scored subset where necessary;
- baseline provider;
- candidate provider;
- promotion thresholds;
- rollback conditions.

Metrics may include:

- structured-output validity;
- factual/source consistency;
- deterministic-field preservation;
- missing-data honesty;
- citation support;
- task accuracy;
- latency;
- cost;
- unsafe recommendation rate;
- tenant leakage rate.

## 21.5 Output quality and provenance

Every model-assisted artifact records:

- provider/model version;
- prompt version;
- retrieval/source set;
- deterministic inputs;
- structured validation outcome;
- fallback path;
- latency/cost;
- human feedback when available.

Model output cannot overwrite deterministic risk values, market facts, sources, missing data, or disclaimers without a separately validated deterministic update.

## 21.6 Prompt injection and source safety

- treat retrieved content as untrusted data;
- isolate system instructions from source text;
- detect or flag instruction-like source content;
- constrain tool calls and outputs;
- require schema validation;
- preserve source attribution;
- never expose secrets to model prompts;
- tenant content stays within approved provider/data policies.

## 21.7 Human feedback

Capture bounded feedback such as:

- helpful/not helpful;
- incorrect claim;
- missing source;
- bad citation;
- unclear explanation;
- incorrect protocol/entity;
- unsafe recommendation language.

Feedback does not become training data automatically. Consent, privacy, quality review, and dataset versioning are required.

## 21.8 Research intelligence

Potential features:

- thesis status tracking;
- catalyst calendar;
- assumption changes;
- report-to-report comparison;
- source-change detection;
- scenario comparison;
- protocol/market coverage expansion;
- source-quality scoring;
- stale-thesis detection;
- monitoring question generation.

These features remain research tools and do not execute trades.

## 21.9 Safe ephemeral GPU execution

Runs through Phase 17 workers with:

- approved images/models;
- bounded resources;
- cost limits;
- no arbitrary user image;
- no inbound public service requirement;
- health validation;
- artifact isolation;
- automatic cleanup;
- audit and evaluation.

## 21.10 Fine-tuning and training

Before training:

- dataset purpose and provenance documented;
- deterministic labels distinguished from human labels;
- private tenant data excluded unless explicit policy/consent exists;
- train/validation/test split versioned;
- leakage and duplication checks;
- baseline comparison;
- rollback path;
- model card and limitations.

Fine-tuned outputs remain advisory unless deterministic validation independently supports the result.

## 21.11 Testing

- provider failure/fallback;
- prompt/schema version regression;
- deterministic-field preservation;
- unsupported claim/citation tests;
- prompt-injection dataset;
- source poisoning tests;
- tenant isolation;
- cost/latency budgets;
- provider promotion/rollback;
- feedback privacy;
- model registry permissions;
- ephemeral GPU cleanup;
- no trade recommendation/execution regression.

## 21.12 Completion gates

- task-level provider routing exists;
- model registry and prompt versions are durable;
- evaluation gates promotion;
- regression datasets run automatically;
- source/citation consistency is measured;
- deterministic fields remain authoritative;
- provider privacy and tenant policy are enforced;
- feedback is controlled and versioned;
- ephemeral compute uses workers and cost controls;
- new intelligence features preserve non-execution boundaries;
- rollback works.

---

# Cross-phase definition of done

Every future phase is complete only when:

1. the implementation matches the relevant contract;
2. migrations upgrade existing production-like data without destructive reset;
3. normal, failure, authorization, concurrency, and recovery paths are tested;
4. PostgreSQL-specific behavior is tested where relevant;
5. frontend type/build and browser tests pass;
6. Docker and deployment configuration validate;
7. secrets and private data are not exposed;
8. public demo and deterministic-risk boundaries do not regress;
9. observability and runbooks appropriate to the phase exist;
10. documentation and `current_state.md` match reality;
11. external/manual verification is recorded;
12. known limitations are explicit;
13. CI is green;
14. the phase is not marked complete merely because scaffolding or placeholder UI exists.

---

# Short prompt examples

After these contracts are committed, a future Codex prompt may be as short as:

```text
Implement V1 Phase 17 on a new branch from current main.
Read docs/development_plan.md, docs/current_state.md,
docs/future_phase_contracts.md, docs/architecture.md,
docs/deployment.md, docs/testing.md, and docs/agent_execution_guide.md.
Follow the Phase 17 contract exactly, preserve completed behavior,
run all required checks, update the docs, commit logically, and do not merge.
```

For a correction pass:

```text
Audit the current Phase 18 branch against the complete Phase 18 contract in
docs/future_phase_contracts.md. Fix every blocker, run the required validation,
update current-state documentation, commit the changes, and do not merge.
```
