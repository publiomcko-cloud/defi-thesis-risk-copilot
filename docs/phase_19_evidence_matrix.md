# Phase 19 Evidence Matrix

Status legend: `implemented locally`, `planned`, or `external evidence required`.

| Contract requirement | Status | Implementation / evidence | Rollback or boundary |
| --- | --- | --- | --- |
| Structured operational logging and redaction | implemented locally | `app/core/logging.py`, `app/core/observability.py`, `test_phase19_observability.py` | Local JSON logs only; no external exporter. |
| Browser to BFF to API correlation | implemented locally | `frontend/src/lib/api.ts`, BFF route, API middleware, BFF contract and backend tests | Remove correlation forwarding without changing auth/cookie behavior. |
| API to job to worker correlation | implemented locally | Server-owned job context and worker header forwarding | Existing job schema/tenant authorization unchanged. |
| Non-mutating readiness | implemented locally | Admin endpoint and `scripts/check_operational_readiness.py` | Read-only metadata; no provider, storage, or tenant action. |
| Centralized logs, errors, traces, metrics, retention, dashboard RBAC | planned | 19D/19E | No exporter endpoint or credential is accepted in 19A. |
| Shared distributed rate limiting | implemented locally, deployment evidence pending | PostgreSQL `rate_limit_buckets`, `app/rate_limits/service.py`, rate-limit tests, cleanup integration, and aggregate admin diagnostics | Disabled by default. Preview must set a server-only pepper and exact trusted proxy CIDRs, use `shadow` first, then explicitly select `enforce`. Public-demo in-process limiting remains the rollback fallback only while shared limiting is disabled. |
| CSP, HSTS, CORS, CSRF, SSRF, upload scanning | implemented locally, deployment evidence pending | Next.js report-only CSP/minimum browser headers, exact FastAPI CORS/origin checks and request bounds, BFF exact origin/backend/redirect checks, and required-scanner contract with fail-closed upload behavior; `test_phase19c_security.py`, BFF/security-header checks | CSP remains report-only and HSTS off by default. Production private storage cannot enable without required scanning. WAF/bot policy, scanner service/quarantine, final origins, HTTPS/HSTS review, and report evidence remain pending. |
| Alerting, synthetics, SLOs, status integration | implemented locally, deployment evidence pending | Aggregate-only admin monitoring snapshot, local candidate evaluator, private operations page, `scripts.run_synthetic_checks.py`, `test_phase19d_monitoring.py`, and [`operations/monitoring_and_alerting.md`](operations/monitoring_and_alerting.md) | No exporter, pager, status provider, dashboard destination, synthetic identity, or customer-data probe is configured. Candidate delivery remains `not_implemented`. |
| Backup/restore and secret rotation | implemented locally, deployment evidence pending | Metadata-only isolated restore verifier, opt-in retention guard, `operations/backup_restore_runbook.md`, `operations/secret_inventory.md`, and `test_phase19e_recovery_operations.py` | No provider backup or production restore is implemented or claimed. Encryption-key migration, approved RPO/RTO, provider drill, secret-store audit, and emergency exercises remain required. |
| Incident response | planned | 19G | Existing cleanup/recovery commands remain unchanged. |
| CI security scanning and protected branch rules | planned, blocker recorded | `npm audit --omit=dev` on 2026-07-28 reports three high-severity production advisories: `next` (direct), `postcss`, and `sharp` (transitive). | Phase 19F must remediate or approve time-bounded exceptions before Phase 19 can complete; existing CI remains required. |
| Load, worker-loss, provider-failure exercises | planned | 19H | Real Vast rentals remain disabled. |
| Controlled Phase 18 deployment evidence | external evidence required | 19I, Phase 18 archive, Phase 22 | `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=false`; JSON RAG remains fallback. |

The matrix is updated as slices gain code, tests, deployment evidence, owners, and a tested rollback. Phase 19 is not complete until every Phase 19 contract gate is evidenced and no unresolved critical/high security finding remains.
