# Deployment — DeFi Thesis & Risk Copilot

This document defines deployment modes, environment variables, trust boundaries, startup, verification, and phase handoffs.

Related contracts:

- [`archive/v1_phase_16/phase_16_identity_ownership_contract.md`](archive/v1_phase_16/phase_16_identity_ownership_contract.md)
- [`archive/v1_phase_17/`](archive/v1_phase_17/)
- [`archive/v1_phase_18/`](archive/v1_phase_18/)
- [`phase_19_execution_plan.md`](phase_19_execution_plan.md)
- [`phase_20_execution_plan.md`](phase_20_execution_plan.md)
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

Live services:

- frontend: `https://defi-thesis-risk-copilot.vercel.app`;
- demo: `https://defi-thesis-risk-copilot.vercel.app/demo`;
- backend: `https://defi-thesis-risk-copilot.onrender.com`;
- health: `/health`;
- readiness: `/ready`;
- deployment status: `/api/deployment/status`;
- OpenAPI: `/docs`.

The live deployment follows `main`; Phases 16–18 are complete there and the
Phase 19 repository foundation is merged. Phase 18 durable knowledge
capabilities remain feature-gated while JSON RAG remains the production
fallback. Phase 19 centralized telemetry, alert delivery, provider restore,
secret rotation, protected-branch, and controlled rollout evidence remains
external. Phase 20 is planning-only and adds no deployment variables or
providers. Final deployed-provider, storage-policy, and legal launch checks
remain V1 Phase 22 work.

## Phase 19A local-only observability

Phase 19A introduces safe structured logs and correlation propagation, not an
external telemetry integration. Keep these defaults unless an approved later
Phase 19 rollout supplies retention, access, exporter, and alerting evidence:

```env
OBSERVABILITY_ENABLED=false
OBSERVABILITY_RELEASE_ID=
OBSERVABILITY_SAMPLING_RATE=1.0
OBSERVABILITY_EXPORT_TIMEOUT_SECONDS=2
OBSERVABILITY_EXPORT_QUEUE_SIZE=100
OBSERVABILITY_CLOCK_TIMEZONE=UTC
```

`backend/scripts/check_operational_readiness.py` reads database/JSON-fallback
state and feature-safe booleans without contacting a telemetry provider or
printing secrets. `GET /api/admin/operations/readiness` exposes the same
metadata only to platform administrators. It does not prove deployed alerting,
storage policy, worker availability, or a Phase 18 cutover.

## Phase 19B shared rate-limiter rollout

Phase 19B uses the existing PostgreSQL/Supabase database, so it does not add a
Redis service or browser credential. It is disabled by default and must not be
enabled until the deployment operator knows the exact proxy CIDRs that are
permitted to supply `X-Forwarded-For`.

```env
RATE_LIMITING_ENABLED=false
RATE_LIMITING_MODE=shadow
RATE_LIMIT_KEY_PEPPER=<server-only-long-random-value>
RATE_LIMIT_TRUSTED_PROXY_CIDRS=<comma-separated-proxy-cidrs>
```

The rollout order is: apply migration `20260728_0022`; set the pepper and proxy
CIDRs in a preview environment; enable `RATE_LIMITING_ENABLED=true` with
`RATE_LIMITING_MODE=shadow`; inspect only the aggregate administrator endpoint
`/api/admin/operations/rate-limits`; define the alert owner; then explicitly
switch to `enforce` for bounded compute. Job submission is cost-bearing and
fails closed if the enabled shared-limiter database path is unavailable.

Do not place the pepper in Vercel browser variables, committed `.env` files,
client logs, or the frontend. To roll back, set `RATE_LIMITING_ENABLED=false`.
The legacy public-demo in-process limiter remains active in that disabled mode.

## Phase 19C edge and upload-security rollout

Keep the 19C controls in their safe defaults until the production operator has
recorded final Vercel/Render origins, a CSP report review, and the HTTPS scope:

```env
FRONTEND_ORIGIN=https://defi-thesis-risk-copilot.vercel.app
BFF_ALLOWED_ORIGINS=https://defi-thesis-risk-copilot.vercel.app
API_MAX_REQUEST_BYTES=1048576
BFF_MAX_REQUEST_BYTES=1048576
BFF_KNOWLEDGE_UPLOAD_MAX_BYTES=10616832
SECURITY_CSP_MODE=report_only
SECURITY_CSP_REPORT_URI=
SECURITY_HSTS_ENABLED=false
KNOWLEDGE_STORAGE_ENABLED=false
KNOWLEDGE_UPLOAD_SCANNING_REQUIRED=false
```

`FRONTEND_ORIGIN` is the exact backend CORS allowlist. `BFF_ALLOWED_ORIGINS`
is the exact same-origin browser allowlist for BFF mutations and must not be a
wildcard. `BFF_MAX_REQUEST_BYTES` and `BFF_KNOWLEDGE_UPLOAD_MAX_BYTES` must
match the backend route budgets. Both BFF and API count actual received bytes,
so a missing or misleading `Content-Length` cannot enlarge the request. The BFF
does not accept a path, credentials, redirect, or request-selected upstream
target. Keep CSP report-only while reviewing browser
compatibility. Set `SECURITY_HSTS_ENABLED=true` only after every included
subdomain is HTTPS-safe; rollback a bad policy by setting it back to `false`.

Private knowledge storage remains disabled. Before a production private-source
activation, configure a trusted internal scanner and require it:

```env
KNOWLEDGE_STORAGE_ENABLED=true
KNOWLEDGE_UPLOAD_SCANNING_REQUIRED=true
KNOWLEDGE_UPLOAD_SCANNER_URL=https://scanner.internal.example/scan
KNOWLEDGE_UPLOAD_SCANNER_TIMEOUT_SECONDS=10
```

The scanner endpoint is server-only, must be HTTPS (or an approved internal
transport), must return a bounded JSON `{\"status\": \"clean\"}`, and any
failure rejects the upload before object storage. Do not activate storage until
scanner, quarantine, WAF/bot, and synthetic two-tenant policy evidence are
recorded. There is no scanner credential in browser configuration.

## Phase 19D monitoring and synthetic rollout

Local monitoring is disabled by default and never sends an alert:

```env
OPERATIONS_MONITORING_ENABLED=false
OPERATIONS_ALERT_EVALUATION_ENABLED=false
OPERATIONS_SYNTHETIC_CHECKS_ENABLED=false
OPERATIONS_SYNTHETIC_ALLOWED_ORIGINS=
```

In a private preview, enable local aggregate inspection first. The
administrator-only `/api/admin/operations/monitoring` endpoint and
`/admin/operations` page expose only counts, ages, booleans, retrieval metrics,
and stable candidate keys. They must continue to return
`alert_delivery=not_implemented` until a later approved delivery adapter exists.

Use [`operations/monitoring_and_alerting.md`](operations/monitoring_and_alerting.md)
for SLO targets, synthetic command rules, owners, escalation, and rollout gates.
Do not configure a browser-visible telemetry key, pager token, or synthetic
credential. Do not run authenticated synthetics until a dedicated least-privilege
synthetic user and revocation procedure are documented.

## Phase 19E recovery verification and retention guard

The local restore verifier is disabled by default and must only run against an
isolated target. It is not a provider backup implementation:

```env
BACKUP_RESTORE_DRILL_ENABLED=false
BACKUP_RETENTION_GUARD_ENABLED=false
BACKUP_RESTORE_EVIDENCE_REFERENCE=
```

Follow [`operations/backup_restore_runbook.md`](operations/backup_restore_runbook.md)
and [`operations/secret_inventory.md`](operations/secret_inventory.md) before
changing these values. Do not set the evidence reference until a provider
backup/object restore drill is recorded in the approved operational system.
The verifier refuses `APP_ENV=production`, and `BACKUP_RETENTION_GUARD_ENABLED`
blocks non-dry cleanup when no reference is configured. Neither control creates
provider backups, exposes a secret, or substitutes Alembic for data recovery.

## Phase 19F CI/CD security rollout

The repository controls are active in GitHub Actions without deployment secrets.
`Supply Chain Security` uses a read-only token and does not run under
`pull_request_target`; `CodeQL` only uploads security results with its scoped
`security-events: write` permission. Both use full-SHA action pins. Do not add
Render, Vercel, Supabase, worker, or provider credentials to these workflows.

Before treating the scans as release enforcement, follow
[`operations/supply_chain_security.md`](operations/supply_chain_security.md) to
review the first hosted baseline and configure required checks on `main`. The
workflow constructs local container images only for scanning and does not
publish them. To roll back a scanner, use the documented reviewed exception
process; do not disable functional CI, secret scanning, or workflow policy.

## Phase 19G incident-response rollout

The repository contains no pager, incident ticket, contact roster, or evidence
store. Before relying on the local monitoring candidates for operational
response, the deployment operator must assign named primary/backup owners,
incident commander coverage, and communication authority in the approved
private operations system. Record the approved evidence location, legal/privacy
escalation route, and status-page process there as well.

Use [`operations/incidents/README.md`](operations/incidents/README.md) to map
the existing `operations.*` alert IDs to versioned procedures, and run the ten
synthetic [tabletop scripts](operations/incidents/tabletop_exercises.md) before
enabling an external alert receiver. Keep alert delivery disabled until a
non-production receiver test and its evidence reference are approved. Do not
place pager tokens, contact details, incident content, evidence URLs with
credentials, raw logs, or customer data in environment files, browser values,
CI output, or the repository.

For rollback, revert the runbook change only through normal review. Reverse a
runtime containment action only after the incident commander records the
recovery verification described by that procedure. These runbooks do not enable
Phase 18 storage flags, real Vast.ai rentals, or destructive recovery actions.

## Phase 19H isolated failure-exercise rollout

[`operations/failure_exercises.md`](operations/failure_exercises.md) defines a
fixed catalog for local/CI failure exercises. It is disabled by default and is
not a production chaos-test control. Enable it only with an isolated
PostgreSQL/pgvector database, the explicit `OPERATIONS_EXERCISES_ISOLATED=true`
acknowledgement, `APP_ENV=exercise`, and bounded timeout. The runner refuses
production and any non-dry-run/real-rental Vast configuration.

The scheduled `Phase 19 Failure Exercises` workflow uses an ephemeral GitHub
Actions pgvector service and no deployment, storage, provider, pager, or
customer credentials. It may be manually dispatched only for the same isolated
conditions. Stop the driver when a control fails, run durable-job recovery in
dry-run mode, and follow the mapped Phase 19G procedure. Production load or
chaos testing requires explicit separate approval and remains outside this
repository's implemented scope.

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
VAST_REAL_RENTALS_ENABLED=false
VAST_RECONCILIATION_PROFILE=unverified
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

For the production hybrid shell, set `NEXT_PUBLIC_PUBLIC_DEMO_MODE=false` on Vercel. This
frontend flag controls whether the navigation is rendered as a read-only portfolio shell; it does
not disable the backend's anonymous demo capability. With the flag set to `false`, anonymous
visitors see Demo, Login, and Signup, authenticated users see their private workspace, and the
Admin link is available for platform-administrator testing. Backend actor and role checks remain
the security boundary for every privileged endpoint.

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

Phase 17 moves authenticated analysis and guarded provider work out of the web request when its
feature flags and trusted worker are enabled. Phase 18 will remove local runtime RAG authority.

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

### Phase 17 job control-plane configuration

Jobs are disabled by default and do not change public-demo requests. With the worker and async
flags enabled, authenticated analysis runs through the durable control plane; anonymous public-demo
analysis remains synchronous. Keep the feature disabled in public deployment unless the worker,
credential, and rollback procedure are explicitly configured:

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
issuance reuse the existing platform-admin/MFA boundary when MFA is configured. The browser BFF
never proxies `/internal/workers/*`. `ASYNC_ANALYSIS_ENABLED=false` is the rollback switch for
authenticated analysis; existing reports and jobs remain durable for review.

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

### Low-cost production worker: scheduled GitHub Actions

For this public repository's low-volume production deployment, Phase 17 can run as the
outbound-only `.github/workflows/phase17-scheduled-worker.yml` workflow instead of a continuously
billed Render Background Worker. It runs every five minutes, claims at most one
`analysis.generate` job with `--once`, and has no inbound network endpoint. This intentionally
trades immediate execution for bounded cost and a maximum normal queue delay of about five
minutes.

Create a protected GitHub environment named `production-worker` and set these environment secrets:

```text
WORKER_CONTROL_PLANE_URL=https://<production-backend>
WORKER_CREDENTIAL=<one scoped analysis.generate worker credential>
WORKER_DATABASE_URL=<one worker-only least-privilege PostgreSQL connection URL>
```

`WORKER_DATABASE_URL` is required by the current deterministic executor, but it must **not** be
the normal application `DATABASE_URL`. Create a dedicated login role with only `CONNECT` and
`USAGE` on `public`, `SELECT` on `users`, `organizations`, and `organization_memberships`, and
`SELECT`, `INSERT`, `UPDATE`, and `DELETE` on `market_data_cache`. Do not grant it access to jobs,
reports, credentials, sessions, audit logs, or any future tables. Keep it only in the protected
`production-worker` GitHub environment, rotate it with the worker credential, and remove the
secret before disabling the scheduled worker. This narrowly scoped, outbound-only execution
profile is the documented exception to the normal remote-worker no-database-access baseline.

The workflow has no pull-request trigger, uses read-only repository permissions, serializes runs,
checks out `main`, and must never print environment variables or credentials. Keep the credential
scoped only to `analysis.generate`; rotate it through the platform-admin worker API and GitHub
environment secret together. Use Actions manual dispatch for an immediate bounded run. Scheduled
workflows can be delayed by GitHub, so this path is suitable for low volume rather than
latency-sensitive workloads. Do not store provider credentials in the GitHub environment.

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

Real rentals are deliberately unavailable in this release. `VAST_DRY_RUN=false` is rejected for a
normal provider until a future adapter declares verified request idempotency, request
reconciliation, and idempotent destroy support. Keep `VAST_REAL_RENTALS_ENABLED=false` and
`VAST_RECONCILIATION_PROFILE=unverified`; no provider credential belongs in job requests, logs, or
browser variables.

Hosted worker recovery runbook: issue a new scoped credential, deploy it as a worker-only secret,
restart the outbound-only worker, verify its `last_seen_at` and operations summary, then revoke the
old credential after the overlap window. To roll back, set `VAST_JOB_ENABLED=false` (and
`VAST_ENABLED=false` for an immediate hard stop), stop the worker, run the administrator cleanup
endpoint for any active sessions, and inspect `cleanup_failed` sessions before re-enabling. A
replayed provider job reconciles its persisted session link; never create a replacement job merely
because a worker response was lost.

Run durable recovery from an operations scheduler, never a browser or the web-request process:

```bash
cd backend
python -m scripts.recover_durable_jobs --dry-run
python -m scripts.recover_durable_jobs
```

The command revalidates authorization, expires abandoned leases and queues, marks stale workers,
finalizes safe cancellations, and reconciles durable capacity and provider-cost ledger counters.
`--dry-run` makes no provider health, reconciliation, rent, or destroy call and persists no
database change. Schedule it from a later
operations runtime. `POST /api/admin/vast/sessions/start` is local dry-run diagnostics only and is
rejected when durable Vast jobs are enabled or dry-run mode is off; all real startup must use the
durable job route. Do not enable real rentals until the provider's request-ID reconciliation is
verified in the deployment environment.

Organization membership changes are safe to apply without deleting completed shared work: they
revoke active jobs only. Queued/retry work is failed and releases its reservation; leased/running
work waits for normal worker cancellation acknowledgement. Account deletion, organization deletion,
and retention cleanup remain the only destructive job-result lifecycle paths.

### Phase 17F user workspace and retention

Authenticated users can review their own authorized jobs at `/jobs`. It exposes state, progress,
attempts, safe events/errors, cancellation, and report references. Administrators retain the
separate worker and aggregate operations views. Account export includes safe job, event, and
artifact metadata; it deliberately excludes job inputs, raw event metadata, provider responses,
credentials, and worker tokens.

Run retention manually until a later scheduler is approved:

```bash
cd backend
python -m scripts.cleanup_expired_data --dry-run
python -m scripts.cleanup_expired_data
```

The cleanup removes expired job events, terminal jobs with their attempts/artifacts, expired worker
credentials, and artifacts whose retention deadline elapsed. It never makes an incomplete local
output appear as a durable artifact. Before account deletion, users can export this safe projection;
deletion cancels running work through lease recovery and disposes of terminal results/artifacts.

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

## 14. Completed Phase 17 baseline validation

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

### Archived Phase 16G record

On 2026-07-21, the then-current Phase 15 deployment returned `404` for
`/login` and `/api/auth/session`; that historical evidence is preserved in
[`archive/v1_phase_16/phase_16_deployed_verification.md`](archive/v1_phase_16/phase_16_deployed_verification.md).
It does not describe the current hybrid deployment. Final provider validation
remains V1 Phase 22 work.

---

## 17. Later deployment handoffs

### Phase 17

Completed on `main`. Preserve worker identities, queue schema, the trusted
GitHub Actions worker path, job observability, and provider cost controls.

### Phase 18

The 18A–18G schema, adapter, authenticated upload API, ingestion worker,
local-only pgvector embedding path, shadow retrieval diagnostic, and lifecycle
rollback/cleanup controls are present but disabled by default.
Configuration defaults:

```env
KNOWLEDGE_STORAGE_ENABLED=false
SUPABASE_STORAGE_BUCKET=private-knowledge
SUPABASE_STORAGE_TIMEOUT_SECONDS=20
KNOWLEDGE_UPLOAD_MAX_BYTES=10485760
KNOWLEDGE_UPLOAD_CHUNK_BYTES=65536
DOCUMENT_INGEST_ENABLED=false
KNOWLEDGE_INGEST_MAX_BYTES=10485760
KNOWLEDGE_INGEST_MAX_TEXT_BYTES=2097152
KNOWLEDGE_INGEST_MAX_PDF_PAGES=100
KNOWLEDGE_CHUNK_MAX_CHARACTERS=2000
KNOWLEDGE_EMBEDDINGS_ENABLED=false
KNOWLEDGE_EMBEDDING_PROFILE_ID=kembprof_local_hash_384_v1
KNOWLEDGE_EMBEDDING_PROVIDER=local_deterministic
KNOWLEDGE_EMBEDDING_MODEL=local-hash-384-v1
KNOWLEDGE_EMBEDDING_DIMENSIONS=384
KNOWLEDGE_SHADOW_RETRIEVAL_ENABLED=false
KNOWLEDGE_SHADOW_RETRIEVAL_TOP_K=4
KNOWLEDGE_PUBLIC_CORPUS_IMPORT_ENABLED=false
KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=false
SUPABASE_SERVICE_ROLE_KEY=
```

`SUPABASE_SERVICE_ROLE_KEY` is backend/worker-only and must never use a
`NEXT_PUBLIC_` name. Enabling storage in production without `SUPABASE_URL` and
the service-role credential fails configuration validation. Bucket creation,
private policies, and a synthetic-tenant object probe are external deployment
prerequisites; Alembic never changes Supabase's managed `storage` schema.

The API accepts uploads only when `KNOWLEDGE_STORAGE_ENABLED=true` and the
private bucket/policy has been independently configured. It returns metadata
only, never a public object URL. Do not enable the flag in production until a
synthetic-tenant private-bucket probe and access-policy review are recorded.
`DOCUMENT_INGEST_ENABLED=true` additionally requires `JOBS_ENABLED=true`,
`WORKER_API_ENABLED=true`, and a scoped trusted worker credential. Do not enable
it until the private bucket policy/probe is validated. Keep durable retrieval
disabled. Runtime JSON remains the production retrieval fallback until shadow
evaluation and rollback gates pass.
`KNOWLEDGE_EMBEDDINGS_ENABLED=true` requires `JOBS_ENABLED=true` and
`WORKER_API_ENABLED=true`; it accepts only the local deterministic 384-dimension
profile and therefore does not need an external provider key. PostgreSQL must
provide the `vector` extension; local/CI Compose uses `pgvector/pgvector:pg16`.
Provision `vector` through a database administrator or Supabase before running
application migrations, then verify it with:

```bash
cd backend
source .venv/bin/activate
python -m scripts.preflight_pgvector
alembic upgrade head
```

The Alembic application role intentionally does not attempt `CREATE EXTENSION`.
Do not enable it before the private-storage/worker deployment gate and pgvector
readiness probe are recorded.
Migration `20260728_0021` can downgrade only before multiple completed
generations exist for the same version/profile; it fails closed rather than
discarding historical embedding rows. After activation, the supported production
rollback is to disable `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED` and retain durable
data while reports return to JSON.
`KNOWLEDGE_SHADOW_RETRIEVAL_ENABLED=true` requires embeddings to be enabled and
exposes only the authenticated diagnostic endpoint. It must not be enabled for
ordinary traffic until a synthetic tenant-isolation probe, pgvector readiness
probe, and retrieval-event review are recorded. It never replaces JSON report
retrieval in this slice.

Phase 18G adds a private, operator-only curated Markdown migration command:

```bash
cd backend
source .venv/bin/activate
python -m scripts.import_public_corpus
KNOWLEDGE_PUBLIC_CORPUS_IMPORT_ENABLED=true python -m scripts.import_public_corpus --apply
python -m scripts.evaluate_public_corpus
```

The import command accepts only checked-in `knowledge_base/**/*.md`, creates
approved public immutable lineage, verifies Supabase objects by bounded
authenticated read when checksum metadata is unavailable, and is not an API or
browser upload path. A failed corpus transaction compensates all objects it
created; `--apply` owns the final database commit and compensates every object
created by that attempt if flush or commit fails. Objects observed as existing
or verified after a concurrent create conflict are never deleted. Unsafe
deterministic-ID collisions fail closed rather than changing tenant/discovered
content.
Apply it only after the private bucket and worker/pgvector deployment checks
are recorded. `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=true` additionally requires
shadow retrieval and should be enabled only after the comparison command passes.
For authenticated analysis it queries approved public, caller-owned private,
and active-organization durable material through server-derived scope; anonymous
analysis remains public-only. It automatically reverts an empty or unavailable
durable lookup to the existing JSON index. Turn the flag back to `false` for an
immediate report-path rollback; no data migration is required.

Phase 18H adds the authenticated `/knowledge` workspace for source ownership,
upload, immutable document versions, ingestion/embedding submission, version
restore, deletion, and safe status inspection. Report sources display exact
durable lineage only where guarded durable retrieval supplied it. The admin view
shows aggregate readiness only; it never returns a private object key, bucket
name, source content, or credential.

Before any live storage activation, perform this recorded deployment runbook:

1. Create `private-knowledge` as a **private** Supabase Storage bucket. Do not
   enable public access and do not create a browser-facing service-role path.
2. Restrict Storage object policies to the application service role and the
   server-derived object-key scheme. A browser must not be able to list, read,
   create, or guess a knowledge object URL.
3. Deploy with all Phase 18 feature flags still `false`, then run:

   ```bash
   cd backend
   source .venv/bin/activate
   python -m scripts.check_knowledge_readiness
   ```

4. In a controlled synthetic environment, enable storage only and run:

   ```bash
   python -m scripts.check_knowledge_readiness --probe-storage
   ```

   The probe creates, bounded-reads, checks the public-object route, and deletes
   one synthetic object. It prints no key or credential. A result other than
   `"storage_probe": "passed"` blocks the rollout.
5. Test a private owner, an active organization member, and a non-member using
   `/knowledge`; confirm owner/member visibility and non-member `404`. Test a
   deleted version is excluded before physical cleanup.
6. Enable the trusted ingestion worker, then embeddings and shadow retrieval;
   record the worker claim/heartbeat/completion and tenant-isolation evidence.
7. Run `python -m scripts.import_public_corpus --apply` with the explicit import
   flag, then `python -m scripts.evaluate_public_corpus` (the local quality gate
   currently evaluates seven cases, including one expected-empty query, at
   top-1). Enable
   `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=true` only after its quality gate passes.
8. Keep JSON rollback active for the documented window. To roll back, set the
   primary flag to `false` first; do not delete durable rows or private objects.

These live Supabase policy, two-user, worker, and primary-cutover steps are
external Phase 22 evidence until they are executed against the deployed
environment. They are intentionally not claimed by local CI.

## Phase 19I Controlled Durable-RAG Validation

Phase 19I adds a read-only guard for the documented controlled rollout. It
does not create a tenant, upload a document, change a feature flag, or expose
storage information. Use the complete operator sequence in
[`operations/controlled_rag_rollout.md`](operations/controlled_rag_rollout.md).

For a shadow-only production check, enable the explicit validation flag while
leaving `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=false`, then run:

```bash
cd backend
python -m scripts.check_controlled_rag_rollout --mode shadow
```

The checker requires database and pgvector readiness, JSON fallback, storage,
ingestion/worker/embedding/shadow prerequisites, and a dry-run-only Vast
configuration. A primary-path check is available only in a separately isolated
non-production environment with `CONTROLLED_RAG_VALIDATION_ISOLATED=true`.
The application rejects the primary flag in production, so it cannot be
accidentally enabled through a deployment variable.

Phase 18F adds a controlled retention command:

```bash
cd backend
source .venv/bin/activate
python -m scripts.cleanup_knowledge_tombstones --dry-run
```

Run the dry run before any real cleanup. A real run requires the private storage
configuration and deletes only versions already tombstoned in a committed
database transaction. Provider failures leave a retryable cleanup task; they
never restore retrieval visibility or expose an object key.

### Phase 19

The repository foundation for shared rate limiting, security headers,
observability hooks, recovery verification, scanning, incident operations, and
bounded exercises is merged. Centralized telemetry, alert delivery, provider
restore, production secret rotation, protected-branch enforcement, and
controlled deployment evidence remain external gates.

### Phase 20

Follow [`phase_20_execution_plan.md`](phase_20_execution_plan.md) only after
the relevant provider ADR and privacy/security gate is approved. Deploy
analytics and notification processors, durable schedules, entitlement and
billing sandbox handling, status/support systems, and legal/commercial controls
incrementally. The plan itself selects no provider and changes no production
flag.

### Phase 21

Deploy evaluated model registry/routing and safe worker-based model execution with rollback and cost/privacy controls.

### Phase 22

Validate custom SMTP, deployed identity/recovery/MFA/browser flows, final isolation checks, and qualified legal/privacy approval before commercial launch.
