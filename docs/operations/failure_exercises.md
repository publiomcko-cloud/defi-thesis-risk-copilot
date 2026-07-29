# Phase 19H Isolated Failure Exercises

Status: **implemented local/CI exercise foundation; no production chaos test,
real provider, customer data, pager, or incident-record system is configured.**

The fixed catalog in `backend/scripts/run_phase19_exercises.py` exercises
existing deterministic, fake, and isolated test paths. It accepts only catalog
IDs, never shell fragments, user-selected commands, provider credentials, or
browser-supplied parameters. It captures child output and reports only safe
exercise ID, runbook ID, duration, and status.

## Required safety configuration

The runner defaults to a dry run. To run it, use an isolated database and set:

```env
APP_ENV=exercise
OPERATIONS_EXERCISES_ENABLED=true
OPERATIONS_EXERCISES_ISOLATED=true
OPERATIONS_EXERCISE_TIMEOUT_SECONDS=180
VAST_ENABLED=false
VAST_DRY_RUN=true
VAST_REAL_RENTALS_ENABLED=false
RUN_POSTGRES_INTEGRATION=true
DATABASE_URL=<isolated PostgreSQL/pgvector URL>
```

It refuses enabled execution in `production`, without the explicit isolation
flag, with a timeout outside 5–600 seconds, or if Vast dry-run is false / real
rentals are enabled. The parent process verifies those gates, then child test
processes receive the exercise flag disabled so their production-negative
configuration tests remain meaningful.

Never point this runner at production, a shared customer database, an active
provider account, or a non-synthetic storage target. The CI workflow creates an
ephemeral pgvector service, supplies no deployment/provider secrets, and runs
only on a weekly schedule or manual dispatch.

## Catalog and incident mapping

| Exercise ID | Controlled evidence | Incident runbook |
| --- | --- | --- |
| `rate-limit-saturation` | Burst/sustained shared-limit behavior and PostgreSQL one-winner admission | `queue.duplication` |
| `queue-admission` | Capacity reservation and durable admission limits | `queue.duplication` |
| `worker-loss-recovery` | Lease expiry, stale mutation rejection, cancellation, and recovery | `workers.compromised` |
| `provider-timeout-failure` | Fake/dry-run provider timeout, cleanup, and conservative cost behavior | `provider.cost` |
| `storage-outage` | Private-storage and upload-scanner failure paths | `operations.database-storage` |
| `pgvector-corruption-recovery` | Derived retrieval corruption repair, rollback, and tenant filtering | `retrieval.vector-corruption` |
| `migration-rollback` | Reversible migration and seeded-data preservation tests | `deployment.failed-migration` |
| `authorization-negative` | Adversarial private/organization access denials | `tenant.exposure` |
| `database-recovery` | Metadata-only isolated restore mismatch detection | `operations.database-storage` |
| `frontend-accessibility` | Semantic landmarks, named navigation, and visible keyboard focus contract | `identity.account-takeover` |

List or dry-run the catalog without enabling it:

```bash
cd backend
source .venv/bin/activate
python -m scripts.run_phase19_exercises --list
python -m scripts.run_phase19_exercises --exercise database-recovery
```

Run all fixed exercises only in the approved isolated environment:

```bash
python -m scripts.run_phase19_exercises --run
```

## Local evidence and limits

The complete ten-exercise catalog passed locally against the isolated pgvector
database during Phase 19H implementation. This validates test harnesses and
existing safety behavior, not capacity at production traffic, a provider SLA,
customer-data recovery, production accessibility, alert delivery, or an
incident response outcome.

The semantic accessibility contract covers every route page's main landmark and
heading (including explicit delegated pages), named primary navigation, and
visible keyboard focus styling. It is a baseline contract, not a substitute for
manual assistive-technology review or a full automated WCAG audit.

## Stop and rollback

Stop the runner or cancel the GitHub Actions job if a test becomes unexpectedly
slow, uses a non-isolated dependency, or signals a control failure. Do not
retry a provider operation manually. Run
`python -m scripts.recover_durable_jobs --dry-run` before any recovery mutation, then follow the mapped Phase 19G
runbook. The runner writes no durable exercise record; use the approved private
incident/evidence system for a real exercise or failure.

To roll back this slice, disable the exercise settings, stop the scheduled
workflow through a reviewed change, and retain the existing Phase 17 job
recovery/JSON RAG fallback. This does not activate or roll back durable RAG,
delete data, or change real-provider settings.
