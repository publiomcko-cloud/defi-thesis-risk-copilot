# Queue Duplication — `queue.duplication`

Owner roles: worker owner (primary), platform owner (backup). Communication
authority: assigned incident communications authority. Begin at `SEV2`; raise
to `SEV1` if authorization, report isolation, or provider cost may be affected.

## Detection

Triggers include duplicate report/artifact evidence, conflicting job events,
unexpected capacity reservations, worker overlap, or queue/dead-letter alerts.
Use job/correlation IDs only in the approved private incident system.

## Immediate containment

Stop new claims for the affected job type or worker scope, request cancellation
at safe points, and run recovery in dry-run mode first. Do not delete jobs,
reports, events, artifacts, or cost records to make the queue look healthy.

## Eradication and scope

Inspect atomic claim, lease generation, heartbeat, idempotency, authorization,
and capacity/cost ledger evidence. Determine whether execution duplicated,
completion merely retried, or a provider outcome requires reconciliation.

## Recovery and rollback

Use the Phase 17 recovery/reconciliation procedure to release only justified
reservations and preserve uncertain provider cost conservatively. Re-enable
claims only after one-winner, stale-lease, idempotency, and tenant checks pass.
Rollback is pausing the affected job type or worker credential.

## Communications

The communications authority coordinates any user impact after verifying
whether duplicate outputs, delays, or cost/accounting exposure occurred.

## Evidence

Record job/event/artifact/cost references, worker scope, dry-run output
reference, decision timeline, reconciliation result, and post-recovery test.
Do not record worker credential values or report content.

## Retrospective

Review lease horizons, cancellation, recovery, capacity reconstruction,
idempotency boundaries, provider accounting, alerts, and failure exercises.
