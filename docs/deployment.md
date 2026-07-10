# Deployment — DeFi Thesis & Risk Copilot

## 1. Deployment Goal

The deployment goal is to provide a portfolio-ready public demo with safe synthetic or read-only data.

The MVP should not require paid APIs.

## 2. Recommended Public Deployment

```text
Vercel
  -> Next.js frontend

Render
  -> FastAPI backend

Supabase
  -> PostgreSQL database

Vector storage
  -> pgvector, Qdrant, or Chroma

LLM provider
  -> Ollama for local demo
  -> OpenAI-compatible provider for hosted demo, optional
```

## 3. Environment Variables

Example variables:

```env
APP_ENV=development
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/defi_copilot
VECTOR_DB_PROVIDER=pgvector
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_COMPATIBLE_API_KEY=
OPENAI_COMPATIBLE_BASE_URL=
COINGECKO_API_KEY=
DEFILLAMA_BASE_URL=https://api.llama.fi
```

## 4. Local Docker

Development:

```bash
docker compose up -d --build
curl http://127.0.0.1:8000/health
```

Production-like check:

```bash
docker compose config
docker compose -f docker-compose.production.yml config
```

`docker-compose.production.yml` defaults to local SQLite and `http://127.0.0.1:8000` for configuration testing. Real hosted deployments should override `DATABASE_URL` and `NEXT_PUBLIC_API_BASE_URL`.

Local Docker services:

- `backend`: FastAPI app, Alembic migration on startup, mounted backend source, mounted read-only `knowledge_base/`.
- `frontend`: Next.js development server with persistent `node_modules` and `.next` volumes.
- `postgres`: local PostgreSQL database on host port `5435`.

The local Compose file overrides `DATABASE_URL` so the backend talks to the Compose PostgreSQL service. Manual backend execution uses the application default SQLite database unless a local `.env` overrides it.

## 5. Deployment Safety

The deployed demo should:

- use synthetic examples
- avoid wallet connection
- avoid transaction execution
- avoid collecting sensitive user data
- clearly display disclaimers
- avoid storing private financial information

## 6. Future Deployment Improvements

Future versions may add:

- authentication
- saved reports
- user-specific watchlists
- background workers
- scheduled ingestion
- Redis queue
- hosted vector database
- monitoring and logging
- usage limits
- paid plans
