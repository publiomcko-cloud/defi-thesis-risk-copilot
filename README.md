# DeFi Thesis & Risk Copilot

[![CI](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/workflows/ci.yml)

AI-powered DeFi research and risk analysis copilot for protocol theses, yield strategies, lending markets, and structured risk reports.

DeFi Thesis & Risk Copilot combines generative AI, RAG, protocol documentation, market data adapters, agentic workflows, and rule-based risk scoring to help users analyze complex DeFi strategies before execution.

## Portfolio Description

Full-stack AI and DeFi portfolio app with FastAPI, Next.js, RAG, LLM agents, vector search, market data integrations, risk scoring, and structured report generation.

## Live Portfolio Demo

- Frontend: pending
- Backend health: pending
- API docs: pending
- Demo video: pending
- Downloadable walkthrough: pending

The first public demo should use synthetic examples and read-only public data. The application does not connect wallets, sign transactions, execute trades, or custody funds.

## Demo Safety

- No wallet connection is implemented in the MVP.
- No transaction execution is implemented.
- No private keys, seed phrases, or user funds are handled.
- Market data may be delayed, incomplete, or simulated.
- Reports are for research and educational purposes only.
- The system does not provide financial, investment, legal, or tax advice.

## For Recruiters

DeFi Thesis & Risk Copilot is designed to demonstrate applied AI engineering judgment, not only isolated chatbot behavior.

It demonstrates:

1. Retrieval-augmented generation over protocol documentation.
2. Agentic workflow orchestration for research, data collection, risk scoring, and report writing.
3. DeFi domain modeling around Pendle, Morpho, Aave, lending markets, fixed-yield assets, collateral risk, and liquidation risk.
4. Backend API design with typed schemas and modular services.
5. Frontend product flow for analysis input, report review, and portfolio-ready demo screens.
6. Dockerized local development.
7. Documentation-first engineering with architecture, testing, deployment, and roadmap notes.

Recommended review path:

1. Read the README and project case study.
2. Open the demo dashboard.
3. Submit the example Pendle + Morpho strategy prompt.
4. Review the generated risk report.
5. Inspect the retrieved sources and assumptions.
6. Review the backend API docs.
7. Inspect the repository architecture and future implementation plan.

## For Clients

This project models how a crypto research team, DeFi community, analyst, or advanced user could use AI to standardize strategy review before capital allocation.

Client-facing value:

- structured DeFi research reports
- repeatable strategy risk analysis
- source-backed protocol explanations
- monitoring checklist generation
- risk classification without trade execution
- safe educational workflow for complex strategies
- extensible architecture for custom dashboards, watchlists, and alerts

## What It Demonstrates

- FastAPI backend with modular agents, data adapters, RAG, and risk services
- Next.js frontend with strategy input, report page, and dashboard-oriented UX
- RAG over protocol documentation and internal DeFi risk notes
- LLM agent workflow for protocol research, data collection, calculation, and report generation
- Rule-based risk scoring for DeFi strategies
- Public data integrations such as DefiLlama, CoinGecko, Morpho, Aave, and future Dune/The Graph adapters
- Structured report generation with assumptions, risks, missing data, sources, and disclaimers
- Docker-based local execution
- Future-ready structure for PyTorch fine-tuning, reranking, SLURM, and HPC batch processing

## Core Demo Flow

```text
strategy input
  -> protocol detection
  -> RAG source retrieval
  -> market data lookup
  -> risk scoring
  -> stress scenario generation
  -> structured report
  -> markdown export
```

Example prompt:

```text
Analyze a hypothetical Pendle PT strategy using Morpho borrow. Evaluate fixed yield, borrow cost, liquidity, oracle risk, liquidation risk, exit before maturity, and monitoring checklist.
```

## Screenshots

Screenshots should be added after the first UI implementation.

| Strategy input | Risk report |
| --- | --- |
| ![Strategy input](docs/screenshots/01-strategy-input.png) | ![Risk report](docs/screenshots/02-risk-report.png) |

| Sources panel | Risk dashboard |
| --- | --- |
| ![Sources panel](docs/screenshots/03-sources-panel.png) | ![Risk dashboard](docs/screenshots/04-risk-dashboard.png) |

## Deployment Architecture

```text
Browser
  -> Vercel Next.js frontend
  -> Render FastAPI backend
  -> Supabase PostgreSQL
  -> Vector database or pgvector
  -> Optional hosted LLM provider
```

Local development can run with Docker Compose using PostgreSQL, vector storage, backend, frontend, and an optional local Ollama service.

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

## Important Endpoints

Planned MVP endpoints:

- `GET /health`
- `POST /api/analyze`
- `GET /api/reports/{report_id}`
- `GET /api/protocols`
- `POST /api/documents/ingest`
- `POST /api/risk-score`
- `POST /api/market-data/fetch`
- `POST /api/reports/{report_id}/export`

## Documentation

- [Changelog](CHANGELOG.md)
- [Current state](docs/current_state.md)
- [Architecture](docs/architecture.md)
- [MVP scope](docs/mvp_scope.md)
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

- The MVP does not execute trades.
- The MVP does not connect wallets.
- The MVP does not provide personalized financial advice.
- Market data may be incomplete or delayed.
- Some protocol-specific metrics may require manual input in the MVP.
- Risk scoring starts as rule-based and should not be treated as a quantitative guarantee.
- RAG answers depend on the quality and freshness of ingested documents.
- No production authentication or billing system is included in the MVP.

## Roadmap

- Implement MVP analysis workflow for Pendle, Morpho, and Aave.
- Add documentation ingestion and vector search.
- Add DefiLlama and CoinGecko adapters.
- Add Morpho and Aave market data adapters.
- Add markdown report export.
- Add watchlist and alerts.
- Add strategy simulator.
- Add Derive options and volatility analysis.
- Add PyTorch-based risk classifier.
- Add reranker fine-tuning for better RAG retrieval.
- Add SLURM and Apptainer support for HPC batch jobs.

## License

This project is intended to be available under the MIT License.
