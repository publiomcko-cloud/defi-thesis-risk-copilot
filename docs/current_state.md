# Current State — DeFi Thesis & Risk Copilot

This document describes the current public portfolio state of DeFi Thesis & Risk Copilot.

Historical planning notes should be kept in `docs/archive/`.

## Public Demo

- Frontend: pending
- Backend health: pending
- API docs: pending
- Demo video: pending

## Current Stack

Current local stack:

- Frontend: Next.js App Router, TypeScript, global CSS
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic
- Local database: SQLite by default; PostgreSQL supported through `DATABASE_URL` and Docker Compose
- Local RAG: curated markdown knowledge base, header-aware chunking, local hash embeddings, JSON vector store
- Frontend/backend integration: controlled analysis workflow with persisted reports
- Testing and validation: pytest, smoke scripts, frontend lint/build
- Automation: GitHub Actions CI

Planned product-expansion additions:

- Automated evaluation pipeline with human review queue
- Strategy simulator
- Watchlists and in-app alerts
- Options and volatility analysis workflow
- Advanced RAG with semantic embeddings, hybrid retrieval, reranking, and evaluation
- Fine-tuning and ML risk classifier groundwork
- Optional HPC and SLURM support

Planned final portfolio additions:

- Public frontend hosting on Vercel
- Public backend hosting on Render
- Public database hosting on Supabase PostgreSQL
- Public demo screenshots and video
- Portfolio-ready case study and README polish

## Implemented Features

Current status: Post-MVP Phase 2 complete. Optional backend LLM synthesis and manual source monitoring are available, with deterministic fallback and human-review boundaries preserved.

The original MVP phases 11, 12, and 13 are intentionally deferred until after the product-expansion phases because they are demo data, deployment, and portfolio-polish work.

Initial documentation includes:

- README
- MVP scope
- architecture document
- data source plan
- RAG design
- agent design
- risk framework
- testing plan
- deployment plan
- portfolio readiness checklist
- demo script
- post-MVP development plan
- LLM synthesis validation record

Initial implementation includes:

- FastAPI backend skeleton.
- `/health` endpoint.
- `/api/analyze` endpoint runs the controlled MVP analysis workflow.
- Report retrieval endpoint returns persisted structured reports.
- Protocol listing endpoint for Pendle, Morpho, and Aave.
- Document ingestion endpoint refreshes the local curated RAG index from `knowledge_base/`.
- Market data endpoint with adapter aggregation and explicit missing fields.
- Pydantic request and response schemas for initial backend contracts.
- SQLAlchemy database foundation.
- Alembic migration setup with initial tables.
- Database-backed analysis request and report persistence.
- Curated local knowledge base for Pendle, Morpho, Aave, Chainlink, and internal risk notes.
- Lightweight local RAG ingestion, chunking, embedding, JSON vector storage, retrieval, and citation formatting.
- Retrieval evaluation script for the MVP RAG questions.
- Analysis workflow can include retrieved local knowledge-base sources when the RAG index exists.
- Market data adapter interface and service layer.
- Manual, Pendle, Morpho, Aave, DefiLlama, and CoinGecko adapters with normalized outputs.
- Market data cache fallback using the existing `market_data_cache` table.
- `/api/market-data/fetch` returns aggregated adapter data, assumptions, and explicit missing fields.
- Analysis reports include a market data summary section.
- Rule-based MVP risk scoring engine.
- Visible risk score components, confidence level, and main risk drivers.
- Stress scenario generation.
- Monitoring checklist generation.
- Analysis reports use deterministic risk scoring instead of the earlier placeholder rating.
- Controlled internal analysis orchestration.
- Strategy parser, protocol research, market data, risk scoring, and report writer agent modules.
- `/api/analyze` now runs the controlled workflow before persisting the report.
- Environment-based backend settings.
- Backend pytest setup.
- Backend smoke check script.
- Next.js App Router frontend.
- Shared frontend API/type definitions.
- Home page with portfolio-oriented call to action.
- Strategy input page wired to the controlled analysis endpoint.
- Report page that renders persisted backend report data.
- Dedicated report template with required sections for strategy description, mechanics, yield source, market data, assumptions, risk analysis, stress scenarios, exit plan, monitoring, rating, uncertainty, sources, and disclaimer.
- Markdown report rendering and `/api/reports/{report_id}/export` endpoint.
- Frontend Markdown export action for generated reports.
- Protocols page for Pendle, Morpho, and Aave scope.
- About page with current phase and safety boundary.
- Reusable frontend components for strategy input, risk rating, report sections, sources, monitoring checklist, data summary, and disclaimers.
- Docker Compose services for backend, frontend, and PostgreSQL.
- Backend and frontend Dockerfiles.
- Docker Compose build wiring for local backend, frontend, and PostgreSQL services.
- Production-like Compose configuration check.
- CI workflow for backend tests, frontend lint/build, and Compose validation.
- Optional backend LLM synthesis with Ollama and OpenAI-compatible provider abstractions.
- Local Ollama validation record for `llama3.2:3b` on GTX 1050 Ti hardware.
- Source watch and discovered item database models.
- Manual source monitoring endpoints: `/api/monitoring/run` and `/api/monitoring/discovered-items`.
- Normalized discovered items for Pendle, Morpho, Aave, DefiLlama, documentation, governance, and risk/audit candidates.
- Duplicate discovery detection through stable discovery keys.
- Monitoring failure recording on source watches.
- Discovered items default to `needs_review` and are not automatically ingested into RAG.

## Active Product Development To Implement

The next active product phases are:

1. Automated evaluation pipeline and review queue.
2. Strategy simulator.
3. Watchlists and in-app alerts.
4. Options and volatility analysis workflow.
5. Advanced RAG and retrieval evaluation.
6. Fine-tuning and ML risk classifier groundwork.
7. HPC and SLURM readiness.

After these product-expansion phases, return to:

1. Final Phase 11 — Demo data and example reports.
2. Final Phase 12 — Public portfolio deployment.
3. Final Phase 13 — Portfolio polish.

## Current Validation Commands

Backend validation:

```bash
cd backend
source .venv/bin/activate
python -m pytest -q
python scripts/run_smoke_checks.py
```

Frontend validation:

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

Docker validation:

```bash
docker compose config
docker compose -f docker-compose.production.yml config
```

LLM validation:

See `docs/llm_synthesis_validation.md` for the local Ollama test record, observed issues, and results.

## Current Limitations

- The application is still an MVP and uses deterministic local analysis logic.
- Data adapters are basic MVP implementations; several protocol adapters still rely on manual fallback.
- RAG is local and curated only; it does not crawl protocol docs or refresh automatically.
- Source monitoring is manually triggered and creates review candidates only; it does not approve or ingest sources.
- Initial monitoring collectors are deterministic discovery candidates, not full live crawlers for every source.
- Embeddings are lightweight local hash embeddings, not semantic model embeddings.
- Risk scoring is deterministic and rule-based, but not a quantitative liquidation engine.
- Reports are persisted and rendered through a deterministic template; optional LLM synthesis can enrich explanatory wording when enabled, but cannot override deterministic risk scoring, missing data, sources, market values, protocols, or disclaimers.
- `/api/documents/ingest` refreshes the local curated RAG index; it does not ingest arbitrary uploaded content yet.
- Source monitoring, review queues, watchlists, alerts, strategy simulation, and options analysis are not implemented yet.
- No deployed public demo exists yet.
- No wallet connection or transaction execution will be implemented.
- Market data may still require manual fallback inputs during early development.
- The controlled workflow is deterministic and internal; it is not a multi-agent autonomous system.
