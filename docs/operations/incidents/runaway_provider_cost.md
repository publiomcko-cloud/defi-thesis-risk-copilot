# Runaway Provider Cost — `provider.cost`

Owner roles: provider owner (primary), platform owner (backup). Communication
authority: assigned incident communications authority. Treat unexpected active
provider cost or a breached budget as `SEV1` until containment is confirmed.

## Detection

Triggers include provider ledger/reconciliation mismatch, budget threshold,
cleanup failure, unexpected session, or provider notice. Real Vast.ai rentals
remain disabled and must not be enabled while responding.

## Immediate containment

Disable new provider submissions, revoke or pause the affected scoped provider
credential, request cancellation/cleanup, and preserve the job/session/cost
ledger. Do not assume a cancelled/failed provider job cost is zero.

## Eradication and scope

Reconcile requested resources, known provider resources, actual/estimated cost,
reservations, cleanup state, authorization, and job linkage. Mark uncertain
outcomes `reconciliation_required` and retain a conservative reservation.

## Recovery and rollback

Destroy or verify provider resources through the approved provider procedure,
record actual cost when known, and release only unused reservation. Restore
submission only after limits, scopes, credential status, and reconciliation
are verified. Rollback means keeping provider execution disabled/dry-run.

## Communications

The communications authority and platform owner decide any finance/vendor or
user communication after cost and scope are verified.

## Evidence

Record provider session/job/cost ledger references, cleanup/reconciliation
outcome, budget decision, provider support reference, and authorization. Never
record provider tokens, account identifiers, or billing documents here.

## Retrospective

Review reservation ceilings, provider fail-closed guards, cleanup/retry logic,
credential scopes, alert thresholds, and exercise coverage.
