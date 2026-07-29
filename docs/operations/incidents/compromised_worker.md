# Compromised Worker — `workers.compromised`

Owner roles: worker owner (primary), security owner (backup). Communication
authority: assigned incident communications authority. Treat a credible worker
credential or executor compromise as `SEV1` until the worker is contained.

## Detection

Triggers include an unexpected claim/heartbeat, invalid protocol behavior,
credential exposure notice, host alert, stale worker anomaly, or untrusted
provider execution signal. Record worker identifiers only in private evidence.

## Immediate containment

Revoke or disable the scoped worker credential, stop the worker from claiming,
and move active work to cooperative cancellation where safe. Do not expose an
internal worker endpoint through the BFF or grant a replacement broader scope.

## Eradication and scope

Review worker registration, credential lifecycle/audit events, permitted job
types, organization scope, claims, heartbeats, completions, artifacts, and
provider requests. Treat uncertain provider outcomes conservatively and
preserve reservations for reconciliation.

## Recovery and rollback

Build or verify a trusted worker image/host, issue a new least-privilege scoped
credential, deploy it with no public inbound port, and confirm a synthetic
claim/heartbeat/completion before re-enabling capacity. Rollback revokes the
replacement and leaves affected job types paused until another trusted worker
is ready.

## Communications

The communications authority and security owner decide notifications after
verifying job, tenant, artifact, and provider impact. Do not disclose worker
tokens, internal addresses, host details, or job payloads.

## Evidence

Record worker/credential lifecycle references, allowed scope, affected job
references, containment time, replacement verification, reconciliation status,
and communication decisions. Exclude credential values and payload content.

## Retrospective

Review credential rotation, worker image/host controls, no-inbound deployment,
lease/cancellation behavior, BFF blocking, monitoring, and provider safeguards.
