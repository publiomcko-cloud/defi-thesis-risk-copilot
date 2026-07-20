# DeFi Thesis & Risk Copilot

[![CI](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/workflows/ci.yml)

A full-stack DeFi research and risk-analysis product that turns a strategy thesis into a structured, source-grounded report with deterministic risk scoring, visible assumptions, missing data, stress scenarios, and monitoring requirements.

The application demonstrates applied AI engineering without connecting wallets, signing transactions, holding funds, executing trades, or presenting personalized financial advice.

## Live Product

- Frontend: https://defi-thesis-risk-copilot.vercel.app
- Guided demo: https://defi-thesis-risk-copilot.vercel.app/demo
- Main example report: https://defi-thesis-risk-copilot.vercel.app/reports/demo_report_pendle_pt_loop
- Backend: https://defi-thesis-risk-copilot.onrender.com
- Backend readiness: https://defi-thesis-risk-copilot.onrender.com/ready
- Deployment status: https://defi-thesis-risk-copilot.onrender.com/api/deployment/status
- API documentation: https://defi-thesis-risk-copilot.onrender.com/docs
- Source repository: https://github.com/publiomcko-cloud/defi-thesis-risk-copilot

The Render free-tier service may require a short cold start. The frontend includes readiness links and retry states for this condition.

## Product Capabilities

- structured DeFi strategy reports
- curated retrieval over protocol documentation and internal risk notes
- public and manual market-data adapters
- deterministic rule-based risk scoring
- visible assumptions, missing data, confidence, and source provenance
- lending-loop and fixed-yield stress simulation
- crypto options and volatility analysis
- source discovery and evaluation
- human review before knowledge-base trust
- explicit, human-approved discovery-to-RAG ingestion
- watchlists and rule-based in-app alerts
- Markdown report export with copy and download actions
- optional local or OpenAI-compatible model synthesis
- optional, admin-only Vast.ai dry-run/manual warm-up infrastructure
- ML, retrieval-evaluation, and HPC groundwork

## Public Deployment Safety

The hosted portfolio environment is intentionally constrained.

### Public read-only workflows

Visitors may inspect:

- demo status and scenarios
- supported protocols
- seeded reports
- discovery candidates
- review outcomes
- ingested-source metadata
- seeded watchlist and alert data
- safe deployment metadata

### Public bounded compute

Visitors may run bounded and rate-limited:

- strategy analysis
- deterministic simulation
- options analysis
- market-data lookup

Do not submit wallet information, private positions, credentials, confidential research, or personally identifying information. The current hosted demo uses a shared demonstration database.

### Blocked in public mode

Public visitors cannot:

- run discovery or monitoring jobs
- create evaluations
- change review status
- ingest content into RAG
- create or modify watchlists and alerts
- ingest documents
- view audit events
- view or change provider credentials
- control Vast.ai sessions
- receive an administrator identity

## Architecture

```text
Browser
  -> Vercel Next.js frontend
  -> Render FastAPI API
  -> Supabase PostgreSQL

Render startup
  -> Alembic migrations
  -> deterministic demo seed
  -> curated RAG index build
  -> Uvicorn
```

Core analysis workflow:

```text
strategy input
  -> strategy parser
  -> curated retrieval
  -> public/manual market-data adapters
  -> deterministic risk scoring
  -> stress scenarios
  -> structured report
  -> persistence
  -> Markdown export
```

Controlled knowledge workflow:

```text
public/manual discovery
  -> normalization and deduplication
  -> deterministic evaluation
  -> human review
  -> approved_for_rag
  -> explicit private/admin ingestion
  -> curated knowledge record
  -> RAG refresh
```

## Key Engineering Decisions

### Deterministic fields remain authoritative

Optional LLM providers can improve explanatory wording, but cannot overwrite:

- risk rating or score
- market values
- missing-data fields
- protocol identities
- source references
- disclaimers

### Discovery does not imply trust

Automatically discovered sources remain candidates until evaluated and human-approved. Approval and ingestion are separate actions.

### Heavy infrastructure is optional

The normal product works without an LLM, GPU rental, wallet, private key, or paid API. Vast.ai support is disabled and dry-run by default.

### Public and private product boundaries are separate

The public environment exposes safe read-only workflows and bounded compute. Privileged mutations require a private authenticated deployment.

## Guided Review Path

For a quick technical review:

1. Open the [guided demo](https://defi-thesis-risk-copilot.vercel.app/demo).
2. Open the seeded Pendle and Morpho risk report.
3. Inspect assumptions, missing data, deterministic rating, sources, and export.
4. Try the simulator and options workflow.
5. Open the read-only review and watchlist demonstrations.
6. Inspect the [API documentation](https://defi-thesis-risk-copilot.onrender.com/docs).
7. Read the [architecture](docs/architecture.md) and [consolidated development plan](docs/development_plan.md).

## Technology Stack

### Backend

- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL / Supabase
- httpx
- cryptography
- pytest

### Frontend

- Next.js App Router
- React
- TypeScript
- responsive global CSS
- Vercel

### Infrastructure and research tooling

- Docker and Docker Compose
- Render
- Supabase
- GitHub Actions
- local Markdown RAG index
- optional Ollama and OpenAI-compatible providers
- optional Vast.ai lifecycle foundation
- optional SLURM and Apptainer templates

## Local Quick Start

Copy the environment template:

```bash
cp .env.example .env
```

Start the complete stack:

```bash
docker compose up -d --build
```

Verify:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

Open:

```text
Frontend: http://127.0.0.1:3000
Demo: http://127.0.0.1:3000/demo
Backend: http://127.0.0.1:8000
API docs: http://127.0.0.1:8000/docs
```

In local mode, deterministic demo data can be seeded manually:

```bash
backend/.venv/bin/python backend/scripts/seed_demo_data.py
```

or:

```bash
curl -X POST http://127.0.0.1:8000/api/demo/seed
```

The hosted public deployment seeds automatically during backend startup and blocks the public seed endpoint.

## Manual Development Setup

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

Retrieval evaluation:

```bash
cd backend
python scripts/evaluate_retrieval.py --retriever hybrid
```

## Important API Routes

### Service and demo

- `GET /`
- `GET /health`
- `GET /ready`
- `GET /api/deployment/status`
- `GET /api/demo/status`
- `GET /api/demo/scenarios`
- `POST /api/demo/seed` — private/local only

### Analysis and reports

- `POST /api/analyze`
- `GET /api/reports/{report_id}`
- `POST /api/reports/{report_id}/export`
- `GET /api/protocols`
- `POST /api/market-data/fetch`
- `POST /api/simulation/run`
- `POST /api/options/analyze`

### Controlled research workflows

- `GET /api/discovery/candidates`
- `POST /api/discovery/run` — blocked publicly
- `GET /api/evaluation/review-items`
- `POST /api/evaluation/discovered-items/{id}/evaluate` — blocked publicly
- `PATCH /api/evaluation/review-items/{id}` — blocked publicly
- `POST /api/evaluation/review-items/{id}/ingest-to-rag` — blocked publicly
- `GET /api/knowledge-base/discovered`

### Watchlists and administration

- `GET /api/watchlist/items`
- `GET /api/watchlist/alerts`
- watchlist mutations — blocked publicly
- provider credential routes — private/admin only
- audit-event routes — private/admin only
- Vast.ai routes — private/admin only

## Documentation

- [Consolidated development plan](docs/development_plan.md) — authoritative roadmap and phase history
- [Current state](docs/current_state.md)
- [Architecture](docs/architecture.md)
- [Deployment](docs/deployment.md)
- [Testing](docs/testing.md)
- [Demo walkthrough](docs/demo_walkthrough.md)
- [RAG design](docs/rag_design.md)
- [Agent design](docs/agent_design.md)
- [Risk framework](docs/risk_framework.md)
- [Data sources](docs/data_sources.md)
- [Changelog](CHANGELOG.md)

The former Post-MVP and Phase 10-12 plan files now redirect to the consolidated plan. Their full historical content remains available in Git history.

## Current Roadmap

Completed work is documented through V1 Phase 15. V1 Phase 16 identity, ownership, and quota hardening is in progress.

V1 Phase 16 is adding:

- Supabase Auth JWT validation with secure-cookie frontend foundations
- local application users, explicit platform roles, organizations, and memberships
- private reports, watchlists, alerts, and saved theses foundations
- isolated anonymous demo sessions
- durable daily product-usage quotas
- account export/deletion, retention cleanup, terms/privacy, and consent records

Future real-product phases cover:

- durable jobs and hybrid local/cloud workers
- durable object and vector storage
- production observability and security
- analytics, notifications, organizations, and commercial readiness
- expanded model and research intelligence

See [docs/development_plan.md](docs/development_plan.md) for the complete plan and release gates.

## Safety Boundary

- no wallet connection
- no transaction signing
- no custody
- no automated trade execution
- no private-key or seed-phrase handling
- no guaranteed-return language
- no model override of deterministic risk fields
- no automatic trust of discovered content
- no live Vast.ai rental in automated tests

All output is research-oriented and educational. Market data may be delayed, incomplete, cached, simulated, or manually entered.
