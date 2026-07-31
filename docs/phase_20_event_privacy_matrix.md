# Phase 20 Event, Consent, and Retention Matrix

Status: **Phase 20B approved subset locally implemented; production activation
remains blocked pending qualified privacy/legal review**

This artifact defines the Phase 20 analytics purposes, event names, metadata
allowlists, consent behavior, and retention classes. The exact Phase 20B
subset is implemented behind a default-off flag; no production collection is
authorized. Operational telemetry, security/audit evidence,
billable usage, billing records, and support cases remain separate domains.

Related artifacts:

- [`phase_20_threat_model.md`](phase_20_threat_model.md);
- [`phase_20_event_taxonomy.schema.json`](phase_20_event_taxonomy.schema.json);
- [`phase_20_event_taxonomy_examples.json`](phase_20_event_taxonomy_examples.json);
- [`phase_20_data_model_review.md`](phase_20_data_model_review.md).

---

## 1. Existing lifecycle authority and gaps

The current repository provides:

- `consent_records` for accepted terms/privacy document versions;
- `POST /api/consents`, restricted to `terms` and `privacy`;
- `GET /api/consents` and account-export consent projection;
- `POST` signup consent synchronization from server-recognized Supabase
  metadata;
- `DELETE /api/account` for account disablement plus job and knowledge
  disposal;
- `scripts.cleanup_expired_data` for dry-run/retention cleanup;
- organization membership/deletion authorization and audit.

The existing `consent_records` row captures user, document type/version,
acceptance timestamp, nullable withdrawal timestamp, and bounded metadata. It
does not currently provide:

- a public withdrawal endpoint;
- a granular analytics purpose;
- an explicit grant/deny/withdraw decision type;
- a consent-policy version independent of a terms/privacy document;
- immutable previous-decision linkage;
- an idempotency key for concurrent preference changes;
- anonymous analytics evidence;
- organization export.

Implemented Phase 20B decision:

- keep `consent_records` authoritative for terms/privacy acceptance;
- do not reinterpret terms/privacy acceptance as analytics consent;
- use a purpose-specific immutable preference decision ledger for the approved
  `product_improvement` subset;
- keep the existing account export/deletion routes and cleanup command as the
  lifecycle authorities, extended through Phase 20 projections/hooks;
- implement organization export in 20H through the existing organization
  authorization/lifecycle service, not a competing service.

The implementation authority and production limitation are recorded in
[`decisions/phase_20b_analytics_approval.md`](decisions/phase_20b_analytics_approval.md).

---

## 2. Purpose registry

| Purpose ID | Description | Domain | Consent/legal-basis position | Allowed data | Approval |
| --- | --- | --- | --- | --- | --- |
| `product_improvement` | Understand bounded use and failure of product capabilities | Optional product analytics | Explicit authenticated-user opt-in for implementation/private validation; production activation requires qualified review | Code-owned event name, time, actor class, and exact allowlisted low-cardinality dimensions | **Implemented, production disabled** |
| `onboarding_effectiveness` | Measure completion of approved onboarding steps | Optional product analytics | Default off; legal basis/consent unresolved | Step class and completion/failure class only; no email, auth subject, or form content | **Blocked**: privacy/legal, product |
| `commercial_funnel` | Understand plan-view, sandbox-checkout, and subscription lifecycle at aggregate level | Optional product analytics, distinct from billing | No collection before 20G and legal/commercial approval | Approved stage class only; no provider customer/subscription/payment identifiers | **Blocked**: privacy/legal, finance, product |
| `operational_reliability` | Detect availability, latency, queue, worker, storage, and retrieval failures | Phase 19 operational telemetry, not product analytics | Existing operational/security basis; analytics preference does not apply | Aggregate/redacted operational fields under Phase 19 | Existing Phase 19 authority |
| `security_audit` | Detect and investigate security/identity/privileged actions | Audit/security, not product analytics | Required security/audit processing | Existing bounded audit schema; no raw request body/secrets | Existing Phase 16/19 authority |
| `product_quota` | Admit or reject a product action within a period | Product quota, not product analytics | Contract/product control | Existing quota subject/action/period counters | Existing Phase 16 authority |
| `billable_usage` | Reconcile a chargeable unit and reversal | Usage ledger, not product analytics | Contractual/commercial; unresolved until 20F/20G review | Unit, server quantity, source lineage, period, reconciliation | **Blocked**: finance/legal/product |
| `billing_evidence` | Verify and reconcile customer/subscription state | Billing/audit, not product analytics | Contractual/legal; provider-specific | Normalized provider IDs/status/hash/version only; no full payload/card data | **Blocked**: billing ADR, finance/legal |
| `customer_support` | Resolve support, feedback, abuse, or privacy requests | Support case, not product analytics | Purpose-specific support/privacy basis | Bounded request fields under 20I; excluded from analytics/LLM/logs | **Blocked**: privacy/legal, support owner |

An action may produce records in more than one domain only through separate
purpose gates and separate schemas. An analytics row is never evidence of
quota use, billable usage, security audit, notification delivery, or billing
state.

---

## 3. Draft retention classes

The project owner approved the Phase 20B implementation bounds below. Their
production use still requires qualified privacy/legal review for applicable
jurisdictions.

| Class | Candidate maximum | Intended records | Export | Deletion/withdrawal | Approval |
| --- | --- | --- | --- | --- | --- |
| `none` | No row | Disallowed or unapproved optional analytics | Not applicable | Nothing collected | Fail-closed default |
| `analytics_short` | 30 days | Initial four optional feature events | Safe event projection in Phase 16 account export | Stop immediately; Phase 20B deletes existing rows in the withdrawal transaction | **Implemented, production disabled** |
| `analytics_standard` | 30 days for the initial Phase 20B subset | Low-volume optional adoption events | Safe event projection in Phase 16 account export | Same as above | **Implemented only for approved four-event subset** |
| `preference_evidence` | Account life plus 30 days after account deletion | Granular grant/deny/withdraw decisions | Include purpose, decision, policy version, and timestamps | Current projection removed on account deletion; immutable evidence removed by cleanup after 30 days | **Implemented, production disabled** |
| `operational_security` | Existing Phase 19 policy | Operational/security telemetry and audit | Existing authorized projections only | Existing Phase 16/19 lifecycle | Existing authority; deployed policy remains external |
| `quota_period` | Existing quota period plus current cleanup policy | `usage_quotas` | Existing `/api/usage`/account behavior | Existing Phase 16 lifecycle | Existing authority |
| `usage_reconciliation` | Contractual reconciliation period, to be approved | Billable usage/reversals | User/org usage projection | Restricted retention or anonymization after deletion; no product serving | **Blocked** |
| `billing_legal` | Jurisdiction/provider-specific, to be approved | Verified receipts and normalized billing evidence | Customer-facing normalized records, not secrets/raw payloads | Narrow restricted legal retention; legal hold explicit/audited | **Blocked** |
| `notification_user` | User-visible period, to be approved | In-app notifications and delivery state | User-visible/exported as approved | Delete after expiry/account lifecycle unless required evidence applies | **Blocked** |
| `support_case` | Request-type/SLA-specific, to be approved | Support, feedback, abuse, privacy requests | Requester-visible status/data as approved | Delete/anonymize after closure/retention unless legal hold applies | **Blocked** |

No later migration may hard-code these candidate periods as approved policy.
Configuration defaults, cleanup behavior, policy copy, and migration downgrade
must be reviewed together.

---

## 4. Consent and actor matrix

| Actor/context | Optional product analytics default | Decision authority | Required behavior |
| --- | --- | --- | --- |
| Anonymous public demo | Off | No decision mechanism approved | Emit no optional analytics event and create no stable analytics identifier |
| Authenticated user | Off until explicit opt-in | The individual user | Check the current exact policy decision at every emission; record immutable decision and current projection atomically |
| User acting in organization | Off pending individual opt-in | The individual user, not organization admin | Record only the approved `organization_context` class; never expose organization ID/name |
| Platform administrator using product | Same as authenticated user | The individual administrator | Admin role does not imply analytics consent; security/admin audit remains separate |
| Worker/service completing user job | No independent consent | Server evaluates the owning user's current decision at the approved event point | Never treat worker identity as analytics subject; no event after deletion or authorization revocation |
| Organization service account | Not implemented | Not applicable | No Phase 20A or 20B service-account analytics |
| Security/audit/operations processing | Not controlled by optional analytics preference | Existing security/operational authority | Stay in existing domain and retention; never copy raw data into analytics |
| Billing/usage processing | Not controlled by optional analytics preference | Verified contractual/server-owned state | Stay in billing/usage domain; optional commercial analytics needs a separate approved event |

Phase 20B decisions are explicit opt-in, deny/grant/withdraw evidence retained
for account life plus 30 days, immediate hard deletion of optional events on
withdrawal, no anonymous analytics, and re-consent after a material policy
version change. Qualified review of jurisdictions and production-facing copy
remains open; future purposes and processors require new decisions.

---

## 5. Candidate event registry

Only four entries are approved and implemented for Phase 20B. Every other
candidate remains excluded or blocked.

| Event | Domain decision | Candidate purpose | Server-owned trigger | Allowed dimensions | Retention | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `account_created` | Keep as identity/audit; no analytics duplicate initially | None | Existing identity synchronization | None | Existing audit | Excluded from initial analytics |
| `email_verified` | Security/identity only | None | Existing verified identity path | None | Existing audit | Excluded |
| `login_succeeded` | Security/identity only | None | Existing authentication/session path | None | Existing security | Excluded |
| `analysis_started` | Optional analytics candidate; never usage/billing evidence | `product_improvement` | Accepted server analysis execution | `actor_class`, `execution_mode` | `analytics_short` | **Blocked** |
| `analysis_completed` | Optional analytics; later billable unit is separate | `product_improvement` | Durable/synchronous report commit succeeds | `actor_class`, `execution_mode`, `result_class` | 30 days | **Implemented, production disabled** |
| `analysis_failed` | Optional analytics; operational failure remains separate | `product_improvement` | Server terminal durable failure classification | `actor_class`, `execution_mode`, `failure_class` | 30 days | **Implemented, production disabled** |
| `report_opened` | Optional analytics candidate | `product_improvement` | Authorized server/BFF report read, deduplicated per approved window | `actor_class`, `report_age_class` | `analytics_short` | **Blocked** |
| `thesis_saved` | Optional analytics | `product_improvement` | Successful authorized save commit | `actor_class`, `visibility_class` | 30 days | **Implemented, production disabled** |
| `watchlist_created` | Optional analytics | `product_improvement` | Successful authorized watchlist commit | `actor_class`, `visibility_class` | 30 days | **Implemented, production disabled** |
| `alert_triggered` | Operational/notification source; optional aggregate analytics deferred | None initially | Existing alert commit | None in analytics | Existing alert retention | Excluded initially |
| `organization_created` | Audit first; optional adoption event | `product_improvement` | Successful organization commit | `actor_class` only | `analytics_standard` | **Blocked** |
| `member_invited` | Organization audit first; optional adoption event deferred to 20H | `product_improvement` | Successful invitation commit | `actor_class`, `invitation_role_class` | `analytics_standard` | **Blocked** |
| `job_cancelled` | Durable-job operational/audit only | None | Existing terminal transition | None | Existing job/audit | Excluded |
| `quota_exceeded` | Quota/operations first; optional product-friction event | `product_improvement` | Server quota denial | `actor_class`, `quota_action` | `analytics_short` | **Blocked** |
| `subscription_started` | Billing evidence first; optional commercial event only after 20G | `commercial_funnel` | Reconciled normalized subscription transition | `commercial_stage` only | `analytics_standard` | **Blocked** |
| `subscription_changed` | Billing evidence first; optional commercial event only after 20G | `commercial_funnel` | Reconciled normalized subscription transition | `commercial_stage` only | `analytics_standard` | **Blocked** |
| `schedule_created` | Optional analytics candidate after 20C | `product_improvement` | Successful authorized schedule commit | `actor_class`, `cadence_class` | `analytics_standard` | **Blocked** |
| `notification_preference_changed` | Preference evidence first; no analytics initially | None | Successful preference decision | None | `preference_evidence` | Excluded initially |

`analysis_completed` appearing in both analytics and future usage does not make
the analytics record authoritative. The usage event has a separate unit,
source lineage, idempotency key, quantity, reversal, retention, and access
policy.

---

## 6. Metadata allowlist

Candidate fields are low-cardinality enumerations. They must be declared per
event and rejected when undeclared.

| Field | Candidate values/bounds | Prohibited interpretation |
| --- | --- | --- |
| `actor_class` | `anonymous`, `authenticated`, `organization_context`; maximum 32 characters | No user, session, organization, email, role, or provider identifier |
| `execution_mode` | `synchronous`, `durable`; maximum 16 | No worker/job/provider/model ID |
| `result_class` | `report_created`, `fallback_created`; maximum 32 | No report ID, title, rating, protocol, source, or strategy |
| `failure_class` | Code-owned safe enum such as `validation`, `quota`, `dependency`, `internal`; maximum 32 | No exception, status body, URL, provider message, or user input |
| `report_age_class` | Code-owned buckets such as `same_day`, `recent`, `older`; maximum 16 | No timestamp precise enough to fingerprint a user |
| `visibility_class` | `private`, `organization`; maximum 16 | No organization ID/name or public/private resource ID |
| `invitation_role_class` | `admin`, `member`, `viewer`; maximum 16 | No invitee email/token or membership ID |
| `quota_action` | Existing bounded action registry; maximum 64 | No quota subject ID, plan claim, counter row ID, or client value |
| `commercial_stage` | Code-owned normalized stage; maximum 32 | No product/price/customer/subscription/invoice/payment ID |
| `cadence_class` | Code-owned coarse bucket; maximum 32 | No exact schedule ID, timezone, thesis, watchlist, or target |

Global denylist:

- raw/free-form metadata;
- strategy, thesis, prompt, report, source, citation, support, notification, or
  document content;
- email, IP, URL, referrer, user agent, cookie, token, auth subject, anonymous
  session, device fingerprint, destination, storage key, signed URL, or
  provider payload;
- user, organization, membership, report, job, source, document, chunk,
  artifact, watchlist, schedule, notification, provider customer, subscription,
  invoice, or payment identifiers;
- client-provided plan, entitlement, quantity, billing status, or event name.

---

## 7. Data flow and lifecycle

```text
Approved server action
  -> exact candidate event definition
  -> current purpose/policy decision
  -> server-derived actor class and scope
  -> allowlisted metadata builder
  -> bounded event with expiry
  -> account export projection
  -> withdrawal/deletion/retention hook
  -> dry-run cleanup with recovery guard
```

Denied path:

```text
unapproved purpose
or no applicable decision
or anonymous analytics disabled
or undeclared field/value
or deleted/inactive actor
  -> no analytics row
  -> no retry with broader data
  -> no effect on audit, operational telemetry, quota, usage, or billing
```

The emitter must fail closed without failing the user’s primary product action
unless a later approved policy explicitly requires otherwise. An analytics
outage cannot weaken security/audit or become a reason to duplicate events
without idempotency.

---

## 8. Approval record

The project-owner decision is
[`decisions/phase_20b_analytics_approval.md`](decisions/phase_20b_analytics_approval.md).

| Review | Required decision | Status |
| --- | --- | --- |
| Product | Initial event subset, purpose, allowed dimensions, usefulness, and owner | **Approved for 20B implementation/private validation** |
| Privacy/legal | Applicable jurisdictions, production notice/copy, consent and retention | **Production activation blocked pending qualified review** |
| Security | Identifier strategy, schema enforcement, access and failure behavior | **Approved at project level for 20B implementation/private validation** |
| Engineering | Trigger semantics, idempotency, lifecycle integration, storage/index limits | **Approved and implemented for 20B** |
| Finance/commercial | `commercial_funnel` purpose and separation from billing/usage | **Not part of 20B; remains blocked** |

Anonymous analytics remains disabled. The authenticated first-party path is
eligible only for synthetic/private validation and remains disabled by default;
production activation is not authorized.
