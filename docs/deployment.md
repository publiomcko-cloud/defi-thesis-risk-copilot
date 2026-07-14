# Deployment — DeFi Thesis & Risk Copilot

## 1. Deployment Goal

The deployment goal is to provide a portfolio-ready public demo with safe synthetic or read-only data.

Post-MVP Phases 10-12 are implemented. Public deployment remains a final portfolio phase after demo data and polish are stable.

## 2. Recommended Public Deployment

```text
Vercel
  -> Next.js frontend

Render or comparable backend host
  -> FastAPI backend

Supabase or managed PostgreSQL
  -> PostgreSQL database

Vector storage
  -> local JSON for MVP, pgvector/Qdrant/Chroma later

LLM provider
  -> disabled by default
  -> Ollama for local demo
  -> OpenAI-compatible API for hosted demo when configured
  -> Vast.ai ephemeral provider only for admin-triggered heavy tasks
```

## 3. Environment Variables

Core variables:

```env
APP_ENV=development
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/defi_copilot
FRONTEND_ORIGIN=http://127.0.0.1:3000
DEFILLAMA_BASE_URL=https://api.llama.fi
LLM_PROVIDER=disabled
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_COMPATIBLE_BASE_URL=
OPENAI_COMPATIBLE_API_KEY=
```

Phase 10 discovery variables:

```env
DISCOVERY_ENABLED=false
DISCOVERY_DEFAULT_MIN_TVL_USD=5000000
DISCOVERY_DEFAULT_MIN_POOL_TVL_USD=500000
DISCOVERY_REQUIRE_HUMAN_APPROVAL=true
```

Phase 11 access-control variables:

```env
AUTH_ENABLED=false
ADMIN_EMAIL=admin@example.local
ADMIN_BOOTSTRAP_TOKEN=
ADMIN_PASSWORD=
AUTH_SECRET_KEY=
CREDENTIAL_ENCRYPTION_KEY=
```

Phase 12 Vast.ai variables:

```env
VAST_ENABLED=false
VAST_API_BASE_URL=https://console.vast.ai/api/v0
VAST_API_KEY=
VAST_CREDENTIAL_NAME=vast_ai_default
VAST_MAX_HOURLY_COST_USD=0.50
VAST_MAX_SESSION_MINUTES=30
VAST_MAX_ACTIVE_INSTANCES=1
VAST_GPU_ALLOWLIST=RTX_4090,RTX_3090,A5000,A6000
VAST_MIN_GPU_RAM_GB=16
VAST_DISK_GB=40
VAST_REQUIRE_VERIFIED=true
VAST_AUTO_DESTROY=true
VAST_IDLE_TIMEOUT_SECONDS=300
VAST_IMAGE=
VAST_MODEL=
VAST_CONTAINER_PORT=8000
VAST_STARTUP_TIMEOUT_SECONDS=600
VAST_POLL_INTERVAL_SECONDS=10
VAST_DRY_RUN=true
```

## 4. Secret Handling

Secrets must be server-side only.

Rules:

- never expose `VAST_API_KEY` or model provider keys to the frontend
- never log full API keys
- store raw keys in environment variables or through the admin provider-credential API
- database-stored credentials keep encrypted secrets plus non-sensitive metadata only
- show only provider name, created time, status, and last four characters in admin UI
- require admin role for credential creation, rotation, testing, and deletion
- keep audit logs for credential and Vast lifecycle actions
- replace the MVP credential encryption helper with managed secret storage or KMS-backed encryption before hosted production use

## 5. Access Control

Two roles are implemented for MVP/local use:

```text
admin
common
```

Common users can:

- create strategy analyses
- view their own reports if ownership is implemented
- run simulations and options analysis
- manage their own watchlist items
- view public/approved knowledge-base context

Admin users can:

- use the bootstrap/admin bearer-token flow
- run DefiLlama/manual discovery
- evaluate discovered items
- approve/reject review items
- ingest approved items into RAG
- manage provider credentials
- view access audit logs
- start, inspect, test, destroy, and clean up dry-run/manual Vast.ai sessions

## 6. Vast.ai Deployment Safety

Vast.ai integration defaults to disabled and dry-run mode defaults to enabled.

The implemented version supports manual admin-triggered startup before automatic ephemeral rental. Normal report generation does not auto-rent Vast.ai instances.

Required safeguards:

- max hourly cost
- max runtime
- max one active instance by default
- verified/allowlisted GPU criteria where possible
- strict timeout handling
- auto-destroy in cleanup/finally paths
- emergency cleanup endpoint
- lifecycle log table
- no common-user access to rent/destroy remote GPU instances

Stopping an instance is not enough for the default safety posture; the default workflow should destroy the instance after the task unless an admin intentionally keeps it warm.

## 7. Local Docker

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

## 8. Final Portfolio Deployment Phases

Final deployment order after Phases 10-12:

```text
Final Phase 13: Demo data and example reports
Final Phase 14: Public portfolio deployment
Final Phase 15: Portfolio polish
```

The public demo should use safe examples, server-side secrets only, clear role boundaries, visible disclaimers, no wallet integration, and no transaction execution.
