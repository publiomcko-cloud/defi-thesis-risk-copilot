# Current State — DeFi Thesis & Risk Copilot

This document describes the current public portfolio state of DeFi Thesis & Risk Copilot.

Historical planning notes should be kept in `docs/archive/`.

## Public Demo

- Frontend: pending
- Backend health: pending
- API docs: pending
- Demo video: pending

## Current Stack

Planned MVP stack:

- Frontend hosting: Vercel
- Backend hosting: Render
- Database hosting: Supabase PostgreSQL
- Vector storage: pgvector, Qdrant, or Chroma
- Frontend: Next.js App Router, TypeScript, Tailwind CSS
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL
- RAG: LlamaIndex or LangChain
- Embeddings: Hugging Face sentence-transformers
- LLM provider: Ollama local or OpenAI-compatible API
- Data sources: DefiLlama, CoinGecko, Morpho, Aave, and manual fallback data
- Testing and validation: pytest, smoke scripts, frontend lint/build
- Automation: GitHub Actions CI

## Implemented Features

Current status: repository foundation stage.

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
- Mocked document ingestion endpoint.
- Mocked market data endpoint with explicit missing fields.
- Pydantic request and response schemas for initial backend contracts.
- SQLAlchemy database foundation.
- Alembic migration setup with initial tables.
- Database-backed analysis request and report persistence.
- Curated local knowledge base for Pendle, Morpho, Aave, Chainlink, and internal risk notes.
- Lightweight local RAG ingestion, chunking, embedding, vector storage, retrieval, and citation formatting.
- Retrieval evaluation script for the MVP RAG questions.
- Analysis workflow can include retrieved local knowledge-base sources when the RAG index exists.
- Environment-based backend settings.
- Backend pytest setup.
- Backend smoke check script.
- Minimal Next.js App Router frontend.
- Shared frontend API/type placeholders.
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
- Rule-based risk scoring.
- Basic market data adapters.
- Report generation.
- Markdown export.
- Database persistence.
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

- The application is only scaffolded.
- Data adapters are planned but not built.
- RAG ingestion is planned but not built.
- Analysis, report generation, and persistence are planned but not built.
- No deployed public demo exists yet.
- No wallet connection or transaction execution will be implemented in the MVP.
- Risk scoring will initially be rule-based.
- Market data may require manual fallback inputs during early development.
