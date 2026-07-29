# Credential Exposure — `security.credential-exposure`

Owner roles: security owner (primary), platform owner (backup). Communication
authority: assigned incident communications authority. Treat a credible exposed
credential as `SEV1` until scope is disproven.

## Detection

Triggers include a secret-scanner match, provider notification, unusual
credential use, a leaked browser/server response, or a human report. Capture
only the scanner/provider alert reference and correlation ID.

## Immediate containment

Stop the affected deployment or workflow path, revoke the exposed credential
at its authority, and disable dependent worker/provider access where needed.
Do not paste the value into the incident record or try it against production.

## Eradication and scope

Use provider audit evidence to identify the credential identifier, issuing
system, time window, scopes, and dependent services. Search approved logs and
repository history with access control; preserve results as references. Follow
[`../secret_inventory.md`](../secret_inventory.md) for the credential class.

## Recovery and rollback

Issue least-privilege replacements, deploy them through server/worker secret
stores, verify a bounded safe operation, and revoke all predecessors. Rollback
means disabling the affected integration, not restoring the exposed value.

## Communications

The communications authority decides audience, timing, and legal/privacy
review after scope assessment. Do not make public claims before affected scope
and containment are recorded.

## Evidence

Record the alert reference, credential identifier (not value), revoke/issue
timestamps, audit reference, affected service boundaries, verification result,
and any required notification decision in the approved private system.

## Retrospective

Review origin, time-to-revoke, scope minimization, secret-store controls,
scanner coverage, and whether any runbook or logging change is required.
