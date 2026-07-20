# Current State — DeFi Thesis & Risk Copilot

This document describes the current implementation and deployment state. The authoritative phase history and roadmap are in [`docs/development_plan.md`](development_plan.md).

## Live Deployment

- Frontend: `https://defi-thesis-risk-copilot.vercel.app`
- Guided demo: `https://defi-thesis-risk-copilot.vercel.app/demo`
- Backend: `https://defi-thesis-risk-copilot.onrender.com`
- Liveness: `https://defi-thesis-risk-copilot.onrender.com/health`
- Readiness: `https://defi-thesis-risk-copilot.onrender.com/ready`
- Deployment status: `https://defi-thesis-risk-copilot.onrender.com/api/deployment/status`
- API docs: `https://defi-thesis-risk-copilot.onrender.com/docs`

The Render free-tier backend may cold-start after inactivity.

## Current Status

Completed:

- Core technical MVP
- Post-MVP Phases 1-12
- Final Phase 13 demo data and example reports
- Final Phase 14 Vercel/Render/Supabase deployment

Active iteration:

```text
V1 Phase 15 — Product Hardening and Public-Safe UX
```

Phase 15 addresses the security, API, deployment, design, and UX findings from the full deployed-project evaluation.

## Current Stack

- Frontend: Next.js App Router, React, TypeScript, responsive CSS, Vercel
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic, Render
- Database: Supabase PostgreSQL in the hosted deployment; SQLite/PostgreSQL supported locally
- RAG: curated Markdown, header-aware chunking, deterministic local embeddings, JSON index
- Public data adapters: manual, Pendle, Morpho, Aave, DefiLlama, and CoinGecko foundations
- Testing: pytest, TypeScript checks, Next.js build, smoke scripts, Compose validation
- Automation: GitHub Actions and platform deployments
- Optional model providers: Ollama, OpenAI-compatible APIs, and admin-only Vast.ai dry-run/manual warm-up

## Public Product Boundary

### Public read-only access

Visitors may inspect:

- demo status and scenario metadata
- protocols
- persisted reports
- discovery candidates
- evaluation/review outcomes
- discovered knowledge-base metadata
- seeded watchlists and alerts
- safe deployment metadata

### Public bounded compute

Visitors may run bounded and rate-limited:

- strategy analysis
- deterministic simulation
- options analysis
- market-data retrieval

### Publicly blocked operations

When `PUBLIC_DEMO_MODE=true`, visitors cannot:

- become an administrator through disabled authentication
- seed/reset the hosted demo through the public API
- run monitoring or global discovery
- create evaluations
- change review state
- ingest sources into RAG
- ingest documents
- create or modify watchlists and alert status
- read audit events or credential metadata
- create, rotate, or disable credentials
- control Vast.ai sessions

The hosted UI hides administrator navigation and renders review/watchlist demonstrations as read-only.

## Startup and Readiness

The public backend startup sequence is:

```text
Alembic upgrade
  -> deterministic demo seed
  -> curated RAG index build
  -> Uvicorn
```

Endpoints:

- `/health` checks process liveness.
- `/ready` checks database connectivity and the public RAG index.
- `/api/deployment/status` exposes safe environment flags and demo state.

Render uses `/ready` as its health-check path.

## Current Capabilities

The application can:

- parse a DeFi strategy thesis
- retrieve curated protocol context
- fetch or normalize public/manual market data
- expose assumptions and missing fields
- calculate deterministic risk ratings and drivers
- generate and persist structured reports
- export Markdown
- simulate lending/fixed-yield stress conditions
- analyze long crypto call/put payoff scenarios
- display seeded watchlists and alerts
- discover and normalize public-source candidates
- evaluate candidates and create review records
- maintain human approval before RAG trust
- ingest approved knowledge in a private/admin environment
- optionally synthesize report wording with an LLM while preserving deterministic fields
- prepare datasets and HPC templates for future model work

## Phase 15 Improvements in This Iteration

### Backend and security

- public visitors use a common read-only identity
- public mutations are centrally blocked
- bounded public compute is rate-limited
- request payloads have size and range limits
- request IDs and request-duration logging are included
- unhandled errors are logged without returning internals
- database/RAG readiness is explicit
- market cache expiration is enforced
- repeated cache keys update rather than grow indefinitely

### Frontend and UX

- live demo is the primary product entry
- actual production URLs replace placeholders
- public admin links are hidden
- direct admin access explains the protected boundary
- review and watchlist screens become read-only publicly
- APY, LTV, LLTV, implied volatility, USD, and basis-point units are explicit
- advanced controls use progressive disclosure
- cold-start retry states and readiness links are visible
- sources are clickable
- Markdown supports copy/download
- duplicate report sections are removed
- navigation, footer, badges, focus states, hover states, responsive behavior, and reduced motion are improved
- shared public-database privacy warnings are visible

## Validation

Backend:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
python -m pytest -q
python scripts/run_smoke_checks.py
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Docker:

```bash
docker compose config
docker compose -f docker-compose.production.yml config
```

RAG:

```bash
cd backend
python scripts/evaluate_retrieval.py --retriever hybrid
```

## Known Limitations

- Phase 15 uses an in-process rate limiter suitable for the current single-instance demo, not a distributed production limiter.
- The hosted environment still uses a shared database for public generated reports; inputs must not contain private or sensitive information.
- Production-grade identity, secure cookie sessions, MFA, account recovery, ownership, and tenant isolation are not implemented yet.
- The local JSON RAG index is rebuilt on startup but is not durable or tenant-aware; pgvector/object storage is planned.
- Heavy background work does not yet use a durable job queue or hybrid workers.
- Render free-tier cold starts can temporarily delay requests.
- Browser end-to-end, automated accessibility, load, and PostgreSQL integration coverage need expansion.
- Centralized monitoring, distributed tracing, alerting, backup drills, WAF policy, and security headers are planned.
- Several market adapters remain foundational and may use partial/manual fallback.
- Discovery and monitoring remain manually initiated in private/admin environments.
- Vast.ai automatic use for ordinary reports remains disabled.
- No wallet connection, custody, signing, or transaction execution exists.

## Next Product Phases

The consolidated roadmap defines:

1. V1 Phase 16 — Production identity, ownership, and quotas
2. V1 Phase 17 — Durable job queue and hybrid workers
3. V1 Phase 18 — Production RAG and knowledge storage
4. V1 Phase 19 — Production operations and security
5. V1 Phase 20 — Analytics, notifications, and commercial readiness
6. V1 Phase 21 — Model and research-intelligence expansion

See [`docs/development_plan.md`](development_plan.md) for the completion gates and detailed scope.
