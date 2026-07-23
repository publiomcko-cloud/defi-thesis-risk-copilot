# DeFi Thesis & Risk Copilot

[![CI](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/workflows/ci.yml)

A full-stack DeFi research and risk-analysis product that turns a strategy thesis into a structured, source-grounded report with deterministic risk scoring, visible assumptions, missing data, stress scenarios, and monitoring requirements.

The application demonstrates applied AI engineering without connecting wallets, signing transactions, holding funds, executing trades, allocating capital, or presenting personalized financial advice.

## Live Phase 15 Product

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
Completed: Phase 0, Post-MVP 1–12, Final 13–14, V1 Phases 15–16
In progress: V1 Phase 17 (17A–17B implemented on its branch)
Planned:   V1 Phases 18–22
```

The Phase 16 merge branch is:

```text
agent/v1-phase-16-identity-ownership
```

Phase 16 delivers managed identity, BFF, ownership, organization, quota, account, consent, retention, and frontend foundations. Its detailed implementation record is archived in [`docs/archive/v1_phase_16/`](docs/archive/v1_phase_16/). Phase 17A–17B adds the durable job foundation and authenticated queue control plane on `agent/v1-phase-17-durable-jobs`; worker execution remains intentionally unimplemented. The remaining live-provider and qualified legal release checks are tracked as final V1 Phase 22 work.

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
- Phase 16 user, organization, thesis, quota, anonymous-session, and account foundations on the merge branch.

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

Phase 15 deployment:

```text
Browser
  -> Vercel Next.js
  -> Render FastAPI
  -> Supabase PostgreSQL
```

Phase 16 target:

```text
Browser
  -> Vercel Next.js auth routes and BFF
  -> HttpOnly managed/anonymous cookies
  -> Render FastAPI token verification and authorization
  -> Supabase PostgreSQL ownership and quota data
```

Later phases add durable jobs/workers, object/vector storage, operations/security, commercial workflows, and evaluated model intelligence.

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

Controlled research/admin routes remain explicitly protected.

## Authoritative Documentation

- [Current state](docs/current_state.md) — deployed versus branch reality
- [Development plan](docs/development_plan.md) — roadmap and phase status
- [Archived Phase 16 records](docs/archive/v1_phase_16/) — implementation contract, execution plan, and deployment evidence
- [Future phase contracts](docs/future_phase_contracts.md) — full Phases 17–22 requirements
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
