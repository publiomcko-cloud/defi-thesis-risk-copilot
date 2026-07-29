# Phase 19E Backup and Restore Runbook

Status: **local verification foundation only.** This repository does not create
or store production database or object backups. An approved provider and an
operator-owned evidence location are required before recovery claims are made.

## Objectives and boundaries

The provisional recovery objectives are an RPO of 24 hours and an RTO of 240
minutes. They are planning values, not approved service commitments, until an
owner records a successful provider restore drill. Alembic upgrade or downgrade
is schema management, never data recovery.

Never copy production customer data into local development. Never place backup
archives, database URLs, storage keys, service-role keys, encrypted blobs, or
secret values in this repository, a browser response, CI output, or ticket
comment.

## Required provider evidence

Before enabling destructive retention guarding in a private environment, record
an evidence reference owned by operations that proves all of the following:

1. PostgreSQL/Supabase backup schedule, retention window, encryption-at-rest,
   and restore operator access.
2. Private object-storage versioning/retention or an approved immutable export
   strategy, including a matching restore procedure.
3. Database and object backup timestamps within the approved RPO window.
4. A synthetic or sanitized isolated restore target, never a local copy of
   production customer data.
5. Named primary and backup recovery owners.
6. A recorded RTO measurement, migration state, verification result, and
   cleanup decision.

`BACKUP_RESTORE_EVIDENCE_REFERENCE` is an identifier such as an approved
change/evidence record. It is not a URL containing credentials and it is never
returned by an application endpoint.

## Isolated restore drill

1. Obtain written approval, scope, RPO/RTO target, and provider snapshot IDs in
   the approved operations system.
2. Create an isolated database and private object-storage target with the same
   schema/extensions. Do not reuse a production application target.
3. Restore the provider-approved database snapshot and matching private objects
   into that isolated target. Verify encryption and private bucket policy with
   the provider controls.
4. Run migrations only as an explicitly recorded compatibility step. Do not use
   a migration downgrade to recover lost rows or objects.
5. Run the application against the isolated target with public durable-RAG
   fallback flags unchanged and `VAST_DRY_RUN=true`.
6. With the feature flag enabled only in the isolated drill environment, create
   a metadata-only manifest before restore or from an equivalent approved
   synthetic source:

   ```bash
   cd backend
   source .venv/bin/activate
   BACKUP_RESTORE_DRILL_ENABLED=true \
   python -m scripts.run_sanitized_restore_drill \
     --write-manifest /approved-isolated-path/restore-manifest.json
   ```

7. Verify the manifest against the restored isolated database:

   ```bash
   BACKUP_RESTORE_DRILL_ENABLED=true \
   python -m scripts.run_sanitized_restore_drill \
     --verify-manifest /approved-isolated-path/restore-manifest.json
   ```

   The manifest verifies only safe counts and salted fingerprints for analysis
   requests, reports, jobs, artifacts, knowledge sources/documents/versions,
   chunks, and embedding metadata. It contains no report content, strategy
   input, source content, storage key, checksum, user identity, or credential.
   It is verification evidence, not a backup artifact.
8. Verify report/job/knowledge metadata and the presence of object references
   through authenticated server-side application paths. Do not inspect raw
   object keys in browser tooling.
9. Record start/end time, observed RPO/RTO, provider snapshot references,
   migration revision, verification output, owner approval, and cleanup of the
   isolated target in the approved evidence system.

The CLI refuses to run when disabled or in `APP_ENV=production`. Its local test
coverage is not proof of a provider restore.

## Retention guard

Existing cleanup remains unchanged by default. After a successful documented
restore drill, an operator may set:

```env
BACKUP_RETENTION_GUARD_ENABLED=true
BACKUP_RESTORE_EVIDENCE_REFERENCE=approved-evidence-identifier
```

With the guard enabled, non-dry retention cleanup requires the evidence
reference. Dry runs remain side-effect-free and do not require it. Disable the
guard only through an approved operational change; that rollback does not
delete data or alter Phase 17 job recovery.

## Failure handling

- Backup unavailable or stale: stop retention cleanup, open an operational
  incident, and preserve affected records.
- Restore verification mismatch: keep the isolated target for evidence, do not
  activate new feature flags, and reconcile provider snapshot/object timing.
- Migration incompatibility: restore the provider snapshot into a fresh
  isolated target and follow the migration rollback procedure; do not attempt
  row recovery with Alembic.
- Evidence reference missing: leave the retention guard disabled or block the
  destructive cleanup command. Never invent an evidence record.

Phase 22 owns final deployed recovery and launch approval.
