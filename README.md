# DeFi Thesis & Risk Copilot

[![CI](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/workflows/ci.yml)

A full-stack DeFi research and risk-analysis product that turns a strategy thesis into a structured, source-grounded report with deterministic risk scoring, visible assumptions, missing data, stress scenarios, and monitoring requirements.

The application demonstrates applied AI engineering without connecting wallets, signing transactions, holding funds, executing trades, allocating capital, or presenting personalized financial advice.

## Live Product

- Frontend: https://defi-thesis-risk-copilot.vercel.app
- Guided demo: https://defi-thesis-risk-copilot.vercel.app/demo
- Example report: https://defi-thesis-risk-copilot.vercel.app/reports/demo_report_pendle_pt_loop
- Backend: https://defi-thesis-risk-copilot.onrender.com
- Readiness: https://defi-thesis-risk-copilot.onrender.com/ready
- Deployment status: https://defi-thesis-risk-copilot.onrender.com/api/deployment/status
- API docs: https://defi-thesis-risk-copilot.onrender.com/docs

The Render free-tier backend may cold-start after inactivity.

## Current Phase Status

```text
Completed: Phase 0, Post-MVP 1–12, Final 13–14, V1 Phases 15–18
In progress: V1 Phase 19 (19A-19I operations/security foundations, recovery verification, supply-chain controls, incident response, isolated failure exercises, and controlled durable-RAG rollout checks)
Planned:   V1 Phases 20–22
```

Phases 16 and 17 are complete on `main`. Phase 16 delivers managed identity,
BFF, ownership, organization, quota, account, consent, retention, and frontend
foundations. Phase 17 adds durable jobs, internal workers, asynchronous
authenticated analysis, a private jobs workspace, and the administrator-only
server-profiled Vast job. Their implementation records are archived in
[`docs/archive/v1_phase_16/`](docs/archive/v1_phase_16/) and
[`docs/archive/v1_phase_17/`](docs/archive/v1_phase_17/).

Phase 18 is complete and merged into `main`; its implementation, correction,
validation, migration, and cutover record is preserved in
[`docs/archive/v1_phase_18/`](docs/archive/v1_phase_18/). Its eight slices are
implemented, but production storage remains disabled by default:
durable knowledge metadata, private-storage interfaces, tenant authorization,
authenticated source/document APIs, bounded upload handling, and the
feature-gated `document.ingest.v1` worker path are present. Versioned local-only
pgvector embedding generations and an authenticated tenant-safe shadow
retrieval/citation diagnostic are also implemented but disabled by default.
Phase 18G adds an operator-only, convergent importer for the checked-in curated
Markdown corpus, whole-import object compensation, fail-closed collision checks,
and scheduled declared-lineage precision/recall/citation evaluation. The local
top-1 gate includes an expected-empty case; it is quality evidence only, not a
production cutover. It also adds a guarded
durable report path. When explicitly enabled, authenticated analysis derives
approved public, caller-owned private, and active-organization scope server-side;
anonymous analysis remains public-only. JSON remains the automatic fallback.
Phase 18H adds the authenticated Knowledge workspace, document/version lifecycle
controls, exact report-citation lineage display, safe private-knowledge export
metadata, and administrator-only readiness metrics. Phase 19 is now active and
may gather controlled deployment, observability, and shadow-mode evidence. Live
private-bucket policy, final cutover verification, and launch approval remain
Phase 22 gates.
Durable source versions
support atomic rollback and queued cleanup after tombstoning; those lifecycle
controls remain inactive until private storage is deliberately enabled.

## Product Capabilities

- structured DeFi strategy reports;
- curated protocol retrieval;
- public and manual market-data adapters;
- deterministic risk scoring;
- visible assumptions, missing data, confidence, and provenance;
- lending-loop and fixed-yield stress simulation;
- long call/put payoff analysis;
- discovery and deterministic evaluation;
- human review before knowledge trust;
- explicit approved-source ingestion;
- watchlists and in-app alerts;
- Markdown export;
- optional local/OpenAI-compatible synthesis;
- admin-controlled Vast.ai dry-run/manual warm-up;
- retrieval, ML, and HPC groundwork;
- user, organization, thesis, quota, anonymous-session, account, and durable-job foundations.

## Public Deployment Safety

The deployed public portfolio environment is intentionally constrained.

Visitors may inspect public demo records and run bounded analysis, simulation, options, and market-data flows.

Public visitors cannot:

- run monitoring or global discovery;
- create evaluations;
- change review state;
- ingest documents or RAG content;
- mutate watchlists or alerts;
- access credentials or audit records;
- control Vast.ai sessions;
- receive administrator identity.

Do not submit sensitive personal, wallet, credential, private-position, or confidential research data to the public demo.

## Architecture

Current deployment:

```text
Browser
  -> Vercel Next.js
  -> Render FastAPI
  -> Supabase PostgreSQL
```

Authenticated architecture:

```text
Browser
  -> Vercel Next.js auth routes and BFF
  -> HttpOnly managed/anonymous cookies
  -> Render FastAPI token verification and authorization
  -> Supabase PostgreSQL ownership and quota data
```

Phase 18 adds private object/vector storage and durable ingestion. Later phases
add operations/security, commercial workflows, and evaluated model intelligence.

See [`docs/architecture.md`](docs/architecture.md).

## Permanent Engineering Decisions

### Deterministic values remain authoritative

Model wording cannot silently replace:

- risk rating or score;
- market values;
- assumptions or missing data;
- protocol identity;
- source references;
- disclaimers.

### Discovery does not imply trust

```text
discovery
  -> evaluation
  -> human review
  -> approved_for_rag
  -> explicit ingestion
```

### Identity does not imply authorization

Managed identity establishes who the user is. The application database establishes:

- platform role;
- account status;
- plan;
- resource owner;
- organization membership;
- visibility;
- quota.

### Heavy infrastructure remains optional and controlled

Normal deterministic analysis does not require an LLM, GPU rental, wallet, private key, or paid provider.

## Local Quick Start

```bash
cp .env.example .env
docker compose up -d --build
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

Open:

```text
Frontend: http://127.0.0.1:3000
Demo:     http://127.0.0.1:3000/demo
Backend:  http://127.0.0.1:8000
API docs: http://127.0.0.1:8000/docs
```

## Manual Development

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Validation

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
```

Compose:

```bash
docker compose config
docker compose -f docker-compose.production.yml config
```

Phase-specific migration, browser, concurrency, worker, retrieval, security, and deployment checks are defined in [`docs/testing.md`](docs/testing.md) and the phase contracts.

## Important Routes

Service/demo:

- `GET /`
- `GET /health`
- `GET /ready`
- `GET /api/deployment/status`
- `GET /api/demo/status`
- `GET /api/demo/scenarios`

Analysis:

- `POST /api/analyze`
- `GET /api/reports/{report_id}`
- `POST /api/reports/{report_id}/export`
- `POST /api/market-data/fetch`
- `POST /api/simulation/run`
- `POST /api/options/analyze`

Phase 16 foundations:

- `/api/auth/*`
- `/api/account*`
- `/api/organizations*`
- `/api/theses*`
- `/api/usage`
- `/api/consents`

Phase 17 foundations:

- `/api/jobs*`
- `/internal/workers/*` (trusted workers only; blocked by the browser BFF)

Controlled research/admin routes remain explicitly protected.

## Authoritative Documentation

- [Current state](docs/current_state.md) — deployed versus branch reality
- [Development plan](docs/development_plan.md) — roadmap and phase status
- [Archived Phase 16 records](docs/archive/v1_phase_16/) — implementation contract, execution plan, and deployment evidence
- [Archived Phase 17 records](docs/archive/v1_phase_17/) — execution and validation evidence
- [Archived Phase 18 records](docs/archive/v1_phase_18/) — implementation, validation, and cutover evidence
- [Phase 19 execution plan](docs/phase_19_execution_plan.md) — active implementation authority
- [Phase 19 monitoring runbook](docs/operations/monitoring_and_alerting.md) — local monitoring and external rollout gates
- [Phase 19 backup/restore runbook](docs/operations/backup_restore_runbook.md) — isolated recovery drill and retention guard
- [Phase 19 secret inventory](docs/operations/secret_inventory.md) — secret ownership and rotation boundaries
- [Phase 19 incident runbooks](docs/operations/incidents/) — versioned containment and recovery procedures with safe tabletop scripts
- [Phase 19 failure exercises](docs/operations/failure_exercises.md) — fixed isolated test catalog and rollback boundaries
- [Future phase contracts](docs/future_phase_contracts.md) — full Phases 19–22 requirements
- [Agent execution guide](docs/agent_execution_guide.md) — short-prompt workflow
- [Architecture](docs/architecture.md)
- [Deployment](docs/deployment.md)
- [Testing](docs/testing.md)
- [Demo walkthrough](docs/demo_walkthrough.md)
- [RAG design](docs/rag_design.md)
- [Agent design](docs/agent_design.md)
- [Risk framework](docs/risk_framework.md)
- [Data sources](docs/data_sources.md)
- [Changelog](CHANGELOG.md)

## Short Agent Prompt

Future phase work can use:

```text
Implement V1 Phase <N> on a new branch from current main.
Read docs/current_state.md, docs/development_plan.md,
the relevant phase contract, docs/architecture.md, docs/deployment.md,
docs/testing.md, and docs/agent_execution_guide.md.
Follow the contract exactly, preserve completed behavior, run all required
checks, update the docs, commit logically, push the branch, open a draft PR,
and do not merge.
```

## Safety Boundary

- no wallet connection;
- no transaction signing;
- no custody;
- no automated trade execution;
- no secret-key handling;
- no guaranteed-return language;
- no model override of deterministic risk fields;
- no automatic trust of discovered content;
- no live Vast rental in automated tests.

All output is research-oriented and educational. Market data may be delayed, incomplete, cached, simulated, or manually entered.
