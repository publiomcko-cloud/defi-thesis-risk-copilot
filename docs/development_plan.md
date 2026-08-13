# DeFi Thesis & Risk Copilot — Authoritative Development Plan

This document is the authoritative roadmap, phase-status index, and dependency map for DeFi Thesis & Risk Copilot.

Detailed implementation requirements live in:

- [`archive/v1_phase_16/phase_16_identity_ownership_contract.md`](archive/v1_phase_16/phase_16_identity_ownership_contract.md) — archived Phase 16 implementation contract and evidence;
- [`archive/v1_phase_16/phase_16_execution_plan.md`](archive/v1_phase_16/phase_16_execution_plan.md) — archived Phase 16 execution record;
- [`future_phase_contracts.md`](future_phase_contracts.md) — complete Phase 17–22 contracts;
- [`archive/v1_phase_17/`](archive/v1_phase_17/) — archived Phase 17 plan,
  corrections, and validation evidence;
- [`archive/v1_phase_18/`](archive/v1_phase_18/) — archived Phase 18 slices,
  gates, validation, migration, deployment, and rollback evidence;
- [`phase_19_execution_plan.md`](phase_19_execution_plan.md) — merged Phase 19
  operations/security foundation and external rollout gates;
- [`phase_20_execution_plan.md`](phase_20_execution_plan.md) — active
  implementation sequence;
- [`agent_execution_guide.md`](agent_execution_guide.md) — how future agents use short prompts safely;
- [`current_state.md`](current_state.md) — what the repository and deployed product actually implement now.

The former `post_mvp_development_plan.md` and `phase_10_12_expansion_plan.md` are historical. Git history preserves their original detailed prompts.

---

## 1. Product mission

DeFi Thesis & Risk Copilot converts a DeFi strategy or market thesis into a structured, source-grounded risk report.

The product should:

1. accept a bounded strategy description;
2. identify protocols, markets, and assumptions;
3. retrieve approved protocol and internal research context;
4. collect public or manually supplied market data;
5. show missing data and uncertainty;
6. calculate deterministic risk drivers and ratings;
7. run transparent stress scenarios;
8. produce a structured report with source provenance;
9. maintain saved theses, reports, watchlists, alerts, and organizations;
10. preserve human approval before new knowledge becomes trusted;
11. support optional model assistance without replacing deterministic truth.

The product does not connect wallets, request private keys, sign transactions, custody funds, execute trades, allocate capital, guarantee returns, or provide personalized financial advice.

---

## 2. Permanent engineering principles

- Deterministic calculations and risk fields remain authoritative.
- LLM output may improve wording but cannot invent or overwrite deterministic values, market facts, sources, missing data, or disclaimers.
- Missing data and uncertainty remain visible.
- Every trusted knowledge source preserves provenance and approval lineage.
- Discovery, evaluation, approval, ingestion, and retrieval are separate states.
- Provider credentials and session secrets remain server-side.
- Public deployments are safe by default.
- Authentication establishes identity; application data establishes roles, ownership, plan, and authorization.
- Resource identifiers never grant access by themselves.
- Tenant and organization filters are server-derived.
- Heavy work is bounded, durable, retryable, idempotent, and cost-controlled before commercial use.
- Every phase must document normal, failure, authorization, concurrency, deletion, and recovery behavior.
- Placeholder UI, mocked provider flows, or scaffolding are not completion.
- Documentation must distinguish implemented, tested, externally unverified, planned, and blocked work.

---

# Completed product history

## Phase 0 — Core technical MVP — Complete

Established:

- FastAPI backend;
- Next.js frontend;
- SQLAlchemy/Alembic persistence;
- Docker Compose stack;
- curated Markdown knowledge base;
- local retrieval;
- market-data adapter interfaces;
- deterministic risk scoring;
- structured report generation;
- Markdown export;
- backend and frontend validation foundations.

Core flow:

```text
strategy input
  -> parsing
  -> curated retrieval
  -> market data
  -> deterministic scoring
  -> stress scenarios
  -> report
  -> persistence/export
```

## Post-MVP Phase 1 — Optional backend LLM synthesis — Complete

- disabled deterministic fallback;
- Ollama provider;
- OpenAI-compatible provider;
- timeout and safe fallback;
- deterministic report fields remain authoritative.

## Post-MVP Phase 2 — Source monitoring and discovery — Complete

- source watches;
- manual/public discovery;
- normalized discovered items;
- deduplication;
- failure tracking;
- candidate listing.

## Post-MVP Phase 3 — Evaluation and review queue — Complete

- deterministic candidate evaluation;
- persisted evaluation results;
- review records and notes;
- confidence and missing data;
- review states: `needs_review`, `approved_for_rag`, `needs_more_data`, `rejected`, `archived`.

## Post-MVP Phase 4 — Strategy simulator — Complete

- net spread;
- borrow-rate shock;
- liquidity/slippage shock;
- collateral drawdown;
- early exit;
- incentive removal;
- combined adverse case.

## Post-MVP Phase 5 — Watchlists and alerts — Complete

- watchlist persistence;
- threshold rules;
- manually evaluated snapshots;
- in-app alert events;
- severity/status;
- no trade execution.

## Post-MVP Phase 6 — Options and volatility analysis — Complete

- long calls/puts;
- premium and contracts;
- breakeven and maximum loss;
- spread and expiration;
- payoff scenarios;
- return-on-premium and volatility framing.

## Post-MVP Phase 7 — Advanced RAG and retrieval evaluation — Complete

- heading-aware chunking;
- local deterministic embeddings;
- keyword/vector/metadata hybrid retrieval;
- reranking/citation foundations;
- retrieval evaluation scripts and dataset.

## Post-MVP Phase 8 — Fine-tuning and ML groundwork — Complete

- report-to-dataset export;
- deterministic labels separated from human ground truth;
- baseline classifier workspace;
- advisory model boundary.

## Post-MVP Phase 9 — HPC and SLURM readiness — Complete

- embedding-generation template;
- retrieval-evaluation template;
- classifier-training template;
- Apptainer definition;
- no HPC dependency for normal operation.

## Post-MVP Phase 10 — Auto-discovery and human-approved RAG ingestion — Complete

```text
discovery
  -> normalize/deduplicate
  -> evaluate
  -> human review
  -> approved_for_rag
  -> explicit admin ingestion
  -> curated Markdown
  -> RAG refresh
```

Automatic discovery/evaluation is allowed. Automatic trust/ingestion is not.

## Post-MVP Phase 11 — Access control and provider configuration — Complete for MVP

- `admin` and `common` roles;
- server-side encrypted credential storage;
- safe credential metadata;
- redacted audit events;
- administrator protection for credentials, review, ingestion, and Vast operations;
- bearer-token local/private foundation.

Production managed identity is superseded by the Phase 16 contract.

## Post-MVP Phase 12 — Vast.ai ephemeral provider — Complete for dry-run/manual warm-up

- offer filtering;
- cost/runtime/GPU controls;
- startup polling and health checks;
- test request path;
- cleanup and idempotent destroy;
- disabled/dry-run defaults;
- no live rental in CI or ordinary public reports.

## Final Phase 13 — Demo data and reports — Complete

- deterministic seed;
- Pendle/Morpho report;
- discovery-to-RAG report;
- watchlist report;
- options report;
- Vast dry-run report;
- `/demo` dashboard;
- committed Markdown examples.

## Final Phase 14 — Public portfolio deployment — Complete

```text
Vercel frontend
  -> Render FastAPI
  -> Supabase PostgreSQL
```

- public demo deployed;
- startup migrations and seed;
- safe deployment metadata;
- deterministic/LLM-disabled defaults;
- no durable reliance on generated runtime report files.

## V1 Phase 15 — Product hardening and public-safe UX — Complete

Backend/security:

- public visitor no longer receives implicit administrator identity;
- privileged public mutations blocked;
- bounded public compute rate-limited;
- request size/range limits;
- request IDs and safe error handling;
- `/health`, `/ready`, and safe deployment status;
- runtime demo/RAG preparation;
- market cache expiration and update-in-place behavior.

Frontend/UX:

- guided demo as primary entry;
- public admin navigation hidden;
- read-only public review/watchlist;
- cold-start and retry states;
- unit clarity;
- source links;
- Markdown copy/download;
- responsive/focus/reduced-motion improvements;
- shared-demo privacy warning.

Phase 15 is the permanent public-safety baseline for all later phases.

---

# Completed V1 implementation

## V1 Phase 16 — Production identity, ownership, and quotas — Complete

Goal: support anonymous visitors and authenticated multi-user/organization workflows securely in the same product architecture.

The detailed implementation contract, sub-phase record, and deployed-preview evidence are archived for traceability:

- [`archive/v1_phase_16/phase_16_identity_ownership_contract.md`](archive/v1_phase_16/phase_16_identity_ownership_contract.md)
- [`archive/v1_phase_16/phase_16_execution_plan.md`](archive/v1_phase_16/phase_16_execution_plan.md)
- [`archive/v1_phase_16/phase_16_deployed_verification.md`](archive/v1_phase_16/phase_16_deployed_verification.md)

Implemented foundation includes:

- Supabase JWT/JWKS verification;
- verified-email checks;
- local user synchronization and database-owned platform roles;
- HttpOnly access/refresh session-cookie and Next.js BFF foundation with explicit route-family allowlisting and anonymous-cookie-only backend forwarding;
- anonymous session records and expiring anonymous reports;
- organizations, memberships, pending invitations, and final-owner protection;
- ownership fields and centralized policy helpers with strict private/organization visibility semantics;
- saved theses;
- daily compute quotas and saved-resource quotas with controlled first-use retry/resource-lock foundations;
- account export/deletion and retention cleanup;
- terms/privacy pages and server-owned consent-record foundation;
- administrator `aal2` enforcement plus a locally tested TOTP enrollment, challenge/verification, and factor-management workflow;
- organization knowledge-source metadata with active-membership authorization and a server-derived public-only retrieval boundary;
- account/thesis/organization frontend components;
- expanded Phase 16 tests.

The implementation, migration, automated browser, PostgreSQL, Compose, CI, and hosted anonymous-isolation work is complete. The remaining external provider and legal release validation is deliberately deferred to the final V1 Phase 22. This preserves the implementation boundary while preventing an unsupported production-launch claim.

Execution sequence:

```text
16A Admin MFA usable workflow — complete on main
16B Organization knowledge metadata and retrieval boundary — complete on main
16C Migration, foreign-key, and index review — complete on main
16D Audit coverage and security event logging — complete on main
16E PostgreSQL concurrency and Phase 15 data validation — complete on main and in CI
16F Full browser E2E for Phase 16 workflows — complete on main and in CI
16G Hosted configuration and automated validation — complete; archived evidence records the remaining manual provider checks
16H Documentation and merge preparation — complete; final provider/legal launch approval moved to Phase 22
```

---

# Planned phases

The complete contracts are in [`future_phase_contracts.md`](future_phase_contracts.md).

## V1 Phase 17 — Durable job queue and hybrid workers — Complete

Goal: execute heavy/retryable/provider work outside the public web process.

Core outcomes:

- durable job state machine;
- scoped worker authentication;
- atomic leasing/heartbeat;
- retry, backoff, dead-letter;
- idempotency;
- cancellation/progress;
- local Docker worker with no inbound ports;
- Vast adapter through jobs;
- artifact records;
- concurrency and cost controls.

Phase 17 must preserve Phase 16 ownership, quotas, actor boundaries, and auditability.

V1 Phase 17 is complete on `main`. It provides durable job, attempt, event,
worker, credential, artifact, and capacity-reservation schemas; closed transitions; tenant-scoped
submission, idempotency, queue expiry, cancellation, and operator replay; PostgreSQL-safe worker
leasing/recovery; asynchronous authenticated analysis; a private jobs workspace; retention and
account export/deletion handling; and an outbound-only trusted worker. The administrator-only Vast
job uses server-owned settings, cost reservation, idempotent session linkage, and dry-run defaults.
CI uses fake/dry-run providers only. Real provider rentals and final hosted
operations validation remain Phase 22 gates and are not production claims.
Historical implementation and correction evidence is archived in
[`archive/v1_phase_17/`](archive/v1_phase_17/).

## V1 Phase 18 — Production RAG and knowledge storage — Complete on `main`

Goal: eliminate runtime-filesystem authority and support durable, versioned, tenant-filtered knowledge.

Core outcomes:

- object storage;
- durable document/version/chunk records;
- pgvector or justified vector store;
- server-derived tenant/protocol filters;
- worker ingestion;
- approved-source lineage;
- re-embedding migration;
- deletion/tombstones;
- rollback;
- retrieval observability and evaluation.

The ordered implementation, validation, correction, migration, and cutover
record is archived in [`archive/v1_phase_18/`](archive/v1_phase_18/). The first slice is
implemented additively: four durable knowledge tables, a private Supabase
Storage abstraction, server-derived tenant authorization, the exact but
feature-gated `document.ingest.v1` registry contract, authenticated
source/document APIs, bounded private-upload handling, audit events, lifecycle
tombstones, and the server-owned worker ingestion path.
The local JSON public retrieval path remains authoritative by default. Slices 18A–18H are
complete locally; source-scoped durable ingestion, local-only versioned pgvector
embeddings, and an authenticated tenant-safe shadow retriever are implemented
but disabled by default. Shadow retrieval records privacy-safe events and exact
citation lineage. The guarded primary report path derives approved public,
caller-owned private, and active-organization scope server-side for
authenticated users while anonymous analysis remains public-only; JSON stays
the fallback. Atomic version rollback, generation-specific same-profile
embedding promotion/rollback, and retryable tombstone cleanup are implemented.
Phase 18G supplies the convergent curated-corpus importer with whole-attempt
object compensation and fail-closed ID collision handling, declared-lineage
expected-empty evaluation/weekly CI evidence, and durable fallback behavior.
Phase 18H supplies the authenticated
source/document/version workspace, report citation lineage UI, safe readiness
metrics, private-knowledge export metadata, and the live storage verification
runbook. Phase 18 is merged into `main`, but its production features remain
feature-gated and JSON remains the fallback. Phase 19 may collect controlled
deployment evidence; final private-bucket policy verification, primary-path
activation, and launch approval remain Phase 22 gates.

## V1 Phase 19 — Production operations and security — Implemented Foundation

Goal: make identity, API, jobs, workers, storage, and retrieval hardened, observable, recoverable, and supportable.

The repository foundation is merged into `main`; the implementation and
external rollout authority remains
[`phase_19_execution_plan.md`](phase_19_execution_plan.md). Centralized
telemetry, alert delivery, provider restore drills, production secret rotation,
protected-branch enforcement, and controlled deployment evidence remain
external gates. Do not interpret the merged code as those gates being complete.

Phase 19A is implemented in the repository: structured/redacted logs, safe correlation
from browser through workers, and read-only readiness evidence. It has no
external telemetry exporter, dashboard, paging, or retention/access-policy
approval yet. The evidence matrix and threat model are
[`phase_19_evidence_matrix.md`](phase_19_evidence_matrix.md) and
[`phase_19_threat_model.md`](phase_19_threat_model.md).

Phase 19B is implemented in the repository: a disabled-by-default PostgreSQL shared
limiter protects bounded compute and durable-job admission with burst/sustained
windows, salted scope hashes, and shadow/enforce modes. Preview proxy-policy,
alert, and staged-enforcement evidence remain pending.

Phase 19C is implemented in the repository: explicit FastAPI CORS/browser-origin and
measured request-size controls for declared, chunked, and misleading-length
bodies, report-only CSP and baseline headers, BFF exact
origin/backend-target/redirect checks, and an opt-in required upload-scanner
contract. The scanner fails closed and production knowledge storage cannot be
enabled without it. WAF/bot policy, scanner/quarantine deployment, final origin
evidence, CSP reporting, and HSTS approval remain pending.

Phase 19D is implemented in the repository: an aggregate-only administrator monitoring
snapshot covers queue/worker/retrieval/provider and fallback state; local alert
candidates are deduplicated and have no delivery channel. The private operations
page and fixed-path synthetic CLI are disabled by default. Telemetry/pager/status
provider selection, dashboard RBAC, safe synthetic identity, alert escalation,
and SLO/error-budget evidence remain deployment work.

Phase 19E is implemented in the repository as a recovery-verification foundation: a
disabled metadata-only manifest tool compares salted durable metadata in an
isolated restore target, and an optional evidence guard can block destructive
retention cleanup. Provider database/object backup, encryption verification,
approved RPO/RTO, a provider restore drill, secret-store audit, emergency
rotation exercise, and encryption-key migration remain required before any
recovery claim.

Phase 19F is implemented in the repository: workflows use immutable action SHAs and
least-privilege permissions; repository policy checks reject mutable actions,
unsafe pull-request triggers, persisted checkout credentials, and unlocked
application manifests. CI generates a safe source-lockfile SBOM and adds
Dependency Review, Gitleaks, CodeQL, and Trivy repository/container scans;
Dependabot proposes weekly pip, npm, and action updates. The remediated
application manifests audit clean locally, and high/critical dependency,
container, and repository findings now fail CI. Suppressions require an
explicit owned, time-bounded registry entry. GitHub branch rules and first
hosted scan evidence remain deployment gates.

Phase 19G is implemented in the repository: versioned incident and security-operations
runbooks cover credential exposure, account takeover, tenant exposure,
malicious sources, queue duplication, provider cost, database/object-storage
outage, vector integrity, failed migration, and compromised workers. The
registry maps existing aggregate alert IDs to stable response procedures; a
structural check verifies required ownership, containment, recovery,
communications, evidence, and retrospective sections. Named human
primary/backup owners, a communication authority, an approved private evidence
location, alert delivery integration, and recorded tabletop exercises remain
deployment gates.

Phase 19H is implemented in the repository: a fail-closed fixed catalog runs only
isolated tests for rate-limit saturation, queue admission, worker loss,
fake-provider failure, storage outage, vector corruption recovery, migration
rollback, authorization negatives, database recovery, and semantic
accessibility. A scheduled no-secret pgvector workflow repeats the catalog and
uploads bounded safe exercise metrics only. It
refuses production, non-isolated operation, arbitrary commands, and real Vast
rentals. Production load/chaos, provider, customer-data, alert/pager, and full
assistive-technology evidence remain external gates.

Phase 19I is implemented in the repository: `check_controlled_rag_rollout` is a
read-only, explicit opt-in readiness validator for the narrow durable-RAG
deployment sequence. It verifies the shadow prerequisites, pgvector, JSON
fallback, worker/ingestion dependencies, and dry-run provider posture. A
primary-path check is limited to an isolated non-production environment, while
production configuration rejects `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=true`.
The real storage-policy/RLS probe, synthetic tenant and worker evidence,
durable-versus-JSON comparison, citation review, monitoring, and tested
rollback must be retained in the approved external evidence system.

Core outcomes:

- threat model;
- distributed rate limiting;
- WAF/security headers/CSRF/SSRF controls;
- centralized logs/errors/traces/metrics;
- request-to-job correlation;
- uptime checks/alerts;
- backup and restore drills;
- secret rotation;
- dependency/container/secret scanning;
- incident runbooks;
- PostgreSQL/browser/accessibility/load/failure tests.

## V1 Phase 20 — Analytics, notifications, and commercial readiness — In Progress

Goal: add privacy-conscious product analytics, scheduled monitoring, controlled notifications, plan entitlements, billing foundations, support, and legal launch readiness.

Phase 20 is active on its implementation branch. Its ordered, reviewable
subphases and gates are defined by
[`phase_20_execution_plan.md`](phase_20_execution_plan.md), subordinate to the
authoritative Phase 20 contract in
[`future_phase_contracts.md`](future_phase_contracts.md).

Phase 20A is an `Implemented Foundation`: it adds the Phase 20 threat/evidence
matrices, event-purpose/consent/retention taxonomy, machine-checkable event
examples, usage-unit/entitlement registry, notification classification,
provider ADR template/scorecards, and proposed `0023`–`0029` data-model review.
Phase 20B is locally implemented under the scoped project-owner decision in
[`decisions/phase_20b_analytics_approval.md`](decisions/phase_20b_analytics_approval.md).
It adds migration `0023`, explicit opt-in preferences, append-only decisions
and bounded events, preference API/UI, Phase 16 lifecycle integration, and
30-day cleanup. Analytics remains disabled by default and production activation
is `Blocked` pending qualified privacy/legal review. No external analytics
provider, browser SDK, notification send, payment, or production secret exists.

Phase 20C is locally complete after its original implementation and correction
hosted CI passes, with reversible migration `0024`. It supports
only authenticated user-owned, enabled private watchlist evaluation targets;
the browser selects neither arbitrary work nor dispatch timing. PostgreSQL
claims schedule occurrences through owner-first locking and `SKIP LOCKED`, then
atomically creates a server-derived Phase 17 `watchlist.evaluate` job. The
current implementation covers IANA/DST-safe cadence, at-most-one coalesced
replacement, over-24-hour missed-run recording, capacity/auth/target
revalidation, schedule lifecycle cancellation, 30-day history cleanup, export,
account deletion, operations aggregates, and `/schedules`. The correction
checkpoint makes Phase 17 control-plane completion the sole successful terminal
occurrence transition and reserves a fixed 120 scheduled evaluations per
authenticated user per UTC day without introducing billing or entitlements.
Automatic dispatch is default-off and production-rejected until a separately
approved rollout. PR #23 remains deliberately draft. Local preview requires an
outbound trusted worker and scheduler process.

Core outcomes:

- consent-aware analytics;
- durable private-watchlist scheduled jobs;
- email/webhook/Telegram preferences and delivery;
- usage metering and entitlement rules;
- billing webhook/idempotency foundation;
- organization invitations and seat controls;
- audit export;
- status/support/feedback workflows;
- qualified legal/privacy/commercial review.

## V1 Phase 21 — Model and research intelligence expansion — Planned

Goal: expand model-assisted research only after evaluation, provenance, privacy, cost, and rollback controls exist.

Core outcomes:

- task-level provider routing;
- model/prompt registry;
- evaluation-before-promotion;
- regression datasets;
- output/citation quality scoring;
- prompt-injection/source-poisoning defenses;
- controlled feedback;
- thesis/catalyst/scenario tracking;
- safe worker-based ephemeral GPU execution;
- fine-tuning dataset/model governance.

## V1 Phase 22 — Final release validation and launch approval — Planned

Goal: close the external validation and legal gates deferred from Phase 16 after the V1 implementation phases are complete. This phase adds no new end-user product capability.

Required outcomes:

- configure and validate reliable Supabase custom SMTP delivery;
- run deployed signup verification, recovery callback/password reset, authenticated-browser refresh/logout, and administrator MFA flows with disposable real accounts;
- confirm the deployed two-user ownership, organization membership-removal, and organization knowledge-metadata boundaries;
- record dated deployment evidence without credentials, tokens, mailbox contents, or personal data;
- obtain qualified review of the terms, privacy notice, retention language, and launch claims;
- rerun the full release regression, migration, browser, Compose, deployment, and documentation checks against the intended production configuration.

Phase 22 is complete only when every deferred provider and legal gate is evidenced, all release documentation is current, and the product can accurately be described as production-ready within its stated safety boundaries.

---

# Release gates

## Production v1 gate

The product may be labeled production v1 only when:

- Phase 16 identity/ownership implementation is merged and Phase 22 final release validation is complete;
- public and authenticated users coexist safely;
- private and organization data isolation is verified;
- anonymous data is isolated and cleaned;
- durable jobs/workers exist;
- RAG/artifacts use durable tenant-aware storage;
- rate limiting works across instances;
- observability, alerts, backups, security headers, and incident procedures exist;
- browser and PostgreSQL integration tests run in CI;
- legal/privacy copy has qualified review;
- no wallet/signing/custody/execution capability was introduced implicitly.

## Definition of done for every phase

A phase is complete only when:

1. the implementation matches its detailed contract;
2. code and migrations are committed;
3. normal, failure, authorization, concurrency, deletion, and recovery tests pass;
4. PostgreSQL-specific behavior is tested when relevant;
5. frontend type/build and browser tests pass;
6. Docker/deployment configuration validates;
7. secrets and tenant data remain protected;
8. Phase 15 public safety and deterministic-risk behavior do not regress;
9. operational evidence appropriate to the phase exists;
10. external/manual checks are recorded;
11. documentation matches reality;
12. known limitations are explicit;
13. CI is green;
14. the phase is not merely scaffolding, placeholder UI, or mocked external behavior.

---

# Short-prompt workflow

Future agents should use [`agent_execution_guide.md`](agent_execution_guide.md).

Standard phase prompt:

```text
Implement V1 Phase <N> on a new branch from current main.
Read docs/current_state.md, docs/development_plan.md,
the relevant phase contract, docs/architecture.md, docs/deployment.md,
docs/testing.md, and docs/agent_execution_guide.md.
Follow the contract exactly, preserve completed behavior, run all required
checks, update the docs, commit logically, push the branch, open a draft PR,
and do not merge.
```
