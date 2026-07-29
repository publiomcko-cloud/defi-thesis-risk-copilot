# Failed Migration — `deployment.failed-migration`

Owner roles: platform owner (primary), recovery owner (backup). Communication
authority: assigned incident communications authority. A migration that causes
availability loss or data-integrity uncertainty is `SEV1`.

## Detection

Triggers include deployment/readiness failure, Alembic error, schema mismatch,
application exceptions after revision change, or restore verification mismatch.
Record the migration revision and deployment reference, not a database URL.

## Immediate containment

Freeze deploys and further migrations, stop destructive cleanup/ingestion,
and keep the last known compatible application release available. Do not run an
unreviewed downgrade against production or edit rows manually.

## Eradication and scope

Determine whether the failure is pre-transaction, partially applied schema,
application compatibility, extension/provider, or data integrity. Reproduce on
an isolated synthetic/approved restore target before selecting a change.

## Recovery and rollback

Use the migration's documented reversible path only when its preconditions are
known to hold. Otherwise restore a provider-approved database/object pair to an
isolated target and follow [`../backup_restore_runbook.md`](../backup_restore_runbook.md).
Alembic downgrade is schema management, not row/object recovery. Resume only
after readiness, migration state, tenant isolation, and application checks pass.

## Communications

The communications authority provides deployment/availability updates after
the IC confirms impact. Escalate data-integrity uncertainty to recovery and
privacy/legal owners before any broad statement.

## Evidence

Record deployment/revision references, safe error category, transaction state
decision, isolated rehearsal/restore reference, approval, and verification.
Exclude SQL dumps, connection strings, raw records, and stack traces with data.

## Retrospective

Review migration design, downgrade preconditions, preflight, backup evidence,
CI rehearsal, rollout sequencing, and release approval controls.
