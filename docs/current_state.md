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
- Frontend/backend integration: mocked analysis flow with persisted reports
- Testing and validation: pytest, smoke scripts, frontend lint/build
- Automation: GitHub Actions CI

Planned later stack additions:

- Public frontend hosting on Vercel
- Public backend hosting on Render
- Public database hosting on Supabase PostgreSQL
- Production vector storage such as pgvector, Qdrant, or Chroma
- Hosted or local LLM provider
- Higher-fidelity public market integrations beyond the initial adapter layer

## Implemented Features

Current status: Phase 8 complete; ready for Phase 9 report generation and Markdown export.

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

Initial implementation includes:

- FastAPI backend skeleton.
- `/health` endpoint.
- Mocked `/api/analyze` endpoint.
- Mocked report retrieval endpoint.
- Protocol listing endpoint for Pendle, Morpho, and Aave.
- Document ingestion endpoint refreshes the local curated RAG index from `knowledge_base/`.
- Mocked market data endpoint with explicit missing fields.
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
- Strategy input page wired to the mocked analysis endpoint.
- Report page that renders mocked backend report data.
- Protocols page for Pendle, Morpho, and Aave scope.
- About page with current phase and safety boundary.
- Reusable frontend components for strategy input, risk rating, report sections, sources, monitoring checklist, data summary, and disclaimers.
- Docker Compose services for backend, frontend, and PostgreSQL.
- Production-like Compose placeholder.

## MVP Features To Implement

- Higher-quality RAG embeddings or reranking.
- Deeper live market API coverage and provider-specific normalization.
- Real LLM-backed report generation.
- Markdown export.
- Dedicated report templates and export endpoints.
- Production deployment.

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

## Current Limitations

- The application is still an MVP and uses mocked analysis logic.
- Data adapters are basic MVP implementations; several protocol adapters still rely on manual fallback.
- RAG is local and curated only; it does not crawl protocol docs or refresh automatically.
- Embeddings are lightweight local hash embeddings, not semantic model embeddings.
- Risk scoring is deterministic and rule-based, but not a quantitative liquidation engine.
- Reports are persisted, but report writing is still template/mock based rather than LLM generated.
- `/api/documents/ingest` refreshes the local curated RAG index; it does not ingest arbitrary uploaded content yet.
- No deployed public demo exists yet.
- No wallet connection or transaction execution will be implemented in the MVP.
- Market data may still require manual fallback inputs during early development.
- The controlled workflow is deterministic and internal; it is not a multi-agent autonomous system.
