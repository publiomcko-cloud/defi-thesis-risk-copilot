# Tenant Data Exposure — `tenant.exposure`

Owner roles: security owner (primary), platform owner (backup). Communication
authority: assigned incident communications authority with privacy/legal review.
Treat any credible cross-tenant read, write, export, artifact, or citation path
as `SEV1` until scope is disproven.

## Detection

Triggers include an authorization test failure, user report, audit anomaly,
retrieval/citation isolation defect, or provider policy alert. Preserve only
redacted request/correlation and evidence references.

## Immediate containment

Disable the affected route, feature flag, worker job type, or retrieval path.
Prefer the documented JSON public fallback when it is safe; do not broaden
access or inspect unrelated tenant content to investigate.

## Eradication and scope

Reproduce with synthetic accounts in an isolated environment, identify the
server-derived scope or authorization predicate failure, and review approved
audit evidence for the affected boundary. Freeze destructive retention for
potential evidence under IC direction.

## Recovery and rollback

Deploy a reviewed authorization fix, run negative tenant-isolation tests, and
verify no private/organization artifact, report, source, or citation leaks.
Rollback means keeping the affected feature disabled or returning to the prior
safe fallback, never restoring a known-vulnerable route.

## Communications

The communications authority, privacy/legal reviewer, and IC determine
notification obligations after validated scope. Technical responders do not
make customer or public statements independently.

## Evidence

Record affected boundary, safe reproduction reference, code/deployment version,
scope decision, containment and verification timestamps, and communication
approval. Do not copy tenant records, report text, object keys, or queries.

## Retrospective

Review server-derived filters, BFF/API controls, tests, audits, provider RLS,
and whether monitoring needs an aggregate-only detection improvement.
