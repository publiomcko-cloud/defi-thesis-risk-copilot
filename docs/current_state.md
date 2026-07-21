# Current State — DeFi Thesis & Risk Copilot

This document describes what is currently deployed on `main`, what exists only on the active Phase 16 branch, and what remains incomplete.

Authoritative references:

- [`development_plan.md`](development_plan.md) — phase history and roadmap;
- [`phase_16_identity_ownership_contract.md`](phase_16_identity_ownership_contract.md) — Phase 16 requirements and blockers;
- [`phase_16_execution_plan.md`](phase_16_execution_plan.md) — ordered Phase 16 sub-phases;
- [`future_phase_contracts.md`](future_phase_contracts.md) — Phases 17–21;
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

The live production branch is `main`. It currently represents the completed Phase 15 public-safe demo baseline unless a later branch has been explicitly merged and deployed.

Render free-tier cold starts may delay the first request after inactivity.

---

## 2. Phase status

Completed on `main`:

- Phase 0 technical MVP;
- Post-MVP Phases 1–12;
- Final Phase 13 demo/report package;
- Final Phase 14 public deployment;
- V1 Phase 15 product hardening and public-safe UX.

Active branch:

```text
agent/v1-phase-16-identity-ownership
```

Current phase status:

```text
V1 Phase 16 — In Progress
```

Reviewed Phase 16 correction commit:

```text
bf1b9ddc6153e02f2018c4a43ba20bb634e82709
```

Documentation-hardening commits follow that correction on the same branch.

---

## 3. Current stack

- Frontend: Next.js App Router, React, TypeScript, Vercel
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic, Render
- Database: Supabase PostgreSQL hosted; PostgreSQL/SQLite local support
- RAG: curated Markdown, heading-aware chunking, deterministic local embeddings, local JSON index
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

## 5. Phase 16 branch — verified implementation foundation

The active branch currently contains the following foundations.

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

## 6. Phase 16 branch — remaining blockers

Phase 16 is not complete. The authoritative blocker list is maintained in [`phase_16_identity_ownership_contract.md`](phase_16_identity_ownership_contract.md).

Current known blockers include:

1. deployed Supabase email/recovery/MFA/session behavior is unverified;
2. terms/privacy require qualified legal review.

The branch must not be described as commercially production-ready.

Planned execution order:

```text
16A Admin MFA usable workflow — complete locally
16B Organization knowledge metadata and retrieval boundary — complete locally
16C Migration, foreign-key, and index review — complete locally
16D Audit coverage and security event logging — complete locally
16E PostgreSQL concurrency and Phase 15 data validation — complete locally and in CI configuration
16F Full browser E2E for Phase 16 workflows — complete locally and in CI configuration
16G Deployed Supabase verification
16H Final legal, documentation, and release gate
```

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
- provide Phase 16 multi-user foundations on the active branch.

---

## 9. Required validation before Phase 16 merge

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
- deployed Supabase manual verification;
- Vercel preview and Render preview validation.

---

## 10. Known platform limitations

- public rate limiting is still in-process, not distributed;
- current RAG index is local JSON and intentionally public-curated only; organization metadata is not document/vector storage;
- heavy work lacks durable queue/workers;
- Render may cold-start;
- several market adapters remain partial/manual fallbacks;
- monitoring/discovery are manually initiated;
- production observability, WAF, backups, restore drills, and incident operations are later phases;
- billing, notifications, and commercial support workflows are not implemented;
- model/research expansion remains later-phase work;
- no wallet, signing, custody, private-key handling, or execution exists.

---

## 11. Next phases

- Phase 16 — finish identity, ownership, quotas, recovery, MFA, and browser/deployment validation;
- Phase 17 — durable jobs and hybrid workers;
- Phase 18 — durable tenant RAG and object/vector storage;
- Phase 19 — production operations and security;
- Phase 20 — analytics, notifications, plans, billing, support, and legal readiness;
- Phase 21 — evaluated model and research-intelligence expansion.

See [`future_phase_contracts.md`](future_phase_contracts.md) for complete requirements.
