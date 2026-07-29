# Phase 19G Incident Response and Security Operations

Status: **implemented local runbook foundation; external ownership, delivery,
and exercised-production evidence remain required.** These procedures are
versioned response guidance, not an incident tracker, contact directory, pager,
or storage location for sensitive evidence.

## Use and safety boundaries

Open an incident in the approved private operations system whenever a critical
signal, credible security report, or integrity failure matches this registry.
Assign an incident commander (IC), technical lead, and communications authority
there. The named primary and backup people, current contact methods, on-call
schedule, evidence-system URL, and status-page authority must never be placed
in this repository.

Do not put credentials, session cookies, database URLs, object keys, signed
URLs, customer content, raw logs, forensic images, or unredacted tenant
identifiers in a pull request, issue, CI artifact, or this directory. Preserve
only redacted references, timestamps, hashes where approved, and evidence
record identifiers in the operational system.

The first responder may take documented reversible containment action. Actions
that affect multiple tenants, public communications, data deletion, a database
restore, or any real provider must be approved by the IC and communication
authority. Real Vast.ai rentals remain disabled; do not enable them as an
incident workaround.

## Severity and escalation

| Severity | Meaning | Initial response | Communication authority | Escalate to |
| --- | --- | --- | --- | --- |
| `SEV1` | Active tenant exposure, confirmed credential compromise, unavailable core service, or uncontrolled cost/security impact | Acknowledge immediately; contain or disable the affected boundary; begin a timeline | Assigned communications authority | Platform owner and security owner immediately; legal/privacy review when data may be affected |
| `SEV2` | Credible high-risk degradation or contained compromise with no confirmed broad exposure | Acknowledge within 30 minutes; contain and investigate | Assigned communications authority | Primary owner, backup owner, and platform owner |
| `SEV3` | Limited degradation, failed control, or suspected issue without material impact | Triage in the current support window; create corrective work | Technical lead | Service owner and backup owner |
| `SEV4` | Informational/false-positive candidate | Record disposition and close or schedule review | Technical lead | Service owner when trend analysis is needed |

If severity is uncertain, begin at the higher level and reduce only after the
IC records the reason. Existing local alert candidates are not pager delivery;
they are inputs to this process once an external receiver and owners are
approved.

## Evidence handling

1. Create the incident record in the approved private system and record the
   stable correlation ID, alert key, runbook ID, affected service boundary, and
   UTC timestamps. Do not record raw customer queries or tokens.
2. Preserve immutable provider/audit references where available. Grant access
   only to the IC, technical lead, security owner, and any required
   privacy/legal reviewer.
3. Keep a separate decision timeline: detection, containment, scope decision,
   recovery verification, communications approval, and closure. Mark unknowns
   explicitly rather than guessing.
4. Apply the normal retention policy and legal hold procedure. Do not destroy
   evidence through cleanup, account deletion, retention, or object lifecycle
   jobs until the IC explicitly releases the hold.
5. Capture safe evidence references rather than copying source documents,
   report content, embeddings, signed URLs, credential values, or database
   dumps into an incident record.

## Runbook registry

Each runbook has an owner role and backup role to assign in the approved
operations system before deployment. Every row supplies a containment action,
recovery dependency, communication authority, and evidence path through the
linked procedure.

| Alert or trigger ID | Runbook ID | Procedure | Primary role / backup role |
| --- | --- | --- | --- |
| `operations.database` | `operations.database-storage` | [Database or object-storage outage](database_or_storage_outage.md) | Platform owner / recovery owner |
| `operations.retrieval` | `retrieval.vector-corruption` | [Vector or retrieval integrity](vector_corruption.md) | Knowledge owner / platform owner |
| `operations.queue`, `operations.jobs` | `queue.duplication` | [Queue duplication](queue_duplication.md) | Worker owner / platform owner |
| `operations.workers` | `workers.compromised` | [Compromised worker](compromised_worker.md) | Worker owner / security owner |
| `operations.providers` | `provider.cost` | [Runaway provider cost](runaway_provider_cost.md) | Provider owner / platform owner |
| Security report or scan | `security.credential-exposure` | [Credential exposure](credential_exposure.md) | Security owner / platform owner |
| Authentication anomaly | `identity.account-takeover` | [Account takeover](account_takeover.md) | Identity owner / security owner |
| Authorization or privacy defect | `tenant.exposure` | [Tenant data exposure](tenant_data_exposure.md) | Security owner / platform owner |
| Scanner or source-integrity signal | `knowledge.malicious-source` | [Malicious upload or source](malicious_source.md) | Knowledge owner / security owner |
| Migration error or integrity mismatch | `deployment.failed-migration` | [Failed migration](failed_migration.md) | Platform owner / recovery owner |

`operations.*` IDs are the stable identifiers already emitted by the local
aggregate monitoring response. They intentionally remain identifiers rather
than browser links: the administrator page contains no customer, incident, or
on-call detail, and alert delivery is still disabled. External alert delivery
must link the corresponding registry procedure only after the operator records
the approved evidence location and receiver test.

## Tabletop exercise process

Use [tabletop_exercises.md](tabletop_exercises.md) in an isolated, synthetic
environment. A tabletop does not authorize production testing, secret rotation,
provider rental, data deletion, or customer communication. For each exercise,
record only the scenario ID, date, facilitator, assigned roles, elapsed
containment/recovery decisions, safe evidence reference, gaps, owner, and due
date in the approved operations system.

Runbook changes are reversible through normal version control. Operational
rollback means reversing the containment action only after the recovery checks
in the relevant procedure pass and the IC records approval.
