# Database or Object-Storage Outage — `operations.database-storage`

Owner roles: platform owner (primary), recovery owner (backup). Communication
authority: assigned incident communications authority. Treat loss of core
database availability, object integrity, or an unsafe fallback as `SEV1`.

## Detection

Triggers include `/ready` failure, approved synthetic failure, database or
storage provider notice, missing JSON fallback, repeated upload/object errors,
or retrieval integrity alert. Keep provider details in the private incident
record only.

## Immediate containment

Freeze unsafe writes, ingestion, retention cleanup, and migration activity.
Do not retry unboundedly or bypass authorization/storage policy. Use the JSON
public fallback only when it is independently healthy and within its documented
public-only scope.

## Eradication and scope

Classify database, connection pool, migration, object-store, policy, or
application failure using approved aggregate/provider evidence. Confirm whether
metadata and object availability diverge without exposing private keys/content.

## Recovery and rollback

Follow [`../backup_restore_runbook.md`](../backup_restore_runbook.md) for any
restore: provider backup/object parity, isolated target, metadata-only manifest,
and recorded RPO/RTO evidence are required. Return traffic only after health,
authorization, job recovery, and object-reference verification pass. Rollback
means disabling the affected durable path or returning to a prior compatible
release, never using Alembic downgrade as data recovery.

## Communications

The communications authority publishes availability updates only after the IC
has a verified scope and recovery estimate. Do not expose provider internals or
customer data.

## Evidence

Record alert/synthetic/provider references, affected boundary, UTC timeline,
safe readiness results, restore/migration revision references, and recovery
verification. Exclude URLs with credentials, dumps, object keys, and content.

## Retrospective

Review provider SLA/backup evidence, fallback behavior, connection limits,
object/database parity, retention guard, monitoring, and RPO/RTO assumptions.
