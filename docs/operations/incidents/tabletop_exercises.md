# Phase 19G Tabletop Exercises

Status: **scripts ready; no deployed incident exercise is claimed.** Run these
only with synthetic data and an approved facilitator. The exercise record lives
in the private operations system, not this repository.

## Facilitation rules

1. Assign an IC, technical lead, communications authority, primary owner, and
   backup owner before starting. Use role placeholders when the production
   roster is not yet approved.
2. Start from the stated inject. Ask participants to identify the runbook,
   severity, containment, recovery dependency, evidence path, and rollback.
3. Do not use production customer data, actual secrets, real provider
   credentials, paid resources, public status messages, or destructive actions.
4. Record elapsed decision times and gaps in the approved private system. A
   failed decision is evidence for corrective work, not a reason to conceal it.
5. Close only after an owner and due date exist for every gap. Re-run the
   affected scenario after remediation.

## Scenario scripts

| Scenario ID | Inject | Expected first decisions | Completion evidence |
| --- | --- | --- | --- |
| `TT-19G-01` | A scanner reports a credential-like value in a commit. | `SEV1`/`SEV2` triage, stop exposure path, revoke/rotate through secret inventory, preserve audit references. | `security.credential-exposure` record, rotation evidence reference, scan rerun result. |
| `TT-19G-02` | A user reports unfamiliar authenticated activity after a recovery flow. | Contain sessions/recovery path, preserve audit references, assess affected account/organization scope. | `identity.account-takeover` timeline and verification decision. |
| `TT-19G-03` | A test proves one tenant can view another tenant's metadata. | Treat as `SEV1`, disable affected endpoint/feature, preserve correlation/audit references, assess scope before communication. | `tenant.exposure` containment and authorization-regression evidence. |
| `TT-19G-04` | The upload scanner returns a non-clean result for a synthetic document. | Reject/quarantine path, confirm no object/retrieval activation, inspect scanner boundary. | `knowledge.malicious-source` evidence and safe re-test. |
| `TT-19G-05` | A synthetic worker replay suggests two reports may be produced for one job. | Pause claims for the scope, preserve job event references, run recovery dry-run before mutations. | `queue.duplication` reconciliation and idempotency result. |
| `TT-19G-06` | Provider accounting shows an unexpected reservation/cost increase. | Disable provider submissions, keep real rentals disabled, reconcile conservatively, preserve cost ledger references. | `provider.cost` reconciliation and approval record. |
| `TT-19G-07` | Readiness fails for the database or private object storage. | Declare degradation, stop unsafe writes/cleanup, select JSON fallback only when documented, begin isolated recovery plan. | `operations.database-storage` decision timeline and recovery verification reference. |
| `TT-19G-08` | Retrieval metrics reveal stale/corrupt vectors for a synthetic source. | Disable durable primary/shadow path as appropriate, retain JSON fallback, avoid cross-tenant inspection, schedule rebuild. | `retrieval.vector-corruption` integrity and fallback evidence. |
| `TT-19G-09` | A migration succeeds partway then application readiness fails. | Freeze deploys, stop further migration, identify last compatible release, use isolated restore procedure. | `deployment.failed-migration` revision, decision, and recovery evidence. |
| `TT-19G-10` | A worker credential is suspected compromised. | Revoke/disable worker, request cancellation where safe, issue replacement only after scope review, verify no stale credential succeeds. | `workers.compromised` credential lifecycle and recovery evidence. |

The Phase 19G rollout gate requires a facilitator-reviewed exercise for every
scenario, named primary/backup owners, communication authority, a containment
decision, recovery dependency, and evidence reference. Until those records
exist, this slice is implemented locally but not deployment-complete.
