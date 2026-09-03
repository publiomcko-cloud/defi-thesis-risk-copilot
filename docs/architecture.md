# Architecture — DeFi Thesis & Risk Copilot

This document defines the system architecture and permanent trust boundaries. Phase-specific requirements live in:

- [`archive/v1_phase_16/phase_16_identity_ownership_contract.md`](archive/v1_phase_16/phase_16_identity_ownership_contract.md)
- [`archive/v1_phase_17/`](archive/v1_phase_17/)
- [`archive/v1_phase_18/`](archive/v1_phase_18/)
- [`phase_19_execution_plan.md`](phase_19_execution_plan.md)
- [`phase_20_execution_plan.md`](phase_20_execution_plan.md)
- [`future_phase_contracts.md`](future_phase_contracts.md)
- [`current_state.md`](current_state.md)

---

## 1. Architecture goals

The system is designed for:

- deterministic, explainable risk analysis;
- source-grounded research and citation provenance;
- visible missing data and uncertainty;
- optional model assistance after retrieval and scoring;
- human approval before new knowledge becomes trusted;
- secure identity, ownership, and tenant isolation;
- server-side credentials and cookies;
- safe anonymous public-demo access;
- durable asynchronous work and storage in later phases;
- incremental deployment from portfolio demo to commercial product.

---

## 2. Permanent boundaries

The application must not implicitly:

- connect wallets;
- request private keys or seed phrases;
- sign transactions;
- custody assets;
- execute trades;
- allocate capital;
- promise returns;
- provide personalized financial advice;
- hide missing data;
- auto-trust discovered sources;
- expose credentials or session secrets;
- let model output replace deterministic risk fields.

---

## 3. Deployed V1 foundation

```text
Browser
  -> Vercel Next.js frontend
  -> Render FastAPI backend
  -> Supabase PostgreSQL

Render startup
  -> Alembic migrations
  -> deterministic public demo seed
  -> local curated RAG index build
  -> Uvicorn
```

The deployed `main` branch includes the Phase 15 public-safe baseline, Phase
16 identity/ownership, Phase 17 durable job control plane, Phase 18 durable
knowledge/retrieval implementation, and the Phase 19 operations/security
repository foundation. Phase 18's durable path remains feature-gated; local
JSON RAG remains the production fallback. Phase 19's centralized telemetry,
alert delivery, provider restore, secret rotation, protected-branch, and
controlled deployment evidence remains external.

Phase 19A adds a local-only operational correlation path:

```text
browser correlation ID
  -> Next.js BFF normalized header
  -> FastAPI request context and redacted JSON log
  -> server-owned durable job context
  -> outbound worker control-plane header and executor context
```

This is not an external telemetry exporter. Operational logs remain redacted,
and the admin-only readiness surface returns aggregate booleans only.

Live endpoints:

- frontend: `https://defi-thesis-risk-copilot.vercel.app`;
- backend: `https://defi-thesis-risk-copilot.onrender.com`;
- liveness: `/health`;
- readiness: `/ready`;
- safe deployment status: `/api/deployment/status`;
- OpenAPI: `/docs`.

---

## 4. Phase 16 implemented identity architecture

```text
Browser
  -> Vercel Next.js application
     -> /api/auth/* server route handlers
     -> /api/backend/* BFF
     -> HttpOnly access/refresh/expiry cookies
     -> HttpOnly anonymous-session cookie
  -> Render FastAPI API
     -> Supabase JWKS token verification
     -> application user synchronization
     -> actor and authorization policies
     -> owned/organization/anonymous resources
     -> durable quota records
  -> Supabase PostgreSQL
```

### Trust boundary

- Browser JavaScript never receives access or refresh tokens.
- Next.js owns browser session cookies and server-side token refresh.
- FastAPI verifies access tokens independently.
- Supabase claims establish identity only.
- Application database fields establish platform role, account status, plan, ownership, and organization membership.
- Resource policies derive tenant scope server-side.
- Organization knowledge metadata is database-owned and membership-scoped, but tenant documents and vectors are not stored in Phase 16.

### Ownership persistence integrity

Phase 16C adds database foreign keys for resource owner, organization, and anonymous-session links, plus saved-thesis owner and consent-user records. Nullable resource links use `SET NULL`; required saved-thesis/consent links use `RESTRICT`. Compound indexes support owner/deleted, organization/visibility/deleted, anonymous/expires, membership, and quota-period access paths. Polymorphic quota subjects and immutable audit actors intentionally remain application-managed references; the Phase 16 contract records why.

When authentication is disabled outside the public demo, the local `demo_admin` context is materialized as a database user before it can create owned resources. This prevents development-only convenience identities from bypassing the same foreign-key integrity expected in PostgreSQL production-like validation.

### Lifecycle audit boundary

The application records bounded audit events for privileged and lifecycle operations. Metadata is recursively redacted and size-limited before persistence; emails, tokens, cookies, credentials, verification codes, and raw request bodies are never retained. Only administrators can query the full operational log. Account export exposes a user-visible projection without internal metadata. Successful Next.js MFA route handlers may report fixed event types to FastAPI only through a server-only BFF shared secret and authenticated user token; the secret is not browser-visible.

### BFF boundary

The BFF must:

- use explicit route-family allowlisting;
- reject arbitrary hosts, schemes, ports, paths, and path traversal;
- forward only safe headers;
- attach the access token through `Authorization`;
- forward only backend-required cookies, such as the anonymous session;
- never forward refresh-token cookies to Render;
- propagate anonymous-session cookies safely;
- clear auth cookies after refresh failure.

The current Phase 16 branch contains the BFF foundation with explicit backend route-family allowlisting and anonymous-cookie-only backend forwarding. Full deployed browser refresh/logout verification remains a completion gate documented in the Phase 16 contract.

---

## 5. Product domains

```text
Next.js frontend/BFF
  -> landing and guided demo
  -> authentication and session management
  -> account/security
  -> strategy analysis
  -> reports/export
  -> simulator/options
  -> theses
  -> organizations/memberships
  -> watchlists/alerts
  -> notifications/preferences
  -> discovery/review/admin tools

FastAPI control plane
  -> request validation
  -> identity synchronization
  -> actor/authorization policies
  -> analysis orchestration
  -> deterministic risk scoring
  -> market data/cache
  -> report persistence
  -> simulation/options
  -> organizations/theses/watchlists/alerts
  -> server-owned notification projections
  -> quotas/account/consent/retention
  -> discovery/evaluation/review
  -> knowledge ingestion
  -> credentials/audit/Vast controls

Persistence
  -> Supabase PostgreSQL hosted
  -> PostgreSQL/SQLite local
  -> curated Markdown sources
  -> local JSON RAG index in current phases
```

### Notification authority

In-app notifications are projections of existing server-side authorities, not a
new decision engine. The approved Phase 20D registry maps watchlist alert,
schedule occurrence, durable-job terminal, and account lifecycle events to
bounded categories, severities, templates, source types, and same-origin
navigation. Browser clients can list and mutate read/preference state only;
they cannot create notification intents, choose recipients, forge severity or
category, provide source identity, or grant access to linked resources.

---

## 6. Analysis architecture

```text
bounded strategy input
  -> strategy parsing
  -> protocol/entity detection
  -> approved retrieval
  -> market-data adapters/cache
  -> explicit unavailable/missing state
  -> deterministic risk scoring
  -> stress scenarios
  -> structured report
  -> optional LLM wording synthesis
  -> owned persistence
  -> authorized rendering/export
```

Authoritative fields include:

- risk rating and score;
- risk drivers;
- market values;
- assumptions;
- missing data;
- source metadata;
- disclaimer.

Model output may not silently override them.

---

## 7. Knowledge trust architecture

```text
discovery
  -> filtering/normalization
  -> stable-key deduplication
  -> deterministic evaluation
  -> human review
  -> approved_for_rag
  -> explicit authorized ingestion
  -> durable source/version in Phase 18
  -> retrieval index
```

Current global ingestion may generate curated Markdown and refresh the public-curated local index. Phase 18 adds a guarded durable path: authenticated analysis derives approved public, caller-owned private, and active-organization scope from its server-side actor, while anonymous analysis remains public-only. The local JSON index remains the default and rollback fallback until live storage-policy and cutover gates are completed.

No automatically discovered content becomes trusted without explicit approval.

---

## 8. Actor architecture

### Anonymous visitor

- reads public seeded content;
- runs bounded compute;
- owns temporary resources through a server-generated anonymous session;
- cannot run privileged mutations.

### Authenticated user

- owns private resources;
- uses quotas and account lifecycle;
- participates in organizations.

### Organization roles

```text
owner
admin
member
viewer
```

Organization access requires:

- active, non-deleted organization;
- active membership;
- allowed role;
- resource visibility equal to `organization`.

### Platform administrator

Uses explicit platform-admin routes. Organization role does not grant platform-admin access. Supabase metadata does not grant platform-admin access.

When configured, platform administrators require MFA assurance.

---

## 9. Resource visibility architecture

```text
private
organization
public_demo
```

### Private

Owner-only. A stale `organization_id` does not grant organization access.

### Organization

Requires active organization and membership. Client input cannot assign arbitrary organization scope.

### Public demo

Globally readable seeded/safe content. Public mutation remains blocked.

### Anonymous private

Requires matching active anonymous session and unexpired resource.

Every list and detail query must enforce the same policy. Export and mutation routes are not exceptions.

---

## 10. Public and authenticated coexistence

The desired product can support both anonymous and authenticated actors in one deployment.

Authorization is therefore actor-based:

```text
operation + actor + role + ownership + organization + visibility + state
```

It must not be reduced to:

```text
PUBLIC_DEMO_MODE=true -> block every mutation
```

A deployment-mode flag may enable anonymous demo behavior, but authenticated user and administrator capabilities still require explicit actor policies.

---

## 11. Identity and session architecture

### Managed identity

- Supabase Auth for credential and recovery flows;
- FastAPI JWKS verification;
- normalized local application user;
- database-owned roles and plans;
- collision-safe identity linking;
- verified email;
- optional/required MFA.

### Local development

`legacy_local` may support controlled development only. Production rejects it.

### Credentials

Provider credentials:

- remain server-side;
- use encrypted storage or environment configuration;
- never return raw values;
- are redacted from logs/audit metadata;
- require explicit platform-admin authorization.

---

## 12. Quota architecture

Two distinct concepts:

### Product quotas

Persistent per-period limits for analysis, simulation, options, market data, and saved-resource counts.

### Network rate limits

Request-frequency protection is distinct from persistent product quotas. Phase 19B provides a disabled-by-default PostgreSQL shared limiter with two fixed windows per action for burst and sustained protection. It derives IP scope from the direct peer unless that peer belongs to an explicit trusted-proxy CIDR, then combines it with an anonymous session or authenticated user scope. Durable job admission adds an organization scope only after server-side membership validation. The database stores salted HMAC scope hashes, never raw IP addresses or session identifiers. The legacy Phase 15 in-process public-demo limiter remains only as the documented rollback fallback while shared limiting is disabled.

Quota check/increment must be atomic. A row lock cannot protect a missing first-use row; PostgreSQL upsert or retry logic is required.

Phase 16E validates the controlled retry plus quota-row-lock design against PostgreSQL: concurrent first use yields a permitted request and a controlled `429` at the configured limit, while the same durable lock serializes saved-thesis and watchlist count checks. The test suite also verifies that soft deletion releases user resource capacity.

---

## 13. Account and retention architecture

Account lifecycle:

```text
active
  -> inactive/deletion requested
  -> deleted/disabled immediately
  -> retention cleanup
  -> identifiers deleted or anonymized
```

Required controls:

- exact confirmation;
- recent authentication where supported;
- final organization-owner protection;
- immediate access revocation;
- session clearing;
- bounded export;
- no secret export;
- deterministic cleanup/dry-run;
- explicit private-resource disposition;
- redacted audit retention.

---

## 14. Runtime reliability

Startup:

```text
alembic upgrade head
  -> scripts.prepare_runtime
  -> uvicorn
```

Health:

- `/health` — process liveness;
- `/ready` — database and required runtime resources;
- `/api/deployment/status` — safe UI metadata.

Request middleware provides request ID, method, path, status, duration, and `X-Request-ID` response header without logging secrets.

---

## 15. Market-data architecture

The cache:

- keys by adapter/query identity;
- updates current rows rather than appending indefinitely;
- removes duplicates;
- enforces expiration;
- uses only unexpired fallback data;
- returns explicit unavailable state when no valid data exists.

Market data may be delayed, partial, cached, simulated, or manually supplied and must be labeled accordingly.

---

## 16. Phase 17 implemented — jobs and workers

```text
API/control plane
  -> PostgreSQL job state
  -> local/cloud worker outbound claim
  -> lease/heartbeat/progress
  -> durable artifact/result
```

Key invariants:

- scoped worker auth;
- atomic claim;
- idempotency;
- retry/dead-letter;
- cancellation;
- cost/concurrency controls;
- no inbound local-worker ports.

See [`future_phase_contracts.md`](future_phase_contracts.md).

### Phase 17 implemented foundation

PostgreSQL now persists job, attempt, event, worker, worker-credential, and artifact metadata.
Job transitions are restricted to a closed service, events are append-only and sequenced, and
worker tokens use a separate hashed credential domain rather than a browser or user token. The
control plane now exposes authenticated, tenant-filtered job submission, list/detail, events,
cancellation, and admin linked replay. A unique scoped idempotency boundary and lockable capacity
reservation rows keep quota, user/organization/global/provider capacity, preallocated report IDs,
and the initial event transactional. The internal worker protocol now leases jobs with PostgreSQL
`SKIP LOCKED`, a monotonic lease generation, a hashed per-attempt token, durable attempt rows, and
bounded heartbeat/retry/cancellation recovery. It is excluded from the browser BFF. The optional
local worker is outbound-only. For `analysis.generate.v1`, it runs the existing deterministic
analysis workflow with the preallocated report ID and returns a bounded completion payload; the
control plane transactionally persists the linked report and analysis request. This trusted
co-located Compose profile receives the configured database and public-curated knowledge-base
mount; a remote worker must not receive general production database credentials without an explicit
least-privilege deployment design. `ASYNC_ANALYSIS_ENABLED` gates authenticated queue use, while
anonymous public analysis remains synchronous. The separate `vast.session.start.v1` executor is
available only through a dedicated platform-admin/MFA-gated endpoint, never through ordinary
analysis or the generic jobs API. It accepts no caller-selected model/image, preallocates and
uniquely links a `vast_sessions.source_job_id` resource before provider work, reserves the maximum
configured cost before claim, and reuses that session on a retry after a lost worker response.
Cancellation and terminal failure request idempotent cleanup. The fake/dry-run provider remains
the default; a trusted worker receives provider secrets from its runtime configuration, never from
the job envelope. Administrator aggregate operations show queue depth, active/stale workers,
dead letters, and provider cleanup failures. Real hosted/provider operation remains a manual
deployment concern and is not claimed as validated.
Authenticated users have a tenant-filtered `/jobs` workspace that polls active work and exposes
only safe status, progress, attempt, event, error, cancellation, and durable result-reference
data. Account export includes the corresponding safe job/event/artifact projection, never raw
inputs, event metadata, worker credentials, or provider data. Account/organization deletion
disposes of terminal job resources, marks incomplete outputs honestly, and leaves running work to
the cancellation/lease-recovery path. Retention expires job events, terminal jobs with dependent
attempts/artifacts, credentials, and expired artifacts according to configured policy. Each claim
also records a fixed maximum lease horizon; execution supervision heartbeats and checks
cancellation while work is running, and it never submits progress or completion after lease loss.
Cancellation is cooperative and the local worker waits for the active executor to exit before
claiming another job. Daily provider cost is persisted as an auditable reservation ledger so active
reserved cost and completed actual spend remain distinct during recovery. Recovery dry-run does no
external provider I/O. Real Vast.ai rentals fail closed while the reconciliation profile is
`unverified`.
Membership and organization authorization changes are non-destructive and acquire `FOR UPDATE`
locks on affected active job rows before committing the membership or organization mutation:
queued/retry jobs fail with `authorization_revoked`, leased/running jobs become
`cancel_requested`, and terminal organization reports/artifacts remain intact. Recovery
reconstructs missing global, provider, user, and organization capacity rows from durable jobs;
the rebuilt global row restores the active budget period and aggregates completed provider spend
from the durable ledger. Terminal provider accounting releases only work with
no provider request, records known resource cost, and retains a conservative reservation for an
uncertain provider outcome.
Only the central registry accepts the exact `analysis.generate.v1` and
`vast.session.start.v1` input/result schemas. Successful analysis completion creates an
`available` database-backed report-reference artifact; binary outputs remain incomplete until
Phase 18 object storage. Provider startup persists a server-owned request identifier before the
outbound call and blocks a second rental until an uncertain outcome is reconciled.

---

## 17. Phase 18 implemented foundation — durable RAG/storage

```text
approved source/upload
  -> object storage
  -> versioned document
  -> ingestion job
  -> durable chunks/embeddings
  -> tenant-filtered vector retrieval
  -> citation lineage
```

Runtime filesystem and global JSON indexes stop being authoritative.

Phase 18A is complete and additive. `knowledge_sources`, `knowledge_documents`,
`knowledge_document_versions`, and `knowledge_chunks` preserve immutable
lineage without changing the current RAG tables. Public, private, and
organization access predicates derive owner and active membership scope on the
server; a platform administrator has no organization-content bypass.

The private-storage protocol has a deterministic lineage-based key builder,
create-only writes, bounded reads, idempotent deletion, a memory test backend,
and a fail-closed Supabase adapter. It is disabled by default.
`document.ingest.v1` has exact input/result schemas, a server-owned submission
path, and a feature-gated Phase 17 worker executor. It validates private object
metadata/checksums, supports bounded text/Markdown, HTML, and PDF extraction,
persists incomplete chunks, and atomically activates only a validated approved
version. The current public JSON path remains active retrieval and rollback
authority until controlled deployment evidence supports a guarded cutover. See
the [archived Phase 18 record](archive/v1_phase_18/).
Phase 18B is merged into `main`: authenticated source/document APIs derive scope
and object lineage server-side, accept only bounded allowlisted uploads, record
approval/upload audit events, and compensate a written object if the database
commit fails. Responses never expose a storage key or object URL. Account and
organization deletion tombstone knowledge descendants; physical object cleanup
remains a later retention slice. Phase 18C keeps storage and ingestion disabled
by default. Phase 18D adds local-only 384-dimension pgvector embedding profiles,
generations, and a PostgreSQL HNSW cosine index through a separate Phase 17
worker job. Incomplete vectors never activate, external embedding providers are
rejected. Phase 18E adds an authenticated, disabled-by-default pgvector shadow
retriever. It applies source approval, lifecycle, current-version, exact active
embedding-generation, and server-derived tenant filters before ranking, records
only privacy-safe retrieval telemetry, and returns checksum-bound citations.
When the separately guarded primary flag is enabled, authenticated analysis uses
the same server-derived public/private/organization boundary; anonymous analysis
remains public-only and curated JSON remains the rollback fallback.
Phase 18F adds immutable-version rollback, manager-scoped embedding-generation
selection, and a two-stage deletion lifecycle. Database tombstones revoke
durable retrieval before a bounded, retryable cleanup script deletes private
objects and derived chunks/vectors; historical retrieval event identifiers are
retained only as non-serving audit lineage.

Phase 18G adds an operator-only importer for the repository's curated Markdown
corpus. It creates approved public immutable source/document/version/chunk/
embedding lineage, repairs deterministic partial state on rerun, never imports
discovered or tenant material, and is disabled by default. It verifies
checksum-free Supabase object metadata by bounded authenticated read, compensates
every object created by a failed whole-corpus attempt, and fails closed on an
unsafe deterministic-ID collision. The guarded report
retriever derives tenant scope only from the actor and falls back to the local
JSON index on an empty or unavailable durable result. Scheduled evaluation
compares the durable corpus against the existing JSON fallback using declared
immutable chunk/source relevance and an expected-empty case before an operator
enables the primary flag.

Phase 18H adds an authenticated source/document/version workspace and preserves
exact durable source/document/version/chunk checksums in report-source data
when the guarded durable retriever is used. The workspace receives only
metadata; it never receives an object key, bucket path, or storage credential.
An administrator-only readiness endpoint exposes aggregate state and feature
flags without tenant content. A separate operator probe can make and delete one
synthetic object and confirms it is not publicly readable before activation.
Private account exports include only source/document/version metadata and never
include document content, embeddings, storage keys, or signed URLs.

---

## 18. Phase 19 implemented foundation — operations/security

Adds:

- distributed rate limiting;
- WAF/security headers/CSRF/SSRF protections;
- centralized logs/errors/traces/metrics;
- request-job correlation;
- backups/restores;
- secret rotation;
- scanning;
- incident response;
- load/failure/browser/PostgreSQL testing.

Phase 19C is implemented as a feature-gated edge boundary: Next.js
emits a report-only CSP and minimum browser headers, FastAPI accepts exact CORS
origins and rejects browser mutations from other origins, and the BFF keeps a
fixed backend origin/path allowlist while rejecting redirects. Private source
storage remains disabled. When production storage is eventually enabled, an
operator-configured scanner must return `clean` before bytes reach storage;
scanner failure rejects the upload. JSON RAG remains the fallback and no
Phase 18 feature flag is activated by these controls.

Phase 19D adds a separate, administrator-only aggregate monitoring projection.
It reads durable job/worker state and privacy-safe retrieval events without
returning tenant, job, worker, query, source, or credential detail. Local alert
candidates remain inside the application and are not pager delivery. The
synthetic runner can only use fixed health/readiness/demo paths until a later
operator-owned authenticated synthetic deployment is approved.

Phase 19E adds a separate metadata-only recovery-verification path. It derives
salted fingerprints from durable report/job/artifact/knowledge metadata but
never serializes content, object keys, checksums, identities, or credentials.
An external provider remains responsible for encrypted database/object backup
and restore. The optional retention guard requires a server-side recovery
evidence identifier before destructive cleanup; it does not alter default
Phase 17 cleanup or job recovery behavior.

Phase 19F keeps build-pipeline trust separate from runtime trust. GitHub Actions
use immutable action revisions and least-privilege permissions; a standard
library policy utility validates workflow and lockfile invariants before project
dependencies are installed. Its SBOM is derived only from pinned Python/npm
metadata, never runtime configuration or secrets. Dependency/secret/SAST and
container-image scans operate in CI without deployment credentials. GitHub
ruleset and security-provider configuration remain an external control-plane
boundary.

Phase 19G makes operational response explicit without adding a runtime incident
or paging service. Existing aggregate monitoring alerts retain stable runbook
IDs; the versioned incident registry maps them to containment, recovery,
communication, evidence, and retrospective procedures. Incident records,
on-call names, pager routes, raw logs, customer data, credentials, and forensic
artifacts remain in approved private operational systems rather than the
application database, browser, or repository. The registry and tabletop scripts
are structural local evidence only; named owners and exercised-response evidence
are required before deployment-complete claims.

Phase 19H adds no production workload path. A backend-only, fixed-command
exercise runner validates its own explicit isolated-environment gate before
spawning known test commands. It forces child test processes into a non-provider
exercise context, caps their timeout, reports no child output, and persists no
exercise state. The scheduled workflow uses an ephemeral pgvector service with
no deployment/provider credentials. It verifies existing failure handling and
semantic browser contracts; it is not a production capacity, provider, pager,
or full accessibility certification system.

Phase 19I adds a read-only rollout-readiness boundary around the existing
durable-RAG controls. It checks only safe booleans: database/pgvector and JSON
fallback availability, explicitly enabled storage/ingestion/worker/embedding/
shadow dependencies, and dry-run provider posture. It neither mutates a
feature flag nor touches tenant content. The production configuration rejects
the pgvector-primary flag; an actual primary report-path check is possible only
in an explicitly isolated non-production environment. Private bucket/RLS,
synthetic identities, worker execution, report/citation comparison, alerting,
and rollback records remain external operational evidence.

---

## 19. Phase 20 portfolio profile completion

The ordered record is [`phase_20_execution_plan.md`](phase_20_execution_plan.md)
and the final audit is [`phase_20_closeout.md`](phase_20_closeout.md). Phase 20
is **Complete — Portfolio Profile** on validated implementation/evidence head
`4b09071623bc686c1e623cbf383eb198b3c89412`; PR #31 remains DRAFT and
unmerged. Slices 20A–20I are complete and merged. They add privacy-conscious analytics, durable
scheduling, in-app notifications, shadow entitlements/non-billable usage,
organization invitations/seats, and first-party support/status/privacy
operations. External delivery and billing remain unimplemented; productization
and qualified review remain deferred rather than completed.

Phase 20A defines the shared design boundary. Phase 20B implements its first
runtime slice:

- Phase 16 `consent_records` remains terms/privacy acceptance authority;
- granular optional analytics decisions use separate immutable
  `privacy_preference_decisions` evidence and a rebuildable
  `privacy_preferences` current projection;
- four code-owned events may enter `product_analytics_events` only after an
  authenticated user's exact current policy opt-in; ownership and source
  deduplication inputs are server-derived and never analytics dimensions;
- decision and event paths serialize on the owning PostgreSQL user row so a
  withdrawal cannot race an event into storage afterward;
- withdrawal and account deletion immediately remove optional events, while
  the shared cleanup authority expires events at 30 days and decision evidence
  30 days after account deletion;
- optional emitter commits occur after the product transaction and fail closed
  without rolling back a successful report, thesis, or watchlist action;
- existing account export/deletion, organization deletion, retention cleanup,
  audit, quota, and job lifecycle remain authoritative;
- proposed Phase 20 rows must register projections/lifecycle hooks rather than
  create a second account or organization lifecycle;
- network rate limits, product quotas, billable usage, entitlements, analytics,
  audit, billing, and support remain separate domains;
- no analytics provider or browser SDK is selected; collection is disabled by
  default and production activation is blocked by configuration validation.

The Phase 20 trust and data-model records are
[`phase_20_threat_model.md`](phase_20_threat_model.md) and
[`phase_20_data_model_review.md`](phase_20_data_model_review.md). The approval
boundary is
[`decisions/phase_20b_analytics_approval.md`](decisions/phase_20b_analytics_approval.md).
Qualified privacy/legal review remains blocked for production activation.

Phase 20C adds a separate durable monitoring domain without changing Phase 16
ownership or Phase 17 job authority. `monitoring_schedules` is a private
user-owned projection limited to the code-owned `watchlist.evaluate` target;
`monitoring_schedule_occurrences` records a unique `(schedule_id,
scheduled_for)` execution identity and optional Phase 17 job link. The
dispatcher derives all timing, owner, target, job input, quota/capacity and
zero-cost deterministic execution context on the server. Schedule routes fail
closed when deployment authentication is disabled and never fall back to the
public/demo identity. It locks the owner
before the schedule, uses PostgreSQL `SKIP LOCKED` for concurrent dispatchers,
and commits each occurrence/job claim together. It reserves a fixed,
server-owned, non-billable 120-per-user UTC-day quota for each newly created
scheduled durable job; retries and recovery reuse that reservation. A
worker-side evaluator can mark an occurrence running but cannot mark it
successfully complete: the authoritative Phase 17 `complete_job()` transaction
transitions the job and occurrence together. A paused/deleted schedule cancels
or requests cancellation of its pending work, while a worker rechecks owner,
schedule and target before evaluation. Daily/weekly cadence retains the
selected IANA wall-clock intent across DST; hourly/six-hourly cadence uses
elapsed UTC intervals. The local JSON RAG fallback, tenant boundaries and real
Vast.ai disabled posture are unchanged. Dispatch remains feature-gated and
production-disabled; the scheduler is an outbound process, never a browser or
web-request timer.

---

## 20. Phase 21 target — model/research expansion

Adds task-level provider routing, model/prompt registry, evaluation-before-promotion, regression datasets, prompt-injection defenses, controlled feedback, thesis/catalyst tracking, and worker-controlled ephemeral GPU tasks.

Deterministic risk and non-execution boundaries remain permanent.
