# Current State — DeFi Thesis & Risk Copilot

This document describes what is deployed on `main`, the next V1 implementation
phase, and the remaining roadmap.

Authoritative references:

- [`development_plan.md`](development_plan.md) — phase history and roadmap;
- [`archive/v1_phase_16/`](archive/v1_phase_16/) — archived Phase 16 contract, execution plan, and deployment evidence;
- [`archive/v1_phase_17/`](archive/v1_phase_17/) — archived Phase 17 plan, corrections, and validation evidence;
- [`archive/v1_phase_18/`](archive/v1_phase_18/) — archived Phase 18 plan, validation, correction, migration, and cutover evidence;
- [`phase_19_execution_plan.md`](phase_19_execution_plan.md) — merged Phase 19 foundation and rollout gates;
- [`phase_19_threat_model.md`](phase_19_threat_model.md) and [`phase_19_evidence_matrix.md`](phase_19_evidence_matrix.md) — Phase 19A–19I risk and evidence record;
- [`phase_20_execution_plan.md`](phase_20_execution_plan.md) — next planned implementation sequence;
- [`future_phase_contracts.md`](future_phase_contracts.md) — Phases 17–22 contract;
- [`agent_execution_guide.md`](agent_execution_guide.md) — short-prompt workflow.

---

## 1. Live deployment

- Frontend: `https://defi-thesis-risk-copilot.vercel.app`
- Guided demo: `https://defi-thesis-risk-copilot.vercel.app/demo`
- Backend: `https://defi-thesis-risk-copilot.onrender.com`
- Liveness: `https://defi-thesis-risk-copilot.onrender.com/health`
- Readiness: `https://defi-thesis-risk-copilot.onrender.com/ready`
- Deployment status: `https://defi-thesis-risk-copilot.onrender.com/api/deployment/status`
- API docs: `https://defi-thesis-risk-copilot.onrender.com/docs`

The live production branch is `main`. It contains the completed Phase 15
public-safety baseline, Phase 16 managed identity/ownership, Phase 17 durable
jobs and worker control plane, Phase 18 durable knowledge/retrieval code, and
the Phase 19 operations/security repository foundation. Phase 19 provider and
control-plane evidence remains external.

Render free-tier cold starts may delay the first request after inactivity.

---

## 2. Phase status

Completed on `main`:

- Phase 0 technical MVP;
- Post-MVP Phases 1–12;
- Final Phase 13 demo/report package;
- Final Phase 14 public deployment;
- V1 Phase 15 product hardening and public-safe UX;
- V1 Phase 16 production identity, ownership, organizations, and quotas;
- V1 Phase 17 durable jobs, workers, async analysis, and job workspace.
- V1 Phase 18 production RAG and knowledge storage.

Implemented foundation on `main`:

- V1 Phase 19 operations, security, recovery, exercises, and controlled
  durable-RAG readiness. External deployment gates remain open.

Current status:

```text
V1 Phase 16 — Complete
V1 Phase 17 — Complete
V1 Phase 18 — Complete and merged into main; production features remain feature-gated
V1 Phase 19 — Implemented Foundation and merged into main; centralized telemetry, alert delivery, provider restore drills, secret rotation, protected-branch evidence, and controlled deployment evidence remain external gates
V1 Phase 20 — Planned and next for implementation; no provider selected or runtime capability added
V1 Phase 21 — Planned implementation work
V1 Phase 22 — Planned final release validation and launch approval
```

Reviewed Phase 16 correction commit:

```text
bf1b9ddc6153e02f2018c4a43ba20bb634e82709
```

Historical Phase 16 evidence remains in its archive.

---

## 3. Current stack

- Frontend: Next.js App Router, React, TypeScript, Vercel
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic, Render
- Database: Supabase PostgreSQL hosted; PostgreSQL/SQLite local support
- RAG: active curated Markdown/local JSON path plus disabled-by-default Phase 18
  durable source/document/version/chunk storage, ingestion worker, and local-only
  pgvector embedding generations, lifecycle rollback/tombstone cleanup, and a
  disabled-by-default tenant-safe shadow retrieval/citation path, plus an
  operator-only curated public-corpus importer and guarded pgvector-public
  report path with automatic JSON fallback; authenticated source/document/version
  workspace, report citation lineage, and admin-safe readiness metrics are also
  implemented. Production reports still use JSON unless the guarded primary flag
  is explicitly enabled after live deployment verification
- Public data adapters: manual, Pendle, Morpho, Aave, DefiLlama, CoinGecko foundations
- Testing: pytest, PostgreSQL CI migration path, TypeScript/build checks, smoke scripts, Compose validation
- Optional synthesis: Ollama, OpenAI-compatible APIs, admin-controlled Vast.ai foundation

---

## 4. Deployed Phase 15 baseline

The deployed public product supports:

### Public read-only

- demo status/scenarios;
- protocols;
- seeded reports;
- discovery candidates;
- review outcomes;
- discovered knowledge metadata;
- seeded watchlists/alerts;
- safe deployment metadata.

### Public bounded compute

- strategy analysis;
- simulation;
- options analysis;
- market-data lookup.

### Publicly blocked

- demo reset/reseed;
- monitoring/discovery runs;
- evaluation creation;
- review changes;
- document/RAG ingestion;
- watchlist/alert mutations;
- credential and audit access;
- Vast.ai lifecycle controls.

Phase 15 also provides:

- common read-only public identity instead of implicit admin;
- in-process public compute limiting;
- strict request bounds;
- request IDs and safe errors;
- database/RAG-aware readiness;
- startup migrations, demo seed, and RAG preparation;
- cache expiration/deduplication;
- public-safe navigation and read-only UX;
- cold-start/retry guidance;
- source links and Markdown export.

This behavior is the regression baseline for every later phase.

---

## 5. Phase 16 completed identity foundation

The following foundations are complete on `main`.

### Managed identity

- `AUTH_PROVIDER=supabase` JWT validation through configured JWKS;
- RS256 signature, issuer, audience, expiration, subject, and email checks;
- production rejection of `legacy_local` authentication;
- verified-email enforcement;
- idempotent local application-user synchronization;
- database-owned platform role and plan;
- protection against linking an existing non-invitation account only by matching email;
- pending-invitation account linking foundation;
- platform-admin `aal2` enforcement when configured.
- usable Supabase TOTP enrollment, challenge/verification, factor listing, and unenrollment through same-origin Next.js handlers;
- HttpOnly session-cookie rotation after successful MFA verification without exposing access or refresh tokens in response bodies or browser storage.

### Frontend session/BFF

- same-origin `/api/backend/*` BFF foundation;
- explicit BFF backend route-family allowlist without a catch-all `/` prefix;
- BFF cookie filtering that forwards only the anonymous-session cookie to FastAPI;
- HttpOnly access-token, refresh-token, and expiration cookies;
- refresh-token exchange and rotation foundation;
- cookie clearing after failed refresh;
- browser API client selects same-origin BFF paths;
- server-only backend base URL foundation.

### Ownership and organizations

- application users;
- organizations;
- memberships with owner/admin/member/viewer roles;
- pending/active/removed membership foundation;
- final active-owner protection;
- active/deleted organization check in membership-role lookup;
- ownership/scope fields on analysis requests, reports, and watchlists;
- named ownership, organization, anonymous-session, saved-thesis, and consent foreign keys with deliberate `SET NULL`/`RESTRICT` behavior;
- compound authorization and quota indexes, verified through Phase 15 seeded-data migration and local PostgreSQL seeded migration-cycle checks;
- saved theses;
- centralized resource policy helpers.
- strict private-vs-organization visibility checks so stale `organization_id` values do not grant organization access.
- bounded lifecycle/security audit records for organization, membership, account, consent, credential, and platform-sensitive operations;
- redaction of audit emails, secrets, tokens, cookies, verification codes, and raw request bodies, plus a server-only BFF MFA audit channel when configured.
- PostgreSQL concurrency coverage for quota first use and resource-count limits, plus migrated Phase 15 public report/watchlist API regression coverage.
- non-public local development materializes its synthetic `demo_admin` user before that actor can own foreign-key-backed records; public demo visitors remain anonymous/common users.

### Organization knowledge boundary

- organization-owned source metadata with source URL, provenance hash, human approval, status, and `metadata_only` storage state;
- active-member read access and owner/admin registration/removal authorization without a platform-admin private-data bypass;
- immediate denial for removed members and disabled/deleted organizations;
- server-derived retrieval scope passed through local and hybrid retrieval;
- organization-tagged chunks rejected from the shared JSON index while durable tenant storage is disabled;
- global discovery, review, and ingestion mutations remain platform-admin controlled.

### Anonymous isolation

- cryptographically random server-created anonymous sessions;
- HttpOnly anonymous-session cookie;
- anonymous report and analysis ownership;
- expiration timestamps for new anonymous analyses/reports;
- access tests for matching, different, and expired sessions.

### Quotas and lifecycle

- persistent daily usage quotas for analysis, simulation, options, and market-data fetches;
- controlled first-use quota creation retry and per-user resource-count lock rows for saved-thesis and watchlist limits;
- account export;
- account soft deletion;
- consent records;
- server-owned terms/privacy version configuration for consent persistence;
- terms/privacy pages;
- retention cleanup for expired sessions/resources and old deleted-user identifiers;
- dry-run cleanup mode.

### Frontend product foundations

- login/signup/verification/recovery/reset pages;
- server-side recovery callback/code-exchange foundation for Supabase recovery links;
- account and functional account-security/MFA pages;
- thesis management component;
- organization and organization knowledge-metadata management components;
- terms/privacy pages;
- auth-aware session panel;
- production-like Chromium E2E command with local mocked Supabase/FastAPI upstreams, anonymous isolation/expiry, BFF login/refresh/logout, recovery/reset, account consent/export/deletion confirmation, thesis CRUD/analyze, organization owner protection/member removal, MFA, no-private-content flash, and mobile keyboard/layout smoke;
- failure screenshot/trace capture and CI browser-artifact upload configuration.

---

## 6. Deferred final release validation — V1 Phase 22

Phase 16 is complete on `main`. Its remaining external launch gates are
intentionally tracked in V1 Phase 22, not silently treated as complete:

1. deployed Supabase custom SMTP, signup verification, recovery/reset, authenticated-browser refresh/logout, and administrator MFA validation with disposable real accounts;
2. qualified legal review of terms, privacy, retention, consent, and public launch claims.

The credentialed Phase 16 Vercel/Render preview passed automated BFF,
anonymous-isolation, CORS, readiness, and safe-status checks. Its historical
evidence is preserved in
[`archive/v1_phase_16/phase_16_deployed_verification.md`](archive/v1_phase_16/phase_16_deployed_verification.md).
The product must not be described as commercially production-ready until Phase
22 completes.

---

## 7. Startup and readiness

Current public backend startup:

```text
Alembic upgrade
  -> scripts.prepare_runtime
     -> idempotent deterministic demo seed
     -> curated local RAG index build
  -> Uvicorn
```

Endpoints:

- `/health` — process liveness;
- `/ready` — database and public RAG readiness;
- `/api/deployment/status` — safe environment and demo metadata.

Runtime files are not authoritative for persisted reports. The current RAG index is still local/runtime JSON and has no tenant storage; its retrieval boundary intentionally permits public-curated chunks only.

---

## 8. Current product capabilities

The project can:

- parse DeFi strategy theses;
- retrieve curated protocol context;
- fetch/normalize public and manual market data;
- expose assumptions and missing fields;
- calculate deterministic risk ratings;
- generate/persist structured reports;
- export Markdown;
- simulate lending/fixed-yield scenarios;
- analyze long call/put payoff scenarios;
- display watchlists and alerts;
- discover and evaluate public-source candidates;
- enforce human approval before trusted ingestion;
- optionally synthesize wording without replacing deterministic fields;
- prepare ML/retrieval/HPC workspaces;
- provide the merged Phase 16 multi-user foundations;
- run authenticated asynchronous analysis through durable jobs and review private job history.

---

## 9. Completed Phase 16 validation

Backend:

```bash
cd backend
source .venv/bin/activate
python -m compileall app scripts
alembic upgrade head
alembic downgrade -1
alembic upgrade head
python -m pytest -q
python scripts/run_smoke_checks.py
python -m scripts.cleanup_expired_data --dry-run
```

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm run build
npm run test:e2e
```

Docker:

```bash
docker compose config
docker compose -f docker-compose.production.yml config
docker compose down -v
docker compose up -d --build
```

Additional required evidence:

- completed PostgreSQL concurrent quota tests;
- local browser anonymous create/read/isolation/expiry flow;
- local browser login/BFF/refresh/logout flow;
- organization membership/removal/deletion isolation;
- strict private/organization visibility tests;
- local mocked recovery callback/reset flow;
- local consent and MFA workflow coverage;
- hosted anonymous isolation and preview readiness validation;
- CI validation on the merge commit.

The deferred deployed provider and legal checks are Phase 22 requirements.

---

## 10. Known platform limitations

- the new PostgreSQL shared limiter is implemented but disabled by default; the legacy in-process public-demo limiter remains the rollback fallback until preview shadow and proxy-policy evidence exists;
- local JSON remains the default public-curated retrieval path and the explicit
  rollback fallback. When the guarded Phase 18 primary flag is enabled,
  authenticated analysis can retrieve approved public, caller-owned private,
  and active-organization durable knowledge through server-derived filters;
  anonymous analysis remains public-only. Storage, ingestion, embeddings,
  shadow retrieval, and the primary flag remain disabled by default pending
  production storage-policy and cutover evidence;
- durable jobs, private workspace, retention, export, and account-deletion behavior are complete
  on `main`; Vast provider jobs remain disabled/dry-run by default, and real-provider operation is
  unverified;
- Render may cold-start;
- several market adapters remain partial/manual fallbacks;
- monitoring/discovery are manually initiated;
- the production hybrid frontend exposes public demo/login routes alongside authenticated workspace
  navigation; platform-admin APIs remain role-protected by the backend rather than by hidden URLs;
- provider backup/restore, deployed observability/WAF evidence, GitHub branch-protection/scanner-baseline evidence, and incident operations remain Phase 19/22 gates;
- billing, notifications, and commercial support workflows are not implemented;
- model/research expansion remains later-phase work;
- no wallet, signing, custody, private-key handling, or execution exists.

---

## 11. Active and next phases

- Phase 17 — Complete on `main`; archived implementation and correction evidence is in
  [`archive/v1_phase_17/`](archive/v1_phase_17/). Real Vast.ai rental and continuously hosted
  worker validation remain Phase 22 gates;
- Phase 18 — Complete on `main`; implementation, correction, validation,
  migration, and cutover evidence is archived in
  [`archive/v1_phase_18/`](archive/v1_phase_18/). It provides durable
  tenant-safe knowledge storage, bounded source/document workflows, worker
  ingestion, embeddings, citations, lifecycle controls, curated corpus import,
  and the Knowledge workspace. The complete code remains feature-gated; JSON
  RAG remains the production fallback. The local top-1 retrieval gate has seven
  cases with 100% precision/recall and zero citation issues, but is not
  production cutover evidence. Controlled deployment remains governed by the
  Phase 19 operational gates; final storage-policy, cutover, and launch
  approval remain Phase 22 gates;
- Phase 19 — Implemented Foundation on `main`: 19A implements redacted structured logging,
  browser/BFF/API/job/worker correlation IDs, and non-mutating operational
  readiness. 19B adds a disabled-by-default PostgreSQL shared limiter for
  bounded compute and durable job admission. 19C adds exact CORS/origin and
  measured body controls for declared, chunked, and misleading-length requests,
  report-only CSP/minimum browser and API headers, BFF target/redirect
  checks, and a fail-closed required-scanner contract. External telemetry,
  alerting, production proxy/WAF/origin evidence, scanner/quarantine deployment,
  CSP report review, HSTS approval, backup/restore, and all later Phase 19 gates
  remain pending. 19D adds a disabled-by-default aggregate monitoring snapshot,
  local alert candidates, private admin operations view, and safe synthetic CLI;
  no telemetry exporter, pager, status provider, synthetic identity, or customer
  probe is configured. 19E adds a disabled metadata-only restore verifier,
  opt-in retention evidence guard, and secret-inventory/runbook templates; no
  provider backup/restore, approved RPO/RTO, or encryption-key migration is
  implemented or claimed. 19F adds SHA-pinned/read-only security workflows,
  dependency remediation, lockfile/action policy checks, source SBOM artifacts,
  secret/SAST/dependency/container scans, Dependabot, and a findings runbook.
  High/critical dependency, container, and repository findings now fail CI;
  exceptions must be explicit, owned, and time-bounded. GitHub main ruleset
  configuration and first hosted scanner evidence remain external rollout gates;
  19G adds versioned incident/security-operation procedures, stable mappings
  from the existing aggregate alert IDs, safe evidence-handling rules, and ten
  tabletop scripts. The repository has no on-call roster, incident tracker,
  pager, or production exercise evidence: named primary/backup owners,
  communication authority, approved evidence location, and completed tabletop
  records remain external deployment gates;
  19H adds a fail-closed fixed exercise runner, isolated scheduled pgvector CI
  workflow, semantic accessibility contract, and bounded safe exercise metrics.
  It validates local/CI
  saturation, admission, worker-loss, fake-provider, storage, retrieval,
  migration, authorization, recovery, and frontend paths without persisting
  exercise data or allowing real rentals. Production load/chaos, alert/pager,
  customer-data, provider, and assistive-technology evidence remain external
  gates;
  19I adds a read-only controlled durable-RAG rollout checker. It requires an
  explicit validation flag, verifies pgvector plus JSON fallback and the
  approved shadow prerequisites, rejects primary retrieval in production, and
  permits a primary-path check only in an explicitly isolated non-production
  environment. It does not create tenant data or activate a feature. Deployed
  private-bucket/RLS, synthetic two-user/organization, trusted-worker,
  durable-versus-JSON, citation, monitoring, and rollback evidence remains an
  external gate. The latest hosted PR validation passed, but centralized
  telemetry, alert delivery, provider restore, secret rotation,
  protected-branch enforcement, and controlled deployment are not evidenced
  as complete;
- Phase 20 — Planned and next for implementation under
  [`phase_20_execution_plan.md`](phase_20_execution_plan.md): privacy-conscious
  analytics, durable schedules, user-controlled notifications, separate
  product quotas/billable usage/versioned entitlements, billing sandbox
  foundations, organization commercial workflows, support/status/privacy
  processes, and legal readiness. No Phase 20 provider is selected and no
  Phase 20 runtime behavior is implemented;
- Phase 21 — evaluated model and research-intelligence expansion.
- Phase 22 — final provider, legal, and launch validation.

See [`future_phase_contracts.md`](future_phase_contracts.md) for complete requirements.
