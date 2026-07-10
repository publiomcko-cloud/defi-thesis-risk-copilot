# Development Plan — DeFi Thesis & Risk Copilot

This plan turns the documentation-first project into a working portfolio-ready MVP.

The guiding product rule is simple: the app must not behave like a trading bot. It is a research and risk copilot that retrieves sources, normalizes available data, marks uncertainty, applies deterministic risk rules, and then generates a structured report.

## Milestone 0 — Repository and Planning Baseline

Status: completed.

Goal: create a clean source-controlled project foundation with enough documentation to guide implementation.

Deliverables:

- Git repository initialized on `main`.
- README imported and committed.
- Architecture, MVP scope, data source, RAG, agent, risk, testing, deployment, demo, and portfolio docs imported.
- `.gitignore` created for archives, Python artifacts, Node artifacts, env files, logs, and editor state.
- Documentation archive preserved under `docs/archive/`.

Acceptance criteria:

- `git status` is clean after the initial documentation commit.
- Docs are available from the project root.
- The MVP boundaries are clear: no wallet connection, no transaction signing, no trade execution, and no paid API requirement.

## Milestone 1 — Project Scaffold and Local Runtime

Goal: create the runnable full-stack skeleton before implementing AI behavior.

Backend deliverables:

- Create `backend/` FastAPI application.
- Add Python dependency management with `requirements.txt` or `pyproject.toml`.
- Add `app/main.py` with application startup.
- Add `GET /health`.
- Add core settings module for environment variables.
- Add structured logging and error response conventions.
- Add initial pytest setup.

Frontend deliverables:

- Create `frontend/` Next.js App Router project with TypeScript.
- Add Tailwind CSS.
- Add a usable first screen for strategy analysis.
- Add shared API client and frontend type definitions.
- Add lint and build scripts.

Infrastructure deliverables:

- Add `docker-compose.yml`.
- Add backend service.
- Add frontend service.
- Add PostgreSQL service using a port that does not conflict with existing local containers.
- Add `.env.example`.
- Add local startup notes to README.

Suggested local ports:

- Frontend: `3000`
- Backend: `8000`
- Project PostgreSQL host port: `5435`

Acceptance criteria:

- `docker compose up -d --build` starts local services.
- `GET http://127.0.0.1:8000/health` returns healthy status.
- `npm run lint` and `npm run build` pass in `frontend/`.
- `python -m pytest -q` passes in `backend/`.

## Milestone 2 — Backend Domain Models and API Contracts

Goal: define typed contracts before wiring complex workflows.

Deliverables:

- Add Pydantic models for strategy analysis requests.
- Add Pydantic models for normalized strategy data.
- Add Pydantic models for market data summaries.
- Add Pydantic models for risk scores.
- Add Pydantic models for report sections.
- Add in-memory report persistence for the first iteration.
- Add planned API routes:
  - `GET /api/protocols`
  - `POST /api/analyze`
  - `GET /api/reports/{report_id}`
  - `POST /api/risk-score`
  - `POST /api/market-data/fetch`
  - `POST /api/reports/{report_id}/export`

Initial protocol scope:

- Pendle
- Morpho
- Aave
- Chainlink as supporting oracle context

Acceptance criteria:

- OpenAPI docs are available at `/docs`.
- API schemas clearly show assumptions, missing data, sources, and disclaimers.
- Smoke checks cover health, protocols, analyze, report retrieval, and markdown export.

## Milestone 3 — Rule-Based Risk Scoring MVP

Goal: implement deterministic risk scoring before adding LLM-generated reports.

Deliverables:

- Add `backend/app/risk/framework.py`.
- Add `backend/app/risk/scoring.py`.
- Add `backend/app/risk/scenarios.py`.
- Implement the first point-based scoring system:
  - base risk
  - multi-protocol use
  - leverage
  - volatile collateral
  - variable borrow APY
  - low or unknown liquidity
  - secondary-market exit dependency
  - unclear oracle setup
  - maturity timing risk
  - incentive dependency
  - incomplete documentation or data
- Map scores to:
  - Conservative
  - Moderate
  - Aggressive
  - Very Risky
- Generate stress scenario warnings.
- Generate monitoring checklist items.

Acceptance criteria:

- Risk score output is deterministic.
- Tests cover single-protocol, multi-protocol, leveraged, missing liquidity, variable borrow, oracle uncertainty, and maturity risk cases.
- Every risk score includes score explanation, main risk drivers, missing data, confidence level, and disclaimer.

## Milestone 4 — Market Data and Manual Fallbacks

Goal: make data handling explicit, normalized, and honest about uncertainty.

Deliverables:

- Add adapter interface in `backend/app/data_sources/base.py`.
- Add manual adapter for user-provided fields.
- Add DefiLlama adapter for TVL/protocol metadata/yield context.
- Add CoinGecko adapter for token price and market data.
- Add Morpho adapter for markets, vaults, LLTV, APY, utilization, and oracle metadata when available.
- Add Aave adapter or stub for reserve data, supply rates, borrow rates, liquidation thresholds, and Health Factor concepts.
- Add Pendle adapter or manual-first fallback for PT price, implied APY, maturity, and liquidity.
- Add cache layer for API responses.
- Add normalized data quality metadata:
  - source name
  - fetch timestamp
  - freshness
  - confidence
  - missing fields
  - manual overrides
  - assumptions

Acceptance criteria:

- Live API failure does not break analysis.
- If live data is unavailable, the workflow uses cache, manual fields, or marks values as unknown.
- Reports never present missing or estimated data as verified fact.
- Tests cover adapter normalization and fallback behavior.

## Milestone 5 — Curated Knowledge Base and RAG Ingestion

Goal: ground protocol explanations in source-backed documentation.

Deliverables:

- Add `knowledge_base/` with curated source documents:
  - `pendle/`
  - `morpho/`
  - `aave/`
  - `chainlink/`
  - `internal_notes/`
- Add document loader.
- Add text cleaning.
- Add markdown-header-aware or semantic chunking.
- Add metadata extraction:
  - protocol
  - source URL
  - document title
  - section title
  - ingestion date
  - content type
  - risk category
  - version or source date when available
- Add embeddings using Hugging Face sentence-transformers.
- Add local vector storage using Chroma or pgvector.
- Add retriever that returns chunks, metadata, similarity score, and protocol labels.
- Add `scripts/ingest_demo_docs.py`.
- Add `scripts/evaluate_retrieval.py`.

Acceptance criteria:

- RAG evaluation retrieves useful context for:
  - What is a Pendle PT?
  - What is LLTV in Morpho?
  - What is Health Factor in Aave?
  - What is oracle risk?
  - What is liquidation risk?
  - What happens near PT maturity?
- Retrieval results include citations and source metadata.
- The app can explain when the knowledge base has insufficient context.

## Milestone 6 — Controlled Agent Workflow

Goal: implement the MVP analysis flow as a controlled orchestration pipeline.

Deliverables:

- Add `backend/app/agents/orchestrator.py`.
- Add protocol detection from strategy text.
- Add strategy parsing and normalization.
- Add retrieval step for protocol documentation.
- Add market data lookup step.
- Add missing-data detection.
- Add risk scoring step.
- Add report writing step.
- Add safe LLM integration:
  - Ollama local provider first
  - OpenAI-compatible provider as optional future configuration
- Add prompt template that includes:
  - user request
  - normalized strategy data
  - retrieved context
  - market data summary
  - risk scoring output
  - required report structure
  - safety rules
  - citation instructions

Control rules:

- Do not execute trades.
- Do not connect wallets.
- Do not recommend direct buy or sell actions.
- Do not hide missing data.
- Do not present uncertain data as fact.
- Do not ignore source limitations.

Acceptance criteria:

- `POST /api/analyze` completes the full workflow for the demo Pendle + Morpho prompt.
- The workflow produces a saved report ID.
- The report includes sources, assumptions, missing data, risk rating, monitoring checklist, stress scenarios, and disclaimer.
- LLM output is constrained by retrieved context and deterministic risk scoring.

## Milestone 7 — Report Generation and Markdown Export

Goal: produce a professional structured report that can be reviewed, shared, and exported.

Deliverables:

- Add report templates.
- Add report renderer.
- Add markdown export.
- Add report persistence in PostgreSQL.
- Add source citation formatting.
- Add report sections:
  - executive summary
  - protocols involved
  - strategy mechanics
  - yield source
  - market data summary
  - assumptions
  - missing data
  - risk analysis
  - stress scenarios
  - exit plan
  - monitoring checklist
  - risk rating
  - sources
  - disclaimer

Acceptance criteria:

- Every generated report contains all required sections.
- Markdown export is deterministic and readable.
- Report tests validate section presence, source presence, missing-data handling, and disclaimer presence.

## Milestone 8 — Frontend Product MVP

Goal: build the usable user-facing workflow.

Deliverables:

- Implement strategy input page.
- Add protocol selector.
- Add optional market URL input.
- Add manual parameter fields for MVP data gaps:
  - PT price
  - implied APY
  - maturity date
  - borrow APY
  - collateral amount
  - debt amount
  - target LTV
  - estimated slippage
  - pool liquidity
- Add loading and error states.
- Add report page.
- Add risk rating display.
- Add data summary table.
- Add missing data warnings.
- Add sources panel.
- Add monitoring checklist.
- Add markdown export action.
- Add protocols page or compact protocol overview.

Acceptance criteria:

- User can submit the demo prompt from the UI.
- User can review risk rating, sources, assumptions, and report sections.
- User can export markdown.
- Frontend build and lint pass.
- UI clearly communicates that this is research only and does not execute trades.

## Milestone 9 — Database, Migrations, and Persistence

Goal: move beyond in-memory state while keeping local development simple.

Deliverables:

- Add SQLAlchemy models.
- Add Alembic migrations.
- Store analysis requests.
- Store generated reports.
- Store report sections or report JSON.
- Store source metadata.
- Store market data snapshots.
- Store ingested document metadata.
- Add database session management.

Acceptance criteria:

- `alembic upgrade head` initializes the database.
- Reports survive backend restarts.
- Tests can run against an isolated test database or SQLite fallback.

## Milestone 10 — Docker, CI, and Developer Experience

Goal: make the project easy to run and review.

Deliverables:

- Complete Dockerfiles for backend and frontend.
- Complete `docker-compose.yml`.
- Add optional production-like compose config.
- Add `scripts/run_smoke_checks.py`.
- Add GitHub Actions CI:
  - backend tests
  - frontend lint
  - frontend build
  - Docker Compose config validation
- Update README quick start.
- Add troubleshooting notes for occupied ports and missing Ollama models.

Acceptance criteria:

- A reviewer can clone the repo and run the local app with documented commands.
- CI passes on GitHub.
- Smoke checks pass locally.

## Milestone 11 — Portfolio Demo Readiness

Goal: make the project legible and impressive for recruiters, clients, and technical reviewers.

Deliverables:

- Add screenshots:
  - strategy input
  - risk report
  - sources panel
  - risk dashboard
- Add an example generated Pendle + Morpho report.
- Add a short demo video using synthetic/read-only data.
- Add live frontend link when deployed.
- Add backend health link when deployed.
- Add public API docs link when deployed.
- Update README live demo section.
- Update portfolio readiness checklist.
- Add clear known limitations section.

Acceptance criteria:

- A 2-4 minute demo can show the complete workflow:
  - strategy prompt
  - RAG retrieval
  - data summary
  - risk scoring
  - structured report
  - markdown export
- README guides recruiters and clients through the strongest review path.
- The project clearly communicates practical AI engineering rather than generic chatbot behavior.

## Milestone 12 — Public Deployment

Goal: deploy a safe public demo with synthetic examples and read-only data.

Deliverables:

- Deploy frontend to Vercel.
- Deploy backend to Render.
- Deploy PostgreSQL to Supabase or equivalent.
- Configure vector storage with pgvector, Chroma, or Qdrant.
- Configure environment variables:
  - `APP_ENV`
  - `DATABASE_URL`
  - `VECTOR_DB_PROVIDER`
  - `LLM_PROVIDER`
  - `OLLAMA_BASE_URL`
  - optional OpenAI-compatible provider variables
  - `DEFILLAMA_BASE_URL`
  - optional `COINGECKO_API_KEY`
- Add deployment safety copy.
- Add public health endpoint.

Acceptance criteria:

- Public frontend is accessible.
- Public backend health endpoint is accessible.
- API docs are accessible if safe to expose.
- The demo uses synthetic examples and does not collect sensitive information.

## Milestone 13 — Post-MVP Product Expansion

Goal: extend the product after the MVP is stable and demonstrable.

Potential expansions:

- Watchlists for protocols, assets, and strategies.
- Alerts for borrow APY, TVL, liquidity, maturity, or governance changes.
- Strategy simulator.
- Portfolio-level risk aggregation.
- Scheduled documentation refresh.
- Hybrid search and reranking.
- Citation validation and answer faithfulness evaluation.
- Dune and The Graph adapters.
- Chainlink price feed integration.
- Governance forum ingestion.
- Audit report ingestion.
- Options analysis.
- Learned risk classifier using PyTorch and Hugging Face.
- Fine-tuned reranker.
- Background worker and queue.
- Authentication and saved user reports.

Acceptance criteria:

- Future features remain optional and do not destabilize the MVP.
- Safety boundaries remain explicit.
- Each expansion has its own tests, data quality rules, and documentation.

## Recommended Build Order

1. Scaffold backend and frontend.
2. Implement health, protocols, typed schemas, and smoke checks.
3. Implement deterministic risk scoring.
4. Implement manual data fallback and public data adapters.
5. Implement RAG ingestion and retrieval.
6. Implement controlled analysis orchestrator.
7. Implement report renderer and markdown export.
8. Build the frontend workflow.
9. Add database persistence.
10. Dockerize and add CI.
11. Polish portfolio assets.
12. Deploy public demo.

## Definition of MVP Done

The MVP is done when a user can submit the demo Pendle + Morpho strategy and receive a structured source-backed report that includes:

- executive summary
- protocols involved
- strategy mechanics
- yield source
- market data summary
- assumptions
- missing data
- risk analysis
- stress scenarios
- exit plan
- monitoring checklist
- risk rating
- sources
- disclaimer
- markdown export

The app must run locally with Docker Compose, pass backend tests, pass frontend lint/build, and have enough documentation for a technical reviewer to understand the architecture and tradeoffs.
