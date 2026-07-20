# Current State — DeFi Thesis & Risk Copilot

This document describes what is currently deployed on `main`, what exists only on the active Phase 16 branch, and what remains incomplete.

Authoritative references:

- [`development_plan.md`](development_plan.md) — phase history and roadmap;
- [`phase_16_identity_ownership_contract.md`](phase_16_identity_ownership_contract.md) — Phase 16 requirements and blockers;
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

### Frontend session/BFF

- same-origin `/api/backend/*` BFF foundation;
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
- saved theses;
- centralized resource policy helpers.

### Anonymous isolation

- cryptographically random server-created anonymous sessions;
- HttpOnly anonymous-session cookie;
- anonymous report and analysis ownership;
- expiration timestamps for new anonymous analyses/reports;
- access tests for matching, different, and expired sessions.

### Quotas and lifecycle

- persistent daily usage quotas for analysis, simulation, options, and market-data fetches;
- saved-thesis and watchlist resource-count limits;
- account export;
- account soft deletion;
- consent records;
- terms/privacy pages;
- retention cleanup for expired sessions/resources and old deleted-user identifiers;
- dry-run cleanup mode.

### Frontend product foundations

- login/signup/verification/recovery/reset pages;
- account and account-security pages;
- thesis management component;
- organization management component;
- terms/privacy pages;
- auth-aware session panel;
- basic E2E smoke command.

---

## 6. Phase 16 branch — remaining blockers

Phase 16 is not complete. The authoritative blocker list is maintained in [`phase_16_identity_ownership_contract.md`](phase_16_identity_ownership_contract.md).

Current known blockers include:

1. the BFF allowlist currently contains `/`, which matches every absolute backend path;
2. the BFF forwards the full frontend cookie header to Render instead of only required backend cookies;
3. `block_public_demo_mutation` remains global deployment-mode logic and can block authenticated mutations in a public+authenticated deployment;
4. resource policy may grant organization access whenever `organization_id` exists without first requiring `visibility=organization`;
5. daily quota first-use creation is not concurrency-safe;
6. saved-resource count-then-create limits are not concurrency-safe;
7. recovery lacks a complete provider callback/code-exchange path;
8. signup consent versions are still client-influenced rather than exclusively server-owned;
9. MFA enrollment/challenge/unenrollment is not a complete usable workflow;
10. organization knowledge-base ownership and tenant retrieval are not fully implemented;
11. migration foreign keys and compound ownership indexes need review;
12. organization/security lifecycle audit coverage is incomplete;
13. browser E2E and PostgreSQL concurrency coverage are incomplete;
14. deployed Supabase email/recovery/MFA/session behavior is unverified;
15. terms/privacy require qualified legal review.

The branch must not be described as commercially production-ready.

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

Runtime files are not authoritative for persisted reports, but the current RAG index is still local/runtime JSON and not tenant-aware.

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

- PostgreSQL concurrent quota tests;
- browser anonymous create/read/isolation flow;
- browser login/BFF/refresh/logout flow;
- organization membership/removal/deletion isolation;
- strict private/organization visibility tests;
- recovery callback/reset flow;
- consent-version enforcement;
- admin MFA denial/allow flow;
- deployed Supabase manual verification;
- Vercel preview and Render preview validation.

---

## 10. Known platform limitations

- public rate limiting is still in-process, not distributed;
- current RAG index is local JSON and not tenant-aware;
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
