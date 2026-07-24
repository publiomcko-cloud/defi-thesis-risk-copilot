# Deployment — DeFi Thesis & Risk Copilot

This document defines deployment modes, environment variables, trust boundaries, startup, verification, and phase handoffs.

Related contracts:

- [`archive/v1_phase_16/phase_16_identity_ownership_contract.md`](archive/v1_phase_16/phase_16_identity_ownership_contract.md)
- [`future_phase_contracts.md`](future_phase_contracts.md)
- [`current_state.md`](current_state.md)

---

## 1. Hosted architecture

```text
Browser
  -> Vercel Next.js
     -> same-origin auth routes
     -> same-origin backend BFF
  -> Render FastAPI
  -> Supabase PostgreSQL
```

Live Phase 15 services:

- frontend: `https://defi-thesis-risk-copilot.vercel.app`;
- demo: `https://defi-thesis-risk-copilot.vercel.app/demo`;
- backend: `https://defi-thesis-risk-copilot.onrender.com`;
- health: `/health`;
- readiness: `/ready`;
- deployment status: `/api/deployment/status`;
- OpenAPI: `/docs`.

The live deployment follows `main`. Phase 16 is merge-ready; the final deployed-provider and legal launch checks are now V1 Phase 22 work.

---

## 2. Supported deployment modes

### Mode A — Public portfolio demo

Purpose: anonymous synthetic demonstration with public-safe read and bounded compute.

Backend:

```env
APP_ENV=portfolio_demo
PUBLIC_DEMO_MODE=true
AUTH_ENABLED=false
AUTH_PROVIDER=legacy_local
DATABASE_URL=<Supabase pooled PostgreSQL URL>
FRONTEND_ORIGIN=https://defi-thesis-risk-copilot.vercel.app
LLM_SYNTHESIS_ENABLED=false
LLM_PROVIDER=disabled
RAG_SEMANTIC_ENABLED=false
VAST_ENABLED=false
VAST_DRY_RUN=true
```

Frontend:

```env
BACKEND_API_BASE_URL=https://defi-thesis-risk-copilot.onrender.com
NEXT_PUBLIC_API_BASE_URL=/api/backend
NEXT_PUBLIC_PUBLIC_DEMO_MODE=true
COOKIE_SECURE=true
```

`AUTH_ENABLED=false` must not create an administrator for hosted visitors. Public visitors receive anonymous/common public behavior only.

### Mode B — Private authenticated product

Purpose: authenticated users without anonymous public compute.

```env
APP_ENV=production
PUBLIC_DEMO_MODE=false
AUTH_ENABLED=true
AUTH_PROVIDER=supabase
```

This mode requires the complete Supabase and BFF configuration below.

### Mode C — Hybrid public demo plus authenticated product

Purpose: anonymous demo visitors and authenticated users coexist in one deployment.

```env
APP_ENV=production
PUBLIC_DEMO_MODE=true
AUTH_ENABLED=true
AUTH_PROVIDER=supabase
```

This is the completed Phase 16 implementation target. Commercial enablement and the final deployed validation are V1 Phase 22 requirements:

- actor-based route policies are validated on deployed domains;
- authenticated users can perform authorized personal/organization mutations while anonymous visitors remain restricted in deployed Supabase mode;
- BFF route and cookie allowlists continue to pass local and deployed security tests;
- browser anonymous and authenticated flows pass on deployed domains.

Do not enable Mode C commercially until Phase 22 completes.

---

## 3. Next.js BFF configuration

Browser requests use:

```text
/api/backend/*
```

Next.js uses the server-only variable:

```env
BACKEND_API_BASE_URL=https://defi-thesis-risk-copilot.onrender.com
```

Do not rely on a public browser variable to identify the authenticated backend destination.

The BFF must:

- allow only explicit backend route families;
- reject arbitrary URL/host/path forwarding;
- attach the managed access token server-side;
- forward only the anonymous-session cookie when needed;
- not forward Supabase access/refresh/expiry cookies as a raw `Cookie` header;
- forward safe content type and request ID where appropriate;
- copy only safe response headers;
- propagate anonymous-session `Set-Cookie` safely;
- clear auth cookies after failed token refresh.

Security gate:

```text
ALLOWED_PREFIXES must not contain "/" as a general prefix.
```

A `/` prefix matches every path and invalidates the allowlist.

---

## 4. Supabase database setup

1. Create the Supabase project.
2. obtain the pooled PostgreSQL URL;
3. preserve `sslmode=require` where required;
4. remove unsupported `schema=public` query parameters if present;
5. configure Render `DATABASE_URL`;
6. run Alembic migrations through container startup;
7. verify `/ready`;
8. test upgrade from a Phase 15 database before Phase 16 merge.

Phase 16C adds `20260721_0010`, which validates required saved-thesis and consent ownership before adding foreign keys. It safely detaches only invalid nullable resource links without changing visibility, but it deliberately stops deployment for invalid required links. Take a database backup and resolve such integrity errors before retrying production startup; do not reset production data to bypass the migration.

Typical pooled URL:

```text
postgresql://postgres.<project-ref>:<password>@<pooler-host>:6543/postgres?sslmode=require
```

Never commit the connection string.

---

## 5. Supabase Auth setup

Backend variables:

```env
AUTH_ENABLED=true
AUTH_PROVIDER=supabase
REQUIRE_VERIFIED_EMAIL=true
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_JWKS_URL=https://<project>.supabase.co/auth/v1/.well-known/jwks.json
SUPABASE_JWT_ISSUER=https://<project>.supabase.co/auth/v1
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_SERVICE_ROLE_KEY=<server-only when explicitly required>
ADMIN_MFA_REQUIRED=false
BFF_AUDIT_SECRET=<long-random-server-only-shared-value>
```

Frontend/server variables:

```env
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_ANON_KEY=<public anon key>
NEXT_PUBLIC_SUPABASE_URL=https://<project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<public anon key>
SESSION_COOKIE_NAME=defi_copilot_session
ANONYMOUS_SESSION_COOKIE_NAME=defi_copilot_anon
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
COOKIE_DOMAIN=
BACKEND_API_BASE_URL=https://defi-thesis-risk-copilot.onrender.com
BFF_AUDIT_SECRET=<same-long-random-server-only-shared-value>
```

Rules:

- `SUPABASE_SERVICE_ROLE_KEY` is never `NEXT_PUBLIC_*`;
- the Next.js auth route handlers prefer server-runtime `SUPABASE_URL` and `SUPABASE_ANON_KEY`; the `NEXT_PUBLIC_*` values remain public client configuration and compatibility fallbacks;
- service-role usage is limited to explicit server-side administrative operations;
- `BFF_AUDIT_SECRET` is configured identically for the backend and the Next.js server runtime only, never as `NEXT_PUBLIC_*`; it authorizes fixed MFA audit events after successful provider operations;
- ordinary requests use user access tokens;
- production fails closed when issuer/JWKS configuration or `BFF_AUDIT_SECRET` is missing while authentication is enabled;
- production rejects `legacy_local` authentication.

TOTP MFA uses `/account/security` and same-origin `/api/auth/mfa/*` handlers. Enable TOTP in the Supabase Auth MFA settings, enroll a test administrator, verify that challenge completion rotates the HttpOnly session cookies to an `aal2` token, and only then set `ADMIN_MFA_REQUIRED=true`. Keep at least one tested administrator recovery path before enforcing MFA.

---

## 6. Auth redirect and email configuration

Configure Supabase Site URL and redirect allowlist for:

- production Vercel domain;
- controlled Vercel preview domains when needed;
- local development domain;
- email verification callback;
- password recovery callback;
- MFA enrollment/challenge return paths where applicable.

Redirect targets must be validated by the application. Do not accept arbitrary `next`, `redirect`, or callback hosts.

### Email verification

Verify:

- signup email arrives;
- link returns to the expected application route;
- verified claim is present;
- local application user becomes usable;
- unverified account remains blocked where required.

### Password recovery

The deployed flow must include provider callback/code exchange, temporary recovery session, password update, and invalid/expired-link behavior.

### MFA

When `ADMIN_MFA_REQUIRED=true`:

- admin without `aal2` is denied;
- admin can enroll and complete challenge;
- admin with `aal2` is allowed;
- ordinary users remain governed by normal policy;
- enrollment/recovery behavior is manually tested.
- MFA audit records appear in the administrator audit view after enrollment, verification, and factor removal when `BFF_AUDIT_SECRET` is configured.

---

## 7. Cookie policy

Authentication cookies:

```text
HttpOnly=true
Secure=true in production
SameSite=Lax or stricter when compatible
Path=/
explicit Max-Age
```

Separate cookies are used for:

- access token;
- refresh token;
- access expiration;
- anonymous session.

Do not log cookie headers. Do not include tokens in deployment status, error responses, analytics, or audit metadata.

Local HTTP development may require `COOKIE_SECURE=false`. Production must use secure cookies.

---

## 8. CORS and browser access

Recommended production origin:

```env
FRONTEND_ORIGIN=https://defi-thesis-risk-copilot.vercel.app
```

Controlled multiple origins may be comma-separated.

Do not use wildcard origin with credentials.

Browser product requests should use the same-origin BFF, reducing direct credentialed cross-origin calls. Direct backend CORS remains restricted for API/docs/controlled integrations.

---

## 9. Render startup

Container startup:

```bash
alembic upgrade head \
  && python -m scripts.prepare_runtime \
  && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`prepare_runtime`:

- seeds deterministic public demo data when configured;
- builds the current local RAG index;
- remains idempotent.

The public seed endpoint stays blocked in hosted public mode.

Phase 17 will move heavy work out of this web startup/runtime path. Phase 18 will remove local runtime RAG authority.

---

## 10. Health and readiness

- `/health` — process liveness only;
- `/ready` — database and required runtime readiness;
- `/api/deployment/status` — safe operational metadata.

Responses must not include:

- database URLs;
- passwords;
- access/refresh tokens;
- service-role keys;
- provider credentials;
- encryption keys;
- raw cookies.

Render health check uses `/ready`.

---

## 11. Secret handling

- use platform secret configuration or a production secret manager;
- never commit `.env` or real keys;
- database credential storage requires encryption configuration;
- provider secrets never return to the browser;
- logs and audit metadata redact sensitive values;
- public demo has no real provider credentials;
- Vast live credentials remain disabled publicly;
- Phase 19 adds formal inventory, rotation, emergency rotation, and KMS/secret-manager procedures.

---

## 12. Quota and retention configuration

Example Phase 16 variables:

```env
ANONYMOUS_RETENTION_HOURS=24
DELETED_ACCOUNT_RETENTION_DAYS=30
DEFAULT_USER_PLAN=free
QUOTA_ANONYMOUS_ANALYSES_PER_DAY=5
QUOTA_FREE_ANALYSES_PER_DAY=25
QUOTA_FREE_SIMULATIONS_PER_DAY=100
QUOTA_FREE_OPTIONS_PER_DAY=100
QUOTA_FREE_MARKET_DATA_PER_DAY=100
QUOTA_FREE_SAVED_THESES=50
QUOTA_FREE_WATCHLISTS=25
QUOTA_ADMIN_EXEMPT=true
```

Retention cleanup remains manual in Phase 16:

```bash
cd backend
python -m scripts.cleanup_expired_data --dry-run
python -m scripts.cleanup_expired_data
```

Phase 17/20 may schedule cleanup through durable jobs. A scheduler must not be added as an unreliable browser or web-process timer.

### Phase 17A–17B job control-plane configuration

The job foundation is disabled by default and does not start a worker or change existing analysis
requests. With `JOBS_ENABLED=true`, authenticated users may submit bounded jobs, but they remain
queued until Phase 17C supplies a worker protocol. Keep it disabled in public deployment unless
that queued-only behavior is explicitly being tested:

```env
JOBS_ENABLED=false
WORKER_API_ENABLED=false
ASYNC_ANALYSIS_ENABLED=false
VAST_JOB_ENABLED=false
JOB_GLOBAL_PENDING_LIMIT=100
JOB_GLOBAL_RUNNING_LIMIT=4
JOB_USER_PENDING_LIMIT=10
JOB_USER_RUNNING_LIMIT=2
JOB_ORG_PENDING_LIMIT=50
JOB_ORG_RUNNING_LIMIT=8
JOB_PROVIDER_PENDING_LIMIT=25
JOB_PROVIDER_RUNNING_LIMIT=4
WORKER_TOKEN_PEPPER=<server-only secret when WORKER_API_ENABLED=true in production>
```

`WORKER_TOKEN_PEPPER` hashes worker-only credentials and must never be a browser/session token,
job payload field, log value, or public environment variable. Production configuration fails
closed if worker APIs are enabled without it. Administrative worker registration and credential
issuance reuse the existing platform-admin/MFA boundary when MFA is configured; the internal
worker protocol itself is not available until Phase 17C. `ASYNC_ANALYSIS_ENABLED` remains false:
existing `/api/analyze` stays synchronous through Phase 17B.

### Phase 17D–17E trusted worker and guarded Vast job

Phase 17D provides an optional trusted co-located analysis worker. Keep it off in the public demo.
For an authenticated local test only, register a worker and issue its scoped credential through
the admin API, then configure the backend and start the profile:

```env
JOBS_ENABLED=true
WORKER_API_ENABLED=true
WORKER_TOKEN_PEPPER=<server-only random value>
WORKER_CREDENTIAL=<issued wrk_ credential, worker container only>
ASYNC_ANALYSIS_ENABLED=true
VAST_ENABLED=false
VAST_DRY_RUN=true
VAST_JOB_ENABLED=false
```

```bash
docker compose --profile worker up -d worker
```

The worker has no published port and calls only `http://backend:8000/internal/workers/v1/*` using
its own credential. It can claim only allowlisted job types. The Compose profile shares the local
PostgreSQL database and public-curated knowledge base so it can run the deterministic analysis
workflow, but it sends only a bounded completion result to the control plane; the control plane
persists the report. Do not use this Compose profile as a remote-worker blueprint: hosted workers
need a separately designed least-privilege data-access path. It never connects wallets, signs, or
trades. Stop it with `docker compose --profile worker stop worker`; SIGTERM stops new claims and
releases its active lease for retry.

To test the Phase 17E provider path privately, first register a worker whose credential is scoped
to `vast.session.start`, configure its `WORKER_CREDENTIAL`, and retain dry-run mode:

```env
JOBS_ENABLED=true
WORKER_API_ENABLED=true
VAST_ENABLED=true
VAST_DRY_RUN=true
VAST_JOB_ENABLED=true
VAST_MODEL=<server-owned model identifier>
VAST_IMAGE=<server-owned image identifier>
VAST_MAX_HOURLY_COST_USD=0.50
VAST_MAX_SESSION_MINUTES=30
VAST_MAX_ACTIVE_INSTANCES=1
JOB_DAILY_COST_BUDGET_MICROUSD=500000
```

Only a platform administrator satisfying configured MFA may submit
`POST /api/admin/vast/jobs/start`. The job body has only `allow_remote_gpu` and `warm_instance`;
the model, image, offer, GPU, host verification, cost, runtime, startup timeout, and cleanup
limits are environment-owned. The generic `/api/jobs` route and public-demo paths reject this job
type. Use `GET /api/admin/jobs/operations` and the existing sessions endpoint to inspect aggregate
queue/worker/cleanup state without exposing credentials.

For a real rental, keep all three feature flags explicit, set `VAST_DRY_RUN=false`, require admin
MFA, set a nonzero daily micro-USD budget, inject `VAST_API_KEY` or a configured encrypted provider
credential only into the trusted worker runtime, and perform a dry-run rehearsal first. Do not put
provider credentials in job requests, logs, or browser variables. This repository has not verified
a real hosted worker or rental.

Hosted worker recovery runbook: issue a new scoped credential, deploy it as a worker-only secret,
restart the outbound-only worker, verify its `last_seen_at` and operations summary, then revoke the
old credential after the overlap window. To roll back, set `VAST_JOB_ENABLED=false` (and
`VAST_ENABLED=false` for an immediate hard stop), stop the worker, run the administrator cleanup
endpoint for any active sessions, and inspect `cleanup_failed` sessions before re-enabling. A
replayed provider job reconciles its persisted session link; never create a replacement job merely
because a worker response was lost.

---

## 13. Local Docker

```bash
cp .env.example .env
docker compose up -d --build
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

For local Next.js BFF:

```env
BACKEND_API_BASE_URL=http://backend:8000
NEXT_PUBLIC_API_BASE_URL=/api/backend
COOKIE_SECURE=false
```

When running frontend outside Docker, use the reachable local backend URL.

---

## 14. Phase 16 merge validation

### Backend

```bash
cd backend
source .venv/bin/activate
python -m compileall app scripts
alembic upgrade head
alembic downgrade -1
alembic upgrade head
python -m pytest -q
python scripts/run_smoke_checks.py
python -m scripts.cleanup_expired_data --dry-run
```

### Frontend

```bash
cd frontend
npm ci
npm run lint
npm run build
npm run test:e2e
```

### Compose

```bash
docker compose config
docker compose -f docker-compose.production.yml config
docker compose down -v
docker compose up -d --build
```

### V1 Phase 22 manual release verification

Test on Vercel/Render preview deployments:

- public seeded report;
- anonymous analysis and same-browser report retrieval;
- second browser isolation;
- login;
- access-token refresh;
- logout;
- private thesis/report/watchlist isolation;
- organization access/removal/deletion;
- recovery email/callback/reset;
- consent records;
- admin MFA denial/allow;
- public mutation denial;
- no secrets in browser/network/status/logs.

---

## 15. Public endpoint policy

Public read-only and bounded compute are retained from Phase 15.

Privileged operations always require explicit role/ownership checks, including when `PUBLIC_DEMO_MODE=false`.

In hybrid mode, anonymous denial must not globally block authenticated user operations. Route policy is determined by actor and capability.

---

## 16. Deployment checklist

- [ ] branch based on current `main`;
- [ ] migrations preserve existing Phase 15 data;
- [ ] frontend build succeeds;
- [ ] backend tests succeed;
- [x] local production-like browser E2E succeeds with mocked identity/backend providers; deployed-domain verification remains required;
- [ ] Compose validates;
- [x] BFF allowlist is effective in local contract checks;
- [x] refresh cookies are not forwarded to Render in local contract checks;
- [ ] secure cookie settings verified;
- [ ] public and authenticated users coexist as designed;
- [ ] private/organization isolation verified;
- [ ] quota concurrency verified on PostgreSQL;
- [ ] recovery and MFA verified with Supabase;
- [ ] `/health` and `/ready` succeed;
- [ ] public mutation probes are denied;
- [ ] no secrets appear in status/logs/network responses;
- [ ] LLM/Vast defaults remain safe;
- [ ] documentation matches deployment;
- [ ] V1 Phase 22 final provider/legal release validation is complete before commercial launch.

### Archived Phase 16G Record

The current live domains remain the Phase 15 public-demo deployment. On 2026-07-21, Vercel returned `404` for `/login` and `/api/auth/session`, and Render reported `portfolio_demo` with `auth_enabled=false`; public privileged-mutation probes returned controlled `403` responses. This confirms the baseline remains safe but cannot satisfy managed-identity verification. The exact preview configuration and manual verification matrix are archived in [`archive/v1_phase_16/phase_16_deployed_verification.md`](archive/v1_phase_16/phase_16_deployed_verification.md); final provider validation is V1 Phase 22 work.

---

## 17. Later deployment handoffs

### Phase 17

Deploy worker identities, queue schema, local/cloud workers, job observability, and cost controls.

### Phase 18

Deploy object storage and tenant-aware vector storage. Stop treating runtime filesystem as authoritative.

### Phase 19

Deploy shared rate limiting, WAF, security headers, centralized observability, backups, restore drills, scanning, and incident operations.

### Phase 20

Deploy analytics/notification processors, durable schedules, billing webhook handling, status/support systems, and legal/commercial controls.

### Phase 21

Deploy evaluated model registry/routing and safe worker-based model execution with rollback and cost/privacy controls.

### Phase 22

Validate custom SMTP, deployed identity/recovery/MFA/browser flows, final isolation checks, and qualified legal/privacy approval before commercial launch.
