# Deployment — DeFi Thesis & Risk Copilot

## 1. Deployment Goal

The deployment goal is to provide a portfolio-ready public demo with safe synthetic or read-only data.

Post-MVP Phases 10-12, Final Phase 13 local demo data, and Final Phase 14 public deployment preparation are implemented.

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

Public demo backend variables for Render:

```env
APP_ENV=portfolio_demo
PUBLIC_DEMO_MODE=true
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@<pooler-host>:6543/postgres?sslmode=require
FRONTEND_ORIGIN=https://<your-vercel-app>.vercel.app
DEFILLAMA_BASE_URL=https://api.llama.fi
AUTH_ENABLED=false
LLM_SYNTHESIS_ENABLED=false
LLM_PROVIDER=disabled
RAG_SEMANTIC_ENABLED=false
VAST_ENABLED=false
VAST_DRY_RUN=true
```

Public demo frontend variable for Vercel:

```env
NEXT_PUBLIC_API_BASE_URL=https://<your-render-service>.onrender.com
NEXT_PUBLIC_PUBLIC_DEMO_MODE=true
```

Local development variables are documented in `.env.example`.

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
- in `PUBLIC_DEMO_MODE=true`, provider credential create/update/delete endpoints are blocked

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

Local demo seed:

```bash
backend/.venv/bin/python backend/scripts/seed_demo_data.py
```

Then open:

```text
http://127.0.0.1:3000/demo
```

Production-like check:

```bash
docker compose config
docker compose -f docker-compose.production.yml config
```

## 8. Render Backend Setup

Use the included `render.yaml` as a safe starting point, or configure manually.

Render settings:

```text
Environment: Docker
Dockerfile path: ./Dockerfile.backend
Health check path: /health
Start command: Dockerfile default
```

The Dockerfile start command runs:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Required Render environment variables:

```env
APP_ENV=portfolio_demo
PUBLIC_DEMO_MODE=true
DATABASE_URL=<Supabase pooled Postgres URL>
FRONTEND_ORIGIN=https://<your-vercel-app>.vercel.app
AUTH_ENABLED=false
LLM_SYNTHESIS_ENABLED=false
LLM_PROVIDER=disabled
RAG_SEMANTIC_ENABLED=false
VAST_ENABLED=false
VAST_DRY_RUN=true
```

Optional safe metadata:

```env
APP_VERSION=0.1.0
DEPLOYMENT_COMMIT=<short-or-full-git-sha>
```

Free-tier notes:

- Render free services may sleep and cold-start slowly.
- The backend filesystem is not durable; use Supabase for persistent records.
- Demo seed avoids runtime example-report file writes when `PUBLIC_DEMO_MODE=true`.
- Do not configure real provider API keys for the public portfolio demo.

After deploy:

```bash
curl https://<your-render-service>.onrender.com/health
curl https://<your-render-service>.onrender.com/api/deployment/status
curl -X POST https://<your-render-service>.onrender.com/api/demo/seed
curl https://<your-render-service>.onrender.com/api/reports/demo_report_pendle_pt_loop
```

## 9. Vercel Frontend Setup

Recommended Vercel settings:

```text
Project root: frontend
Framework preset: Next.js
Build command: npm run build
Install command: npm install
Output: Next.js default
```

Required Vercel environment variables:

```env
NEXT_PUBLIC_API_BASE_URL=https://<your-render-service>.onrender.com
NEXT_PUBLIC_PUBLIC_DEMO_MODE=true
```

Backend CORS must match the deployed frontend:

```env
FRONTEND_ORIGIN=https://<your-vercel-app>.vercel.app
```

If the Render backend is asleep, the first frontend API request may show a temporary loading or fetch error until the backend wakes up. Refresh after the backend health endpoint responds.

## 10. Supabase Setup

Steps:

1. Create a Supabase project.
2. Copy the pooled Postgres connection string from project settings.
3. Use the pooler URL on Render as `DATABASE_URL`.
4. Ensure the URL includes SSL mode when required by Supabase.
5. Let Render run `alembic upgrade head` on startup, or run it manually from a trusted shell.
6. Seed demo data with `POST /api/demo/seed`.
7. Verify `GET /api/reports/demo_report_pendle_pt_loop`.

Typical pooled URL shape:

```text
postgresql://postgres.<project-ref>:<password>@<pooler-host>:6543/postgres?sslmode=require
```

If Supabase or a dashboard tool gives a URL containing `schema=public`, remove that query parameter before saving it on Render. The app also strips `schema` defensively because `psycopg` rejects it as an invalid connection option. Keep `sslmode=require`.

Do not commit Supabase credentials. Supabase free tier may pause, limit connections, or require manual project restoration after inactivity. Keep backups if the demo database matters.

## 11. Deployment Status Endpoint

The backend exposes:

```text
GET /api/deployment/status
```

It returns safe metadata only:

- app environment
- public demo mode
- database connectivity
- demo seed status
- auth/LLM/Vast/RAG safety flags
- version and optional commit

It does not return database URLs, API keys, bearer tokens, provider secrets, or credential values.

## 12. Public Demo Checklist

- Supabase project created.
- Render backend deployed.
- `DATABASE_URL` set from Supabase pooled Postgres.
- `FRONTEND_ORIGIN` set to the Vercel URL.
- Alembic migrations applied by Render startup or trusted shell.
- Demo seed executed.
- Vercel frontend deployed.
- `NEXT_PUBLIC_API_BASE_URL` set to the Render URL.
- CORS checked from the Vercel app.
- `/health` checked.
- `/api/deployment/status` checked.
- `/demo` checked.
- Example report opened.
- No secrets exposed in status/API responses.
- `VAST_ENABLED=false` and `VAST_DRY_RUN=true`.
- `LLM_SYNTHESIS_ENABLED=false` and `LLM_PROVIDER=disabled`.
- Provider credential mutation blocked in public demo mode.

## 13. Final Portfolio Deployment Phases

Final deployment order after Phases 10-14:

```text
Final Phase 15: Portfolio polish
```

The public demo should use safe examples, server-side secrets only, clear role boundaries, visible disclaimers, no wallet integration, and no transaction execution.
