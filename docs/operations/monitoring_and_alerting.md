# Phase 19D Monitoring and Alerting Runbook

Status: **local monitoring foundation only.** No telemetry exporter, pager,
status-page provider, synthetic credential, or customer-data probe is configured
by this repository.

## Signals and objectives

| Signal | Local source | Initial objective | Candidate severity | Runbook ID |
| --- | --- | --- | --- | --- |
| Availability | approved external synthetics, not local process memory | 99.5% | critical | `operations.database` |
| Database and JSON fallback | admin monitoring snapshot | ready | critical | `operations.database`, `operations.retrieval` |
| Queue depth and age | aggregate jobs table | under configured depth; age under 900 seconds | warning | `operations.queue` |
| Dead letters | aggregate jobs table | zero | warning | `operations.jobs` |
| Worker freshness | aggregate worker table | zero stale/overdue workers | warning | `operations.workers` |
| Retrieval | privacy-safe retrieval events | empty rate under 80%; max latency under 5000 ms | warning | `operations.retrieval` |
| Provider cleanup | aggregate provider-session state | zero failed cleanup tasks | warning | `operations.providers` |

Thresholds are environment configuration, not browser input. A local candidate
is deduplicated by stable alert key and carries no tenant, job, worker, query,
source, credential, or response-body data. Candidate generation does **not**
send an alert.

## Local inspection

Set only in an approved private environment:

```env
OPERATIONS_MONITORING_ENABLED=true
OPERATIONS_ALERT_EVALUATION_ENABLED=true
```

An authenticated platform administrator may inspect
`GET /api/admin/operations/monitoring` or the private `/admin/operations` page.
The response is aggregate-only and reports `alert_delivery=not_implemented`.
Do not treat it as a pager, an uptime claim, or a storage-policy probe.

## Synthetic checks

Synthetics are disabled by default. The public-only command requires explicit
operator configuration, an origin-only URL, and an exact server-side allowlist:

```bash
cd backend
source .venv/bin/activate
OPERATIONS_MONITORING_ENABLED=true \
OPERATIONS_SYNTHETIC_CHECKS_ENABLED=true \
OPERATIONS_SYNTHETIC_ALLOWED_ORIGINS=https://approved-synthetic-target.example \\
python -m scripts.run_synthetic_checks --base-url https://approved-synthetic-target.example
```

It checks only `/health`, `/ready`, and `/api/demo/status`; it prints status and
latency, never response bodies. The optional `--authenticated` check uses the
server-side `SYNTHETIC_CHECK_BEARER_TOKEN` environment variable for
`/api/auth/me`. Do not put that token in a command argument, repository file,
browser variable, log, or CI output. Use a dedicated synthetic identity with no
customer data and a documented owner.

## Before external delivery

Phase 19D is not deployed-complete until an operator records:

1. a telemetry/error/trace destination, data classification, retention, and RBAC;
2. named primary and backup alert owners, severity and escalation policy;
3. a non-production alert receiver test and alert-deduplication evidence;
4. a safe synthetic tenant, credential rotation/revocation procedure, and target;
5. dashboard ownership plus SLI/SLO/error-budget review; and
6. a rollback procedure that mutes a faulty route while retaining core health checks.

These are Phase 19D deployment gates. Phase 22 retains final launch approval.
