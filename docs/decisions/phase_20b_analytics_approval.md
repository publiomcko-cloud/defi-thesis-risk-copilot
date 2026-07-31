# Phase 20B Analytics Approval Decision

Status: **Approved for implementation and synthetic/private validation; production activation remains blocked pending qualified privacy/legal review**

Recorded: **2026-07-31**

Decision owner: **Project owner**

This decision closes the product, engineering, and project-level security design gate for implementing Phase 20B. It does not certify legal compliance and does not authorize production analytics activation.

## 1. Approval scope

Phase 20B is approved for:

- implementation;
- automated testing;
- migration validation;
- synthetic-user validation;
- private test-environment validation.

Production analytics activation remains blocked until qualified privacy/legal review confirms the applicable jurisdictions, privacy notice, consent wording, and retention policy.

The feature must remain disabled by default:

```text
PRODUCT_ANALYTICS_ENABLED=false
```

## 2. Approved purpose

The only approved analytics purpose is:

```text
product_improvement
```

Analytics must remain separate from:

- operational telemetry;
- security and audit evidence;
- product quota accounting;
- billable usage;
- billing evidence;
- notification-delivery evidence.

## 3. Approved users and actor scope

Optional analytics is limited to authenticated individual users.

Anonymous analytics is disabled. No stable anonymous identifier, device fingerprint, or browser analytics identity may be created.

When a user acts in an organization context, analytics consent remains the individual user's decision. Organization administrators cannot consent on behalf of members.

Workers and services have no independent analytics identity. At an approved server-owned event point, they evaluate the current decision of the owning user.

## 4. Consent policy

Explicit opt-in is required. The default is disabled.

No analytics event may be emitted unless the server confirms a current affirmative decision for the exact purpose and consent-policy version.

Consent evidence must be append-only and record:

- server-derived user ownership;
- purpose;
- decision: `grant`, `deny`, or `withdraw`;
- consent-policy version;
- decision timestamp;
- server-generated idempotency key;
- previous-decision linkage where applicable.

A mutable preference row may be maintained as a current projection, but it is not the historical authority.

Terms or privacy-document acceptance must not be reinterpreted as optional analytics consent.

## 5. Re-consent rules

A new affirmative decision is required when any of the following materially changes:

- analytics purpose;
- approved event set;
- approved metadata;
- retention period;
- external processor;
- identifier strategy;
- privacy notice or consent wording;
- consent-policy version.

Collection must stop for the affected purpose until a valid decision for the new version exists.

## 6. Storage and identifier policy

Use first-party PostgreSQL only.

Do not integrate an external analytics provider or browser analytics SDK in Phase 20B.

Event rows may contain a server-owned user foreign key when required for consent enforcement, tenant isolation, export, and deletion. That ownership key:

- is not an analytics dimension;
- is never accepted from the client;
- is not exposed in aggregate analytics output;
- is not copied to an external processor.

Server-only pseudonymization secrets, if later needed, must remain outside event payloads and browser configuration.

## 7. Initial approved events

Only these events are approved for the initial Phase 20B implementation:

- `analysis_completed`;
- `analysis_failed`;
- `thesis_saved`;
- `watchlist_created`.

Exact server-owned triggers:

- `analysis_completed`: only after the report transaction commits successfully;
- `analysis_failed`: only after a terminal failure is recorded with a safe code-owned failure class;
- `thesis_saved`: only after the authorized thesis-save transaction commits;
- `watchlist_created`: only after the authorized watchlist-create transaction commits.

Each source action may produce at most one analytics event. Use a server-generated idempotency key or unique source boundary to prevent duplicates during retries and concurrent execution.

Events are optional analytics records only. They are not authoritative evidence of quota use, billing, durable-job completion, or security/audit activity.

## 8. Approved metadata

Only these code-owned, bounded fields are allowed:

- `actor_class`;
- `execution_mode`;
- `result_class`;
- `failure_class`;
- `visibility_class`.

Each event must have its own exact metadata allowlist. Undeclared fields or values must be rejected rather than stored.

No free-form metadata is allowed.

## 9. Sensitive-data prohibition

Never store the following in analytics dimensions or payloads:

- strategy or thesis content;
- prompts;
- reports;
- sources or citations;
- document content;
- email addresses;
- IP addresses;
- URLs or referrers;
- user-agent strings;
- cookies or tokens;
- user, organization, membership, report, job, document, provider, payment, or storage identifiers;
- provider payloads;
- client-provided plan, entitlement, event name, or quantity.

Required ownership foreign keys remain server-owned relational controls, not analytics metadata.

## 10. Retention

Analytics events have a maximum retention of 30 days.

Grant, deny, and withdrawal decision evidence is retained for the account lifetime and for 30 days after account deletion in the initial implementation, unless qualified legal review later requires a different narrow period.

Retention cleanup must be:

- automatic;
- idempotent;
- testable in dry-run mode;
- integrated with existing recovery safeguards;
- unable to delete independently required audit or security records.

No migration or configuration may silently increase these periods.

## 11. Withdrawal

Withdrawal stops future optional collection immediately.

Existing optional analytics events must be queued for deletion from active analytics storage and removed within 24 hours.

Withdrawal must not suppress operational telemetry, security auditing, quota records, billing evidence, or other independently authorized records.

Grant, deny, and withdrawal evidence follows the approved decision-evidence retention policy.

## 12. Export

The existing Phase 16 account-export authority remains responsible for export.

The export must include:

- current analytics preferences;
- immutable consent decisions;
- safe analytics event records or an understandable safe projection;
- purpose and policy versions;
- event and expiry timestamps.

It must not expose internal pseudonymization secrets, security controls, or prohibited identifiers.

Phase 20B must register an export projection rather than create a competing export service.

## 13. Account deletion

The existing Phase 16 account-deletion authority remains responsible for deletion.

Phase 20B must register lifecycle hooks with that service rather than create a second deletion mechanism.

Account deletion must:

- disable future analytics immediately;
- delete active optional analytics events;
- process consent evidence according to its approved retention period;
- preserve only independently required audit, security, billing, or legal records.

## 14. Access control

Users may access their own analytics information through the existing account-export mechanism and any later approved account privacy interface.

Organization members and administrators may not inspect another user's optional analytics records.

Operator access must be restricted, audited, and limited to an approved operational purpose. Analytics records must not become a support impersonation mechanism.

## 15. Failure behavior

Analytics is non-critical to the primary product action.

An analytics storage, schema, or emitter failure must:

- fail closed by creating no analytics event;
- not fail or roll back the user's successful product action;
- generate only redacted operational telemetry;
- not retry with broader metadata;
- preserve idempotency during a safe retry.

Analytics failure must not weaken security/audit behavior or cause event duplication.

## 16. Sampling

No sampling is used in the initial implementation.

Any future sampling behavior requires a versioned policy update and review.

## 17. Required Phase 20B implementation evidence

This approval permits implementation; it does not constitute completion. Phase 20B must still produce:

- migration `0023` or its reviewed successor;
- current preference projection;
- append-only decision evidence;
- append-only bounded analytics events;
- code-owned event and metadata registry;
- server-side consent and purpose gate;
- preference APIs and accessible UI;
- Phase 16 export and deletion integration;
- retention and withdrawal cleanup;
- tenant-isolation and operator-access controls;
- tests for grant, deny, withdrawal, re-consent, policy transition, concurrency, idempotency, metadata rejection, redaction, export, deletion, and retention;
- disabled-by-default rollout and rollback evidence;
- green backend, PostgreSQL, frontend, browser, security, migration, and recovery checks.

## 18. Approval boundary

The project owner approves:

- the product purpose;
- initial event set;
- technical implementation boundaries;
- first-party storage;
- project-level security restrictions;
- retention and lifecycle behavior for implementation and testing.

Qualified privacy/legal review remains required before production activation.

Therefore:

- Phase 20B implementation is eligible to begin;
- synthetic and private-environment validation is approved;
- Phase 20B is not complete until its runtime implementation and evidence pass;
- production must continue with `PRODUCT_ANALYTICS_ENABLED=false` until the production legal gate is explicitly recorded as approved.

## 19. Implementation checkpoint

The Phase 20B runtime and local evidence were implemented on 2026-07-31 under
this decision. [`../phase_20_evidence_matrix.md`](../phase_20_evidence_matrix.md)
records the migration, consent, concurrency, lifecycle, frontend and rollback
checks. This does not change the approval boundary: production analytics stays
disabled until the qualified privacy/legal gate is recorded separately.
