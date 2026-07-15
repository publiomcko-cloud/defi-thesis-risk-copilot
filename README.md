# DeFi Thesis & Risk Copilot

[![CI](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/workflows/ci.yml)

AI-powered DeFi research and risk analysis copilot for protocol theses, yield strategies, lending markets, source-grounded reports, and controlled research workflows.

DeFi Thesis & Risk Copilot combines RAG, protocol documentation, market data adapters, controlled agentic workflows, rule-based risk scoring, optional LLM synthesis, review queues, simulations, watchlists, options analysis, and ML/HPC groundwork to help users analyze complex DeFi strategies before execution.

## Portfolio Description

Full-stack AI and DeFi portfolio app with FastAPI, Next.js, RAG, controlled agent workflows, market data integrations, deterministic risk scoring, structured report generation, Docker, CI, and a post-MVP roadmap for controlled discovery-to-RAG ingestion and optional ephemeral GPU model infrastructure.

## Current Status

The technical MVP and product-expansion phases are complete through Final Phase 14:

```text
Post-MVP Phase 1: Optional backend LLM synthesis
Post-MVP Phase 2: Source monitoring and discovery
Post-MVP Phase 3: Automated evaluation pipeline and review queue
Post-MVP Phase 4: Strategy simulator
Post-MVP Phase 5: Watchlist and alerts
Post-MVP Phase 6: Options and volatility analysis agent
Post-MVP Phase 7: Advanced RAG and retrieval evaluation
Post-MVP Phase 8: Fine-tuning and ML risk classifier groundwork
Post-MVP Phase 9: HPC and SLURM readiness
Post-MVP Phase 10: Auto-discovery and human-approved RAG ingestion
Post-MVP Phase 11: Access control and secure provider configuration
Post-MVP Phase 12: Vast.ai ephemeral model provider
Final Phase 13: Demo data and example reports
Final Phase 14: Public portfolio deployment preparation
```

Before final portfolio polish, the next planned product phase is:

```text
Final Phase 15: Portfolio polish
```

See [`docs/post_mvp_development_plan.md`](docs/post_mvp_development_plan.md) and [`docs/phase_10_12_expansion_plan.md`](docs/phase_10_12_expansion_plan.md).

## Live Portfolio Demo

- Frontend: `https://<your-vercel-app>.vercel.app`
- Backend health: `https://<your-render-service>.onrender.com/health`
- Deployment status: `https://<your-render-service>.onrender.com/api/deployment/status`
- API docs: `https://<your-render-service>.onrender.com/docs`
- Demo video: pending
- Downloadable walkthrough: local demo walkthrough available in [`docs/demo_walkthrough.md`](docs/demo_walkthrough.md)

The public demo is designed for synthetic examples and read-only public data. The application does not connect wallets, sign transactions, execute trades, or custody funds.

Recommended free-tier deployment:

```text
Vercel frontend
  -> Render FastAPI backend
  -> Supabase pooled Postgres
```

Public demo defaults:

```env
PUBLIC_DEMO_MODE=true
AUTH_ENABLED=false
LLM_SYNTHESIS_ENABLED=false
LLM_PROVIDER=disabled
VAST_ENABLED=false
VAST_DRY_RUN=true
RAG_SEMANTIC_ENABLED=false
```

## Local Portfolio Demo

Final Phase 13 adds deterministic demo data, a `/demo` dashboard, and example reports that can be reproduced without paid APIs, wallets, or real Vast.ai rental.

Seed the local demo data:

```bash
backend/.venv/bin/python backend/scripts/seed_demo_data.py
```

Or, while the backend is running, call:

```bash
curl -X POST http://127.0.0.1:8000/api/demo/seed
```

Open:

```text
Demo dashboard: http://127.0.0.1:3000/demo
Main demo report: http://127.0.0.1:3000/reports/demo_report_pendle_pt_loop
Example Markdown reports: examples/reports/
```

## Demo Safety

- No wallet connection is implemented.
- No transaction execution is implemented.
- No private keys, seed phrases, or user funds are handled.
- Market data may be delayed, incomplete, cached, user-provided, or simulated.
- Reports are for research and educational purposes only.
- The system does not provide financial, investment, legal, or tax advice.
- Discovery-to-RAG ingestion keeps human approval and explicit admin ingestion before knowledge-base updates.
- Vast.ai integration is admin-only, server-side, cost-limited, runtime-limited, dry-run by default, and disabled by default.

## For Recruiters

DeFi Thesis & Risk Copilot is designed to demonstrate applied AI engineering judgment, not only isolated chatbot behavior.

It demonstrates:

1. Retrieval-augmented generation over protocol documentation.
2. Controlled agent workflow orchestration for research, data collection, risk scoring, and report writing.
3. DeFi domain modeling around Pendle, Morpho, Aave, lending markets, fixed-yield assets, collateral risk, options risk, and liquidation risk.
4. Backend API design with typed schemas and modular services.
5. Frontend product flow for analysis input, report review, simulation, watchlists, options, and portfolio-ready demo screens.
6. Dockerized local development and CI.
7. Documentation-first engineering with architecture, testing, deployment, and roadmap notes.
8. Security-aware planning for admin/common roles, provider secrets, and ephemeral GPU infrastructure.

Recommended review path:

1. Read the README and project case study.
2. Seed demo data with the script or `/api/demo/seed`.
3. Open the `/demo` dashboard.
4. Review the seeded Pendle + Morpho report.
5. Inspect retrieved sources and assumptions.
6. Try discovery/review, simulation, watchlist, options, and Vast dry-run pages.
7. Inspect the repository architecture and post-MVP development plan.

## For Clients

This project models how a crypto research team, DeFi community, analyst, or advanced user could use AI to standardize strategy review before capital allocation.

Client-facing value:

- structured DeFi research reports
- repeatable strategy risk analysis
- source-backed protocol explanations
- monitoring checklist generation
- risk classification without trade execution
- deterministic strategy simulation
- options and volatility scenario framing
- safe educational workflow for complex strategies
- extensible architecture for controlled source discovery, human review, knowledge-base ingestion, watchlists, alerts, and optional remote model infrastructure

## What It Demonstrates

- FastAPI backend with modular agents, data adapters, RAG, and risk services
- Next.js frontend with strategy input, report page, and dashboard-oriented UX
- RAG over protocol documentation and internal DeFi risk notes
- Controlled workflow for protocol research, data collection, risk scoring, and report generation
- Rule-based risk scoring for DeFi strategies
- Public data integrations and adapter fallbacks for DefiLlama, CoinGecko, Pendle, Morpho, Aave, and manual inputs
- Structured report generation with assumptions, risks, missing data, sources, and disclaimers
- Markdown export
- Strategy simulation, watchlists, options analysis, retrieval evaluation, ML groundwork, and HPC templates
- Docker-based local execution and CI validation
- Human-approved discovery-to-RAG ingestion, MVP role-based access control, server-side provider credential metadata, audit logs, and admin-only Vast.ai dry-run/manual warm-up sessions

## Core Demo Flow

```text
strategy input
  -> protocol detection
  -> RAG source retrieval
  -> market data lookup
  -> risk scoring
  -> stress scenario generation
  -> structured report
  -> optional LLM synthesis
  -> markdown export
```

Planned expanded demo flow:

```text
DefiLlama/manual discovery
  -> discovered candidate
  -> automated evaluation
  -> human review
  -> admin approved_for_rag
  -> explicit ingest-to-RAG
  -> future report cites ingested knowledge
```

Example prompt:

```text
Analyze a hypothetical Pendle PT strategy using Morpho borrow. Evaluate fixed yield, borrow cost, liquidity, oracle risk, liquidation risk, exit before maturity, and monitoring checklist.
```

## Screenshots

Evaluation screenshots are available in `docs/screenshots/evaluation/`.

| Home | Analyze |
| --- | --- |
| ![Home](docs/screenshots/evaluation/01-home.png) | ![Analyze](docs/screenshots/evaluation/05-analyze-filled-inputs.png) |

| Report | Markdown export |
| --- | --- |
| ![Report](docs/screenshots/evaluation/06-report-output.png) | ![Markdown export](docs/screenshots/evaluation/07-markdown-export-output.png) |

## Deployment Architecture

```text
Browser
  -> Vercel Next.js frontend
  -> Render FastAPI backend
  -> Supabase PostgreSQL
  -> Vector database or pgvector
  -> LLM disabled by default in public demo
  -> Vast.ai disabled or dry-run only in public demo
```

Local development can run with Docker Compose using PostgreSQL, backend, frontend, local RAG files, and optional local LLM services.

## Local Quick Start

Start the local Docker services:

```bash
docker compose up -d --build
```

Verify the app:

```bash
curl http://127.0.0.1:8000/health
```

Open:

```text
Frontend: http://127.0.0.1:3000
Backend health: http://127.0.0.1:8000/health
API docs: http://127.0.0.1:8000/docs
```

Stop the local stack:

```bash
docker compose down
```

Manual backend setup, using the default local SQLite database:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Manual frontend setup:

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
python -m pytest -q
python scripts/run_smoke_checks.py
```

Optional LLM synthesis is disabled by default. To test it locally, set `LLM_SYNTHESIS_ENABLED=true` and configure either Ollama or an OpenAI-compatible provider. LLM output may improve explanatory wording, but deterministic risk scoring, missing data, sources, market values, and disclaimers remain authoritative.

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

RAG validation:

```bash
cd backend
python scripts/evaluate_retrieval.py
```

Production-like Docker configuration check:

```bash
docker compose config
docker compose -f docker-compose.production.yml config
```

Public deployment setup is documented in [`docs/deployment.md`](docs/deployment.md). After deploying the backend and running migrations, seed the hosted demo with:

```bash
curl -X POST https://<your-render-service>.onrender.com/api/demo/seed
```

## Important Endpoints

Current endpoints include:

- `GET /health`
- `POST /api/analyze`
- `GET /api/reports/{report_id}`
- `POST /api/reports/{report_id}/export`
- `GET /api/protocols`
- `GET /api/deployment/status`
- `GET /api/demo/status`
- `GET /api/demo/scenarios`
- `POST /api/demo/seed`
- `POST /api/documents/ingest`
- `POST /api/market-data/fetch`
- `POST /api/monitoring/run`
- `GET /api/monitoring/discovered-items`
- `POST /api/evaluation/discovered-items/{discovered_item_id}/evaluate`
- `GET /api/evaluation/review-items`
- `PATCH /api/evaluation/review-items/{review_item_id}`
- `POST /api/evaluation/review-items/{review_item_id}/ingest-to-rag`
- `POST /api/discovery/run`
- `GET /api/discovery/candidates`
- `GET /api/knowledge-base/discovered`
- `GET /api/auth/me`
- `POST /api/admin/provider-credentials`
- `GET /api/admin/provider-credentials`
- `PATCH /api/admin/provider-credentials/{credential_id}`
- `DELETE /api/admin/provider-credentials/{credential_id}`
- `GET /api/admin/audit-events`
- `POST /api/simulation/run`
- `POST /api/watchlist/items`
- `POST /api/watchlist/items/{watchlist_item_id}/evaluate`
- `GET /api/watchlist/alerts`
- `POST /api/options/analyze`
- `GET /api/admin/vast/config`
- `POST /api/admin/vast/config`
- `POST /api/admin/vast/sessions/start`
- `GET /api/admin/vast/sessions`
- `GET /api/admin/vast/sessions/{session_id}`
- `POST /api/admin/vast/sessions/{session_id}/test-prompt`
- `POST /api/admin/vast/sessions/{session_id}/destroy`
- `POST /api/admin/vast/cleanup`

## Documentation

- [Changelog](CHANGELOG.md)
- [Current state](docs/current_state.md)
- [Architecture](docs/architecture.md)
- [MVP scope](docs/mvp_scope.md)
- [Post-MVP development plan](docs/post_mvp_development_plan.md)
- [Phase 10-12 expansion plan](docs/phase_10_12_expansion_plan.md)
- [Case study](docs/case_study.md)
- [Data sources](docs/data_sources.md)
- [RAG design](docs/rag_design.md)
- [Agent design](docs/agent_design.md)
- [Risk framework](docs/risk_framework.md)
- [Demo architecture](docs/demo_architecture.md)
- [Demo script](docs/demo_script.md)
- [Deployment](docs/deployment.md)
- [Testing](docs/testing.md)
- [Portfolio readiness](docs/portfolio_readiness.md)
- [Development plan](docs/development_plan.md)

Archive:

- [Historical development plan](docs/archive/development_plan.md)

## Known Limitations

- The application does not execute trades.
- The application does not connect wallets.
- The application does not provide personalized financial advice.
- Market data may be incomplete, cached, delayed, or user-provided.
- Some protocol-specific metrics still require manual input.
- Risk scoring is rule-based and should not be treated as a quantitative guarantee.
- RAG answers depend on the quality and freshness of ingested documents.
- Review approval does not ingest sources automatically; an explicit admin ingest action is required.
- MVP token access control is implemented for admin-only workflows when `AUTH_ENABLED=true`; hosted production auth, MFA, ownership scoping, and password reset are not implemented.
- Vast.ai manual warm-up is implemented with dry-run enabled by default; automatic Vast use for normal report generation is not enabled.
- No production billing system is included.

## Roadmap

Completed product foundation:

- Implement MVP analysis workflow for Pendle, Morpho, and Aave.
- Add documentation ingestion and local retrieval.
- Add market data adapter layer.
- Add deterministic risk scoring.
- Add controlled agent orchestration.
- Add structured report generation and Markdown export.
- Add Docker and CI.
- Add optional LLM synthesis, source monitoring, evaluation queue, discovery-to-RAG ingestion, MVP access control, provider credential metadata, audit logs, Vast.ai dry-run/manual warm-up, simulation, watchlists, options analysis, advanced RAG, ML groundwork, and HPC templates.

Final portfolio phases:

- Phase 13: Demo data and example reports.
- Phase 14: Public portfolio deployment preparation.
- Phase 15: Portfolio polish.

## License

This project is intended to be available under the MIT License.
