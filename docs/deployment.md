# Deployment — DeFi Thesis & Risk Copilot

## 1. Live Deployment

```text
Vercel Next.js frontend
  -> Render FastAPI backend
  -> Supabase PostgreSQL
```

Live services:

- Frontend: `https://defi-thesis-risk-copilot.vercel.app`
- Demo: `https://defi-thesis-risk-copilot.vercel.app/demo`
- Backend: `https://defi-thesis-risk-copilot.onrender.com`
- Liveness: `https://defi-thesis-risk-copilot.onrender.com/health`
- Readiness: `https://defi-thesis-risk-copilot.onrender.com/ready`
- Deployment status: `https://defi-thesis-risk-copilot.onrender.com/api/deployment/status`
- OpenAPI: `https://defi-thesis-risk-copilot.onrender.com/docs`

## 2. Hosted Public-Demo Posture

Required backend settings:

```env
APP_ENV=portfolio_demo
APP_VERSION=1.0.0
PUBLIC_DEMO_MODE=true
DATABASE_URL=<Supabase pooled PostgreSQL URL>
FRONTEND_ORIGIN=https://defi-thesis-risk-copilot.vercel.app
AUTH_ENABLED=false
LLM_SYNTHESIS_ENABLED=false
LLM_PROVIDER=disabled
RAG_SEMANTIC_ENABLED=false
VAST_ENABLED=false
VAST_DRY_RUN=true
DEPLOYMENT_COMMIT=<Git commit SHA>
```

Required frontend settings:

```env
NEXT_PUBLIC_API_BASE_URL=https://defi-thesis-risk-copilot.onrender.com
NEXT_PUBLIC_PUBLIC_DEMO_MODE=true
```

`AUTH_ENABLED=false` does not make hosted visitors administrators. When public-demo mode is enabled, the unauthenticated identity is a common read-only visitor.

## 3. Public Endpoint Policy

### Public read-only

- `GET /`
- `GET /health`
- `GET /ready`
- `GET /api/deployment/status`
- `GET /api/demo/status`
- `GET /api/demo/scenarios`
- `GET /api/protocols`
- `GET /api/reports/{id}`
- `GET /api/discovery/candidates`
- `GET /api/evaluation/review-items`
- `GET /api/knowledge-base/discovered`
- `GET /api/watchlist/items`
- `GET /api/watchlist/alerts`

### Public bounded compute

- `POST /api/analyze`
- `POST /api/market-data/fetch`
- `POST /api/simulation/run`
- `POST /api/options/analyze`

These routes have bounded request schemas and an in-process per-client rate limit in the current single-instance deployment.

### Blocked in public-demo mode

- public demo reseed/reset
- document ingestion
- source monitoring runs
- global discovery runs
- evaluation creation
- review mutations
- RAG ingestion
- watchlist and alert mutations
- credential reads/writes
- audit logs
- Vast.ai session controls

## 4. Render Startup

The Docker image starts with:

```bash
alembic upgrade head \
  && python -m scripts.prepare_runtime \
  && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`prepare_runtime.py` performs an idempotent synthetic demo seed and builds the curated RAG index when `PUBLIC_DEMO_MODE=true`.

Render configuration:

```text
Environment: Docker
Dockerfile: ./Dockerfile.backend
Health check: /ready
Start command: Dockerfile default
```

The public seed endpoint is intentionally blocked. Hosted data is prepared at startup instead.

## 5. Health Model

- `/health` is liveness: the Python process is responding.
- `/ready` is readiness: PostgreSQL is reachable and the public RAG index exists.
- `/api/deployment/status` is safe UI metadata: environment, DB state, demo seed, model/Vast/RAG flags, version, and commit.

No health/status response includes database URLs, passwords, provider keys, bearer tokens, or stored secrets.

## 6. Vercel Setup

Recommended settings:

```text
Project root: frontend
Framework: Next.js
Install: npm install
Build: npm run build
Output: .next
```

Do not configure `public` as the output directory. The included `frontend/vercel.json` uses `.next`.

The frontend:

- uses the Render API URL from `NEXT_PUBLIC_API_BASE_URL`;
- hides administrator navigation in public mode;
- exposes retry and backend-readiness actions for cold starts;
- labels the hosted environment as shared, synthetic, and read-only for privileged workflows.

## 7. Supabase Setup

1. Create a Supabase project.
2. Copy the pooled PostgreSQL connection URL.
3. Preserve `sslmode=require` when required.
4. Remove `schema=public` from the query string if present; the application also strips it defensively.
5. Set the URL as Render `DATABASE_URL`.
6. Let container startup run Alembic migrations and runtime preparation.
7. Verify `/ready` and the main demo report.

Typical URL shape:

```text
postgresql://postgres.<project-ref>:<password>@<pooler-host>:6543/postgres?sslmode=require
```

Do not commit the connection string.

## 8. CORS

Set:

```env
FRONTEND_ORIGIN=https://defi-thesis-risk-copilot.vercel.app
```

The backend also accepts comma-separated origins for controlled preview/local environments:

```env
FRONTEND_ORIGIN=https://defi-thesis-risk-copilot.vercel.app,http://127.0.0.1:3000
```

Do not use a wildcard origin with credentials.

## 9. Free-Tier Behavior

- Render may sleep and cold-start after inactivity.
- Supabase free projects may pause or limit resources.
- Render runtime files are ephemeral.
- The curated JSON RAG index is rebuilt on each public container start.
- Persistent reports and demo records live in PostgreSQL.
- The public environment must not contain real provider credentials.

The JSON RAG index is adequate for the portfolio deployment, but durable pgvector/object storage is planned for the real multi-user product.

## 10. Secret Handling

- secrets remain server-side;
- raw secrets never return to the frontend;
- logs and audit metadata redact sensitive fields;
- database credential storage requires an encryption key;
- public visitors cannot read credential metadata;
- real Vast.ai use remains disabled publicly;
- managed secret storage/KMS remains a production-roadmap item.

Private/local authentication settings:

```env
AUTH_ENABLED=true
ADMIN_EMAIL=admin@example.local
ADMIN_BOOTSTRAP_TOKEN=<strong secret>
AUTH_SECRET_KEY=<strong secret>
CREDENTIAL_ENCRYPTION_KEY=<strong encryption material>
```

## 11. Local Docker

```bash
cp .env.example .env
docker compose up -d --build
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

Local demo seed:

```bash
backend/.venv/bin/python backend/scripts/seed_demo_data.py
```

Production-like configuration validation:

```bash
docker compose config
docker compose -f docker-compose.production.yml config
```

## 12. Deployment Verification

After Render deployment:

```bash
curl https://defi-thesis-risk-copilot.onrender.com/
curl https://defi-thesis-risk-copilot.onrender.com/health
curl https://defi-thesis-risk-copilot.onrender.com/ready
curl https://defi-thesis-risk-copilot.onrender.com/api/deployment/status
curl https://defi-thesis-risk-copilot.onrender.com/api/demo/status
curl https://defi-thesis-risk-copilot.onrender.com/api/reports/demo_report_pendle_pt_loop
```

Public mutation checks should return `403`:

```bash
curl -i -X POST https://defi-thesis-risk-copilot.onrender.com/api/demo/seed
curl -i -X POST https://defi-thesis-risk-copilot.onrender.com/api/monitoring/run \
  -H 'Content-Type: application/json' -d '{}'
curl -i -X POST https://defi-thesis-risk-copilot.onrender.com/api/discovery/run \
  -H 'Content-Type: application/json' -d '{}'
```

## 13. Deployment Checklist

- [ ] Vercel build succeeds.
- [ ] Render build succeeds.
- [ ] Alembic migrations complete.
- [ ] Runtime preparation seeds the demo and builds RAG.
- [ ] `/health` returns healthy.
- [ ] `/ready` returns ready.
- [ ] Deployment status reports DB and demo readiness.
- [ ] The main demo report opens from Vercel.
- [ ] CORS permits only expected frontend origins.
- [ ] Public administrator identity is not granted.
- [ ] Public mutations return `403`.
- [ ] Public compute is bounded and rate-limited.
- [ ] LLM synthesis is disabled by default.
- [ ] Vast.ai is disabled/dry-run.
- [ ] No real secrets are configured in the public environment.
- [ ] Git commit/version metadata is set.

## 14. Supabase Auth Setup

For a private product deployment:

```env
AUTH_ENABLED=true
AUTH_PROVIDER=supabase
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_JWKS_URL=https://<project>.supabase.co/auth/v1/.well-known/jwks.json
SUPABASE_JWT_ISSUER=https://<project>.supabase.co/auth/v1
SUPABASE_JWT_AUDIENCE=authenticated
NEXT_PUBLIC_SUPABASE_URL=https://<project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>
```

Keep `SUPABASE_SERVICE_ROLE_KEY` server-side only and do not expose it through `NEXT_PUBLIC_*`.

Production fails closed when `AUTH_ENABLED=true`, `AUTH_PROVIDER=supabase`, and required Supabase JWT configuration is missing. `AUTH_PROVIDER=legacy_local` is only for explicit local development and is rejected in production.

MFA:

- ordinary users may use MFA when Supabase MFA is configured;
- `ADMIN_MFA_REQUIRED=true` documents and surfaces the administrator requirement;
- full TOTP enrollment/challenge verification must be tested against the deployed Supabase project.

Retention cleanup is manual in Phase 16:

```bash
cd backend
python -m scripts.cleanup_expired_data --dry-run
python -m scripts.cleanup_expired_data
```

## 15. Next Production Steps

See [`docs/development_plan.md`](development_plan.md) for:

- managed identity and tenant ownership
- distributed rate limits
- durable jobs and hybrid workers
- object storage and pgvector
- production monitoring, security, backups, and browser tests
