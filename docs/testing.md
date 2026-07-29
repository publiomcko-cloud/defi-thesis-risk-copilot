# Testing — DeFi Thesis & Risk Copilot

This file is the validation index. Detailed acceptance tests are defined in:

- [`archive/v1_phase_16/phase_16_identity_ownership_contract.md`](archive/v1_phase_16/phase_16_identity_ownership_contract.md)
- [`archive/v1_phase_17/`](archive/v1_phase_17/)
- [`archive/v1_phase_18/`](archive/v1_phase_18/)
- [`phase_19_execution_plan.md`](phase_19_execution_plan.md)
- [`phase_20_execution_plan.md`](phase_20_execution_plan.md)
- [`future_phase_contracts.md`](future_phase_contracts.md)
- [`agent_execution_guide.md`](agent_execution_guide.md)

No check may require production customer data, real paid infrastructure, or live capital execution.

## 1. Baseline commands

Backend:

```bash
cd backend
source .venv/bin/activate
python -m compileall app scripts
alembic upgrade head
python -m pytest -q
python scripts/run_smoke_checks.py
```

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm run build
npm run test:bff
npm run test:mfa
npm run test:mfa:routes
npm run test:e2e
```

Compose:

```bash
docker compose config
docker compose -f docker-compose.production.yml config
```

Report a command as passed only when it was executed successfully.

## 2. Migration validation

For schema-changing phases:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

Also validate PostgreSQL with existing prior-phase data, ownership backfills, constraints, indexes, and intentional deletion behavior.

## 3. Permanent Phase 15 regression suite

Every later phase preserves:

- public visitors never receive administrator access;
- public privileged mutations remain denied;
- bounded analysis, simulation, options, and market-data flows work;
- request limits and rate limits work;
- seeded reports and Markdown export work;
- deterministic risk fields and sources remain authoritative;
- cache expiration and unavailable states work;
- startup seed/RAG preparation remains idempotent;
- `/health`, `/ready`, and safe deployment status work;
- public review/watchlist UX remains read-only;
- no credentials or session material appear in responses or logs.

## 4. Phase 16 required suites

### Authentication and identity

Test valid and invalid JWTs, issuer/audience/expiration/signature, verified email, inactive/deleted accounts, identity collisions, pending invitations, refresh rotation, logout, and administrator MFA assurance.

### BFF and cookies

Test explicit route allowlisting, rejection of arbitrary targets, safe header forwarding, access-token attachment, refresh-cookie isolation, anonymous-cookie propagation, refresh success/failure, and browser storage absence.

### Anonymous isolation

```text
browser A creates and reads report
browser B receives 404
expired session receives 404
cleanup removes expired data
seeded public report remains
```

### Ownership

Test User A versus User B, strict private visibility, organization roles, removed members, disabled/deleted organizations, final-owner protection, and safe `404` behavior.

### Route authorization

Test monitoring, discovery, evaluation, review, document/RAG ingestion, credentials, audit, and Vast routes for anonymous, ordinary user, organization role, and platform administrator actors.

### Quotas

Test exact limit, exceeded limit, period reset, plan differences, saved-resource limits, deletion releasing capacity, and concurrent first-use behavior on PostgreSQL.

### Account lifecycle

Test bounded export, exclusion of foreign/sensitive data, deletion confirmation, final-owner blocking, immediate access revocation, dry-run cleanup, retention, consent versioning, and password recovery callback.

### Frontend E2E

Test anonymous demo, login/BFF/refresh/logout, account, private jobs workspace, thesis CRUD,
organizations/memberships, recovery, consent, MFA, mobile layout, keyboard focus, and no private-content flash.

A route-status smoke script is useful but is not full browser E2E coverage.

## 5. Completed Phase 16 coverage

Present:

- private report isolation;
- final owner protection;
- quota boundary;
- valid/invalid JWT cases;
- anonymous report isolation and expiration;
- strict private visibility with stale organization IDs;
- public-demo durable mutations blocked for anonymous visitors and allowed for authenticated hybrid users;
- watchlist resource limit;
- server-owned consent versions;
- retention anonymization/deletion;
- BFF allowlist/cookie-filter contract check;
- Supabase MFA provider adapter success/failure contract checks;
- same-origin MFA route-handler success/failure, cookie-rotation, cookie-isolation, and origin checks;
- administrator `aal1` denial, `aal2` allow, and ordinary-user `aal1` access;
- organization knowledge metadata owner/admin mutation and active-member read authorization;
- outsider, removed-member, disabled-organization, and non-member platform-admin knowledge denial;
- shared-index rejection of organization-tagged chunks under server-derived Phase 16 retrieval scope;
- migration evidence that seeded Phase 15 public reports/watchlists survive the Phase 16 upgrade, ownership/consent foreign keys and compound indexes exist, and downgrade/upgrade preserves the seed;
- PostgreSQL 16 upgrade/downgrade/upgrade validation from a seeded Phase 15 database for the Phase 16C migration;
- organization/membership lifecycle, final-owner-denial, account export/deletion, consent, and MFA audit-event coverage;
- audit metadata redaction and bounds, administrator-only audit access, and exclusion of internal audit metadata from account export;
- BFF MFA route-handler audit dispatch with a server-only shared audit secret;
- PostgreSQL first-use quota races, exact-limit `429` handling, saved-thesis/watchlist resource-count serialization, and deletion-release coverage when `RUN_POSTGRES_INTEGRATION=true`;
- migrated Phase 15 public report/watchlist API regression coverage, including anonymous public mutation denial;
- production-like Chromium browser E2E with local mocked Supabase/FastAPI upstreams: anonymous report isolation/expiry, BFF login/refresh/logout, recovery/reset, account export/deletion confirmation/consent, thesis CRUD/analyze, organization owner protection/member removal, MFA, no-private-content flash, and mobile keyboard/layout smoke;
- failure screenshots/traces and CI upload configuration for the browser suite.

Deferred to V1 Phase 22 final release validation:

- deployed recovery callback verification;
- deployed end-to-end Supabase MFA flow;
- full browser coverage for organization knowledge metadata controls;
- deployed Supabase verification.

Phase 16 implementation coverage is complete. Final deployed-provider and qualified legal validation is tracked in V1 Phase 22.

## 6. Phase 17 validation

Test atomic job claims, leases, heartbeat, abandoned recovery, retry/dead-letter, idempotency, cancellation, worker authentication, tenant isolation, graceful shutdown, and cost/concurrency limits.

Phase 17A additionally requires migration upgrade/downgrade/upgrade evidence, schema/index and
constraint tests, closed-transition/event-sequence tests, worker credential issuance/rotation/
revocation tests, cross-tenant job-visibility denial, lifecycle disposal, retention cleanup, and
production worker-configuration failure tests. Phase 17B additionally requires authenticated
submission/list/detail/event/cancel isolation, scoped same-key idempotency and conflict coverage,
public-demo denial, queue-capacity reservation, linked admin replay, and a PostgreSQL concurrent
duplicate-submission test. Phase 17D adds authenticated asynchronous analysis submission,
idempotent replay, transactional source-job report linkage, cancellation-without-report, and the
feature-flag synchronous fallback. The browser form polls only the authenticated job endpoint;
the BFF continues to keep user tokens in HttpOnly cookies.

Phase 17C adds internal-worker credential/scope/protocol denial, BFF internal-path denial,
PostgreSQL `SKIP LOCKED` one-winner claims, lease-generation stale-mutation denial, heartbeat and
progress bounds, cancellation acknowledgement, expiry recovery, retry/dead-letter, and fake
executor tests. The local worker remains optional and has no public port. Phase 17D replaces the
fake executor for `analysis.generate.v1` with deterministic report generation; generic lifecycle
fixtures remain schema-versioned queue tests. Phase 17E adds fake/dry-run `vast.session.start.v1`
coverage: admin-only dedicated submission, rejection by the generic jobs route and arbitrary
profile fields, pre-claim daily cost rejection, unique job-to-session linkage, retry reconciliation
after a lost completion response, cancellation cleanup, migration upgrade/downgrade coverage, and
safe aggregate operator state. CI must keep `VAST_DRY_RUN=true`; real rentals are never a test
dependency.

Phase 17F adds private workspace browser coverage for job status/events/cancellation/result links,
safe account export of job/event/artifact metadata, account-deletion disposal, incomplete-artifact
marking, and retention cleanup. The GitHub Actions backend job applies migrations and runs the
PostgreSQL-enabled suite; frontend CI runs the BFF contracts, production build, browser suite, and
Compose rendering. No real provider credential or paid rental is used.

The Phase 17 correction suite additionally proves cooperative executor termination/no-overlap execution, repeated execution heartbeats, cancellation and
lease-loss cleanup, fixed per-attempt lease horizons, exact schema rejection, typed retry versus
permanent failure handling, organization-role revocation, no-worker queue recovery, durable
provider-request reconciliation, side-effect-free recovery dry runs, durable provider-cost accounting, immediate organization authorization revocation, real-provider fail-closed configuration, direct-route restriction, database-backed report artifacts, and
completed-only report links. PostgreSQL CI remains the concurrency evidence; no CI job may rent a
real provider instance.

The final Phase 17 correction coverage additionally verifies non-destructive membership revocation
under PostgreSQL job-row locks against claim, completion, and heartbeat mutations,
environment-controlled analysis lease horizons, and PostgreSQL reconstruction of deleted capacity
rows for global, provider, user, and organization scopes, including the restored budget period and
completed provider spend on a rebuilt global row.

`backend/scripts/run_smoke_checks.py` defaults to `http://127.0.0.1:8000`; set
`SMOKE_BASE_URL` only when validating an isolated local API process. Optional LLM synthesis should
be disabled for bounded smoke timing unless that provider is the explicit subject of the test.

## 7. Completed Phase 18 validation

Follow the archived [Phase 18 validation and execution record](archive/v1_phase_18/)
when maintaining durable knowledge/retrieval behavior.
The implemented foundation must prove reversible additive migrations, immutable
version relationships, private object-key construction, disabled-by-default
storage, exact `document.ingest.v1` registry schemas, server-derived public,
private, and organization authorization, compensated bounded upload handling,
and feature-gated durable ingestion cleanup/activation. It must preserve the
public JSON retriever as a rollback path.

Implemented 18A–18H evidence:

- `test_phase18_foundation.py` covers ownership, anonymous denial, active
  organization membership, non-member platform-admin denial, trusted-public
  separation, key traversal, bounded/create-only storage, redacted Supabase
  failures, fail-closed configuration, exact job schemas, and disabled
  submission;
- `test_phase18_migration.py` upgrades from the Phase 17 head, preserves
  existing `document_sources`, verifies indexes/uniqueness, downgrades, and
  re-upgrades;
- `test_phase18_postgres_foundation.py` verifies PostgreSQL scope constraints,
  organization isolation, and immediate removed-member denial.
- `test_phase18_storage_adapter.py` verifies the private Supabase metadata
  route, bounded authenticated checksum fallback when object-info lacks one,
  and rejects malformed or cross-key signed download responses without exposing
  provider details.
- `test_phase18b_knowledge_api.py` covers authenticated private and organization
  upload isolation, manager-only mutation, allowlist/checksum validation,
  storage-disabled failure, database-failure object compensation, approval audit
  records, no object URL/key exposure, and account/organization tombstones.
- `test_phase18c_ingestion.py` covers server-owned/idempotent ingestion
  submission, approved-source enforcement, generic-job blocking, allowlisted
  parser behavior, Phase 17 worker execution, retry/cancellation partial-chunk
  cleanup, and atomic version activation.
- `test_phase18d_embeddings.py` covers local-only provider configuration,
  server-owned/idempotent embedding jobs, worker completion, dimension mismatch,
  same-profile generation selection/rollback, and partial-vector cleanup. PostgreSQL integration verifies the `vector`
  extension, `vector(384)` column, HNSW cosine index, and similarity operation.
- `test_phase18e_shadow_retrieval.py` covers pre-ranking public/private/
  organization filtering, active-membership removal, source tombstones,
  non-current versions, checksum-bound citation lineage, and privacy-safe
  retrieval-event metadata. PostgreSQL integration covers tenant-filtered
  pgvector ordering.
- `test_phase18f_lifecycle.py` covers atomic immutable-version rollback,
  manager-scoped embedding generation promotion and rollback, immediate
  tombstone revocation, side-effect-free cleanup dry run, retryable object and
  derived-content cleanup, and safe historical retrieval-event identifiers.
- `test_phase18g_public_corpus.py` covers idempotent checked-in-Markdown
  migration, immutable re-ingestion versions, approved-public-only retrieval,
  convergent partial-state repair including `A -> B -> A`, object-write
  compensation across a two-document transaction, fail-closed deterministic-ID
  collision handling, created-versus-conflict object ownership, post-upload
  verification failure, operator commit failure, transaction-local evaluation
  rollback, declared-lineage/expected-empty evaluation, citation coverage, and
  chunk/metadata/embedding repair. PostgreSQL coverage additionally proves a
  null indexed vector is rebuilt. The suite retains disabled-by-default
  import/cutover flags and automatic JSON fallback when durable public corpus
  is absent.
- `test_phase18_postgres_foundation.py` additionally proves the curated importer
  populates PostgreSQL's indexed `vector(384)` column before public ranking.
- `test_phase18h_citation_lineage.py` proves a durable chunk's exact citation
  identifiers and checksums persist in report source data without a storage key.
- `test_phase18b_knowledge_api.py` additionally covers source-document list
  ownership, administrator-only aggregate readiness, and redaction of private
  storage details. Browser E2E covers the authenticated Knowledge workspace
  source registration and document upload flow through the BFF.
- `test_phase18_final_retrieval.py` proves guarded report-path durable retrieval
  for public/private/organization sources, anonymous public-only behavior,
  citation isolation, deletion/supersession/stale-generation exclusion, explicit
  no-answer protocol filtering, and bounded overfetch after corrupt lineage.
- `test_phase18_postgres_foundation.py` additionally proves exact active-generation
  selection and same-profile rollback on PostgreSQL plus direct analysis-facing
  pgvector tenant isolation. `scripts/preflight_pgvector.py`
  verifies a provisioned `vector` extension before Alembic; migrations never
  assume the application role can install extensions.

`python -m scripts.evaluate_public_corpus` compares the JSON fallback and an
in-transaction durable public bootstrap against `retrieval_eval_dataset.json`,
enforcing item-level precision@k, recall, source coverage, citation integrity,
and expected-empty behavior. The checked-in gate runs at top-1 and currently has
seven cases, including an irrelevant no-answer query; the recorded result is
7/7 with 100% precision@1/recall and zero citation issues. This is local/CI
quality evidence, not deployed storage-policy or cutover evidence.
It rolls the bootstrap back, writes no private object, and requires 80% pass
rate, full source coverage, and zero citation issues. CI runs it on pull
requests; `retrieval-evaluation.yml` repeats it weekly and stores the metrics
as an artifact.

The live deployment runbook uses `python -m scripts.check_knowledge_readiness`
for a non-mutating state check and adds `--probe-storage` only for an explicit
synthetic private-object round trip. Production bucket/RLS policy verification,
two-user tenant probes, and primary retrieval activation remain Phase 22
external validation; no local test claims those provider checks passed.
PostgreSQL tests are required for tenant isolation, vector filtering, concurrent
version creation, job idempotency, and migration safety.

## 8. Phase 19 validation

Test distributed limits, security headers, proxy/SSRF/CSRF protections, centralized redaction, trace correlation, backup restore, migration rollback, scans, load, accessibility, browser, PostgreSQL, and failure recovery.

### Phase 19A implemented coverage

```bash
cd backend
source .venv/bin/activate
python -m pytest -q app/tests/test_phase19_observability.py app/tests/test_access_control.py app/tests/test_health.py
python scripts/check_operational_readiness.py

cd ../frontend
npm run lint
npm run test:bff
```

The tests prove normalized correlation headers, redacted structured logs,
server-owned job/worker propagation, admin-only metadata readiness, disabled
export behavior, and no response/log secret values. They do not claim an
external telemetry, tracing, dashboard, or alert deployment.

### Phase 19B implemented coverage

```bash
cd backend
source .venv/bin/activate
python -m pytest -q app/tests/test_phase19_rate_limits.py
RUN_POSTGRES_INTEGRATION=true python -m pytest -q -m postgres_integration
alembic upgrade head
alembic downgrade -1
alembic upgrade head
python -m scripts.cleanup_expired_data --dry-run
```

The suite proves enforced and shadow behavior, fixed-window retry metadata,
proxy-header trust, salted bucket storage, product-quota separation,
server-validated organization scope, database-outage policy, cleanup reporting,
and PostgreSQL concurrent one-winner admission. It does not claim deployed
proxy CIDR correctness, alert delivery, or a completed staged rollout.

The merged Phase 19 foundation retains JSON RAG as the fallback and does not
claim Phase 18 production activation. Deployed policy and cutover gates remain
external evidence for Phase 22.

### Phase 19I implemented coverage

`test_phase19i_controlled_rag.py` verifies that the controlled rollout checker
requires an explicit opt-in, checks JSON fallback and pgvector readiness,
returns only safe booleans, requires isolated mode for a primary-path probe,
and rejects `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED` in production. Existing
Phase 18 integration tests cover private/organization isolation, worker-owned
ingestion, durable report citation lineage, public-only anonymous retrieval,
and JSON fallback. Deployed storage policy, synthetic identities, worker
availability, report comparison, monitoring, and rollback remain external
evidence requirements.

### Phase 19C implemented coverage

```bash
cd backend
source .venv/bin/activate
python -m pytest -q app/tests/test_phase19c_security.py app/tests/test_phase18b_knowledge_api.py app/tests/test_health.py

cd ../frontend
npm run test:bff
npm run test:security
npm run build
npm run test:mfa:routes
npm run test:e2e
```

These checks cover exact CORS preflight/mutation origins, request-size rejection,
browser/API baseline headers, HSTS configuration, BFF origin/target/redirect
rejection, safe backend-base validation, and required scanner clean/failure
behavior. They do not prove a deployed WAF, bot policy, scanner/quarantine
service, CSP report collection, final production origin list, or HSTS scope.

### Phase 19D implemented coverage

```bash
cd backend
source .venv/bin/activate
python -m pytest -q app/tests/test_phase19d_monitoring.py
OPERATIONS_MONITORING_ENABLED=true OPERATIONS_SYNTHETIC_CHECKS_ENABLED=true \
  OPERATIONS_SYNTHETIC_ALLOWED_ORIGINS=https://approved-synthetic-target.example \\
  python -m scripts.run_synthetic_checks --base-url https://approved-synthetic-target.example

cd ../frontend
npm run lint
npm run build
```

The automated coverage proves aggregate-only queue/worker/retrieval signals,
candidate deduplication, admin authorization, configuration gates, and fixed
synthetic paths with no response-body or token output. The CLI example requires
an operator-owned target and is not run against production customer data. Pager,
telemetry, dashboard, authenticated synthetic, escalation, and SLO evidence are
external rollout work.

### Phase 19E implemented coverage

```bash
cd backend
source .venv/bin/activate
python -m pytest -q app/tests/test_phase19e_recovery_operations.py
BACKUP_RESTORE_DRILL_ENABLED=true \
  python -m scripts.run_sanitized_restore_drill --write-manifest /approved-isolated-path/manifest.json
```

The local suite proves salted metadata-only manifest generation and isolated
target comparison, excludes report/source/object/identity/credential values,
fails closed for invalid retention evidence, blocks disabled/production CLI
execution, and records provider credential update/disable behavior without
returning a secret. It does not prove a provider database/object restore,
approved RPO/RTO, encryption-key migration, or production secret-store audit.

### Phase 19F implemented coverage

```bash
python3 scripts/supply_chain.py check-workflows
python3 scripts/supply_chain.py check-lockfiles
python3 scripts/supply_chain.py check-security-exceptions
python3 scripts/supply_chain.py generate-sbom --output /tmp/defi-sbom.cdx.json

cd backend
source .venv/bin/activate
python -m pytest -q app/tests/test_phase19f_supply_chain.py
pip-audit -r requirements.txt

cd ../frontend
npm audit --omit=dev
```

The focused tests reject mutable workflow actions, `pull_request_target`,
persisted checkout credentials, and unlocked Python requirements; they also
validate deterministic secret-free SBOM generation and exact owned,
time-bounded scanner suppressions. GitHub blocks high/critical pip/npm and
Trivy findings. Dependency Review becomes blocking only after a repository
administrator enables GitHub Dependency Graph. Its first hosted evidence, main
ruleset configuration, required-check enforcement, and external-PR
preview-secret isolation still require an administrator and must not be claimed
from local tests alone.

### Phase 19G implemented coverage

```bash
python3 scripts/check_incident_runbooks.py

cd backend
source .venv/bin/activate
python -m pytest -q app/tests/test_phase19g_incident_runbooks.py
```

The structural check verifies the stable runbook registry, ten tabletop
scenarios, ownership/communication declarations, and detection, containment,
eradication, recovery, communications, evidence, and retrospective sections.
It does not claim a pager, named on-call owner, incident system, provider
exercise, customer-data test, or production tabletop outcome. Those are Phase
19G deployment gates and final evidence remains part of Phase 22 approval.

### Phase 19H implemented coverage

```bash
cd backend
source .venv/bin/activate
python -m pytest -q app/tests/test_phase19h_exercises.py
RUN_POSTGRES_INTEGRATION=true python -m pytest -q app/tests/test_phase19h_isolated_operations.py
python -m scripts.run_phase19_exercises --list

APP_ENV=exercise \
OPERATIONS_EXERCISES_ENABLED=true \
OPERATIONS_EXERCISES_ISOLATED=true \
VAST_ENABLED=false \
VAST_DRY_RUN=true \
VAST_REAL_RENTALS_ENABLED=false \
RUN_POSTGRES_INTEGRATION=true \
python -m scripts.run_phase19_exercises --run --evidence-file /tmp/phase19-exercise-evidence.json

cd ../frontend
npm run test:accessibility
```

The runner exercises fixed rate-limit, admission, worker-loss, fake-provider,
storage, vector-repair, migration, authorization, recovery, and semantic
accessibility paths. The dedicated HTTP harness makes 24 public `/health` and
24 authenticated `/api/auth/me` requests at concurrency six and records request
count, concurrency, throughput, success/error rate, p50/p95 latency, and
thresholds. PostgreSQL scenarios record six-way durable admission, queue
recovery, worker lease-loss/stale-execution rejection, and database/storage
failure recovery. It rejects production, non-isolated, real-provider, and
arbitrary-command operation; the schema-v2 evidence is capped at 8 KiB and
contains only aggregate timings/counts/statuses/thresholds, never durable test
data, request bodies, identifiers, URLs, exception text, or customer data.
The scheduled no-secret GitHub workflow adds isolated weekly evidence. These
results are not production load capacity, provider, pager, customer-data,
assistive-technology, or chaos-test evidence.

## 9. Phase 20 validation

Phase 20 is planned only. Its validation authority is
[`phase_20_execution_plan.md`](phase_20_execution_plan.md). Each slice must add
focused unit, PostgreSQL concurrency/isolation, API, BFF/browser, migration, and
rollback evidence as applicable. Required coverage includes:

- analytics consent, taxonomy allowlists, retention, export, and deletion;
- schedule timezone, idempotency, missed-run, cancellation, quota, and recovery behavior;
- notification preference, destination verification, signed webhook, retry, dead-letter, unsubscribe, and deletion behavior;
- explicit separation of network limits, product quotas, billable usage, and versioned plan entitlements;
- server-owned entitlement resolution and exactly-once usage reconciliation;
- billing sandbox signature, replay, out-of-order, lifecycle, portal, and rollback behavior;
- organization invitation, seat, owner-transfer, billing-contact, export, deletion, audit, and concurrency boundaries;
- support, status, feedback, abuse, and privacy-request ownership and retention.

No provider test may use production customer data or be treated as provider
selection before its ADR is approved.

## 10. Phase 21 validation

Test provider routing, model/prompt versioning, evaluation promotion/rollback, deterministic-field preservation, citation support, source-instruction defenses, tenant privacy, cost budgets, feedback controls, and compute cleanup.

## 11. CI expectations

CI should progressively include:

- PostgreSQL 16;
- migrations;
- compile and pytest;
- runtime preparation;
- frontend type/build;
- auth/BFF tests;
- browser tests;
- Compose validation;
- failure artifacts;
- later worker, retrieval, security, accessibility, and load checks.

Real production credentials and paid provider actions are never required in CI.
