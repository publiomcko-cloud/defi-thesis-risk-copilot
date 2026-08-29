# Phase 20 Migration and Data-Model Review

Status: **Migrations `0023`–`0026`, `0028`, and Phase 20I `0029` implemented; `0027` remains reserved/deferred for billing**

Review dates: 2026-07-30 (proposal), 2026-07-31 (Phase 20B implementation),
2026-08-28 (Phase 20I-1 implementation, 20I-2 browser/status checkpoint, and
20I-3 final query-boundary validation)

Observed migration head:

```text
20260828_0029
```

Revisions `0023`–`0026` and `0028` are implemented under their respective
scoped approvals. `0027` remains intentionally reserved/deferred for billing.
`20260828_0029_add_customer_requests.py` follows `20260824_0028` under
[`decisions/phase_20i_support_privacy_status_approval.md`](decisions/phase_20i_support_privacy_status_approval.md).

---

## 1. Existing authorities and schema

### Identity and consent

Current `consent_records`:

```text
id
user_id -> users.id ON DELETE RESTRICT
document_type
document_version
accepted_at
withdrawn_at
metadata_json
```

Current API behavior:

- accepts only `terms` or `privacy`;
- derives the document version from server configuration;
- records signup/API acceptance and a bounded audit event;
- lists and exports consent records;
- exposes no consent-withdrawal route;
- has no granular analytics purpose, decision type, policy version separate
  from document version, prior-decision link, or idempotency key.

Decision:

- retain this table and service as terms/privacy acceptance authority;
- do not add product analytics fields to it unless a later migration review
  proves the semantics are genuinely the same;
- proposed granular analytics preferences use a separate decision ledger
  because they are revocable, purpose-specific product choices, not acceptance
  of terms/privacy documents;
- the new ledger integrates with existing export/deletion/cleanup, and does not
  become a second account lifecycle service.

### Account export and deletion

Current authority:

- `GET /api/account/export` builds `AccountExportResponse`;
- response format is currently `phase17.account_export.v2`;
- it includes profile, memberships, theses, reports, watchlists, alerts, jobs,
  events, artifacts, terms/privacy consents, user-visible audits, and private
  knowledge metadata;
- it excludes private document content, embeddings, storage keys, signed URLs,
  secrets, and internal audit metadata;
- `DELETE /api/account` requires exact confirmation, blocks deletion by a final
  active organization owner, disables/anonymizes the application user,
  tombstones private knowledge, disposes jobs, and returns
  `pending_provider_deletion`;
- `scripts.cleanup_expired_data` has a dry run, optional Phase 19 recovery
  evidence guard, and later identifier/credential/resource cleanup.

Gaps:

- the account export is a direct route implementation rather than a registered
  projection framework;
- no Phase 20 domain projection/hook exists;
- provider identity deletion remains an external job;
- existing cleanup retains the user row and terms/privacy consent relationship;
- no general legal-hold registry exists;
- exact consent, analytics, usage, billing, notification, and support retention
  policy is not approved.

Later slices may introduce a bounded lifecycle-hook/projection registry, but
the public account endpoints and orchestration remain authoritative.

### Organization lifecycle

Current authority:

- server-derived organization membership and role checks;
- final active-owner protection;
- membership downgrade/removal authorization revocation for active jobs;
- organization soft deletion, knowledge tombstone, durable-job disposal, and
  audit;
- organization export endpoint, invitation lifecycle, and non-billable seat
  projection;
- no billing contact, commercial profile, pricing, payment, subscription, or
  external invitation-email authority.

Decision:

- 20H uses the existing organization service and authorization; it does not
  create a second organization or membership authority;
- the server-owned organization seat plan is non-billable, and plan/seat checks
  are separate from active membership and final-owner checks.

### Quota and plan state

Current authority:

- `users.plan` is a database-owned string;
- server settings resolve free/anonymous/admin quota limits;
- `usage_quotas` atomically records subject, action, period, plan snapshot,
  used, and limit;
- resource-count limits use durable lock rows;
- Phase 19 rate-limit buckets are separate;
- Phase 17 capacity/cost reservations are separate;
- no billable usage ledger, immutable plan version, entitlement assignment, or
  billing subscription state exists.

Decision:

- 20F introduces new immutable plan/usage authorities in shadow mode;
- existing plan/quota behavior remains the rollback source until parity and
  approval;
- no analytics event becomes a quota, usage, entitlement, or billing record.

---

## 2. Proposed `0023` — privacy decisions and product analytics

Migration `20260731_0023` now implements this reviewed Phase 20B model.

### `privacy_preference_decisions`

Purpose: immutable evidence for granular optional processing decisions not
represented by terms/privacy document acceptance.

Candidate columns:

| Column | Candidate type/bound | Notes |
| --- | --- | --- |
| `id` | `String(64)` | Prefix `ppd_` |
| `user_id` | `String(64)` FK `users.id` `RESTRICT` | Explicit lifecycle cleanup; no organization admin consent |
| `purpose` | `String(64)` | Code-owned purpose registry |
| `decision` | `String(16)` | `grant`, `deny`, or `withdraw` |
| `policy_version` | `String(32)` | Server-owned policy version |
| `previous_decision_id` | nullable self FK `RESTRICT` | Immutable decision chain |
| `idempotency_key` | `String(128)` | Server-normalized; unique per user/purpose |
| `source` | `String(32)` | Code-owned `account_ui`, `signup`, or approved migration source |
| `occurred_at` | timezone datetime | Effective user decision time |
| `created_at` | timezone datetime | Database receipt time |

Candidate constraints/indexes:

- check decision enum;
- unique `(user_id, purpose, idempotency_key)`;
- index `(user_id, purpose, occurred_at)`;
- no update/delete through product API;
- no free-form metadata JSON;
- a withdrawal references the prior current grant where available;
- one current projection winner under PostgreSQL serialized update.

Open review:

- whether explicit `deny` must be retained;
- whether `previous_decision_id` is required for all transitions;
- whether consent evidence has a legally required post-deletion period;
- whether a legal hold table is needed before any retained evidence.

### `privacy_preferences`

Purpose: current projection for efficient runtime decision checks. It is not
historical evidence.

Candidate columns:

| Column | Candidate type/bound | Notes |
| --- | --- | --- |
| `id` | `String(64)` | Prefix `ppr_` |
| `user_id` | `String(64)` FK `users.id` `RESTRICT` | Server-derived |
| `purpose` | `String(64)` | Code-owned registry |
| `enabled` | boolean | Current projection |
| `policy_version` | `String(32)` | Must match decision |
| `latest_decision_id` | FK decisions `RESTRICT` | Projection lineage |
| `updated_at` | timezone datetime | Concurrency/order |

Candidate constraints/indexes:

- unique `(user_id, purpose)`;
- projection and decision written in one transaction;
- row lock/upsert for concurrent first decision;
- unknown/missing projection means disabled;
- projection may be rebuilt from decisions.

### `product_analytics_events`

Purpose: bounded optional product analytics after approved purpose/decision.

Candidate columns:

| Column | Candidate type/bound | Notes |
| --- | --- | --- |
| `id` | `String(64)` | Prefix `pae_` |
| `event_name` | `String(64)` | Exact code-owned candidate registry |
| `schema_version` | integer | Positive, starts at 1 |
| `purpose` | `String(64)` | Approved purpose |
| `owner_user_id` | nullable FK `users.id` `RESTRICT` | Initial 20B authenticated path; explicit cleanup |
| `organization_id` | nullable FK `organizations.id` `RESTRICT` | Only when approved; never authorizes access |
| `actor_class` | `String(32)` | Low-cardinality, no identifier |
| `dimensions_json` | bounded JSON | Exact per-event typed allowlist; no arbitrary metadata |
| `event_key` | `String(128)` | Server-owned idempotency key |
| `policy_version` | `String(32)` | Decision snapshot |
| `decision_id` | nullable FK decisions `RESTRICT` | Evidence lineage for consent-based events |
| `occurred_at` | timezone datetime | Approved server trigger |
| `received_at` | timezone datetime | Database receipt |
| `expires_at` | timezone datetime | Retention cleanup |
| `anonymized_at` | nullable timezone datetime | Only if approved irreversible anonymization exists |
| `deleted_at` | nullable timezone datetime | Tombstone before hard cleanup if required |

Candidate constraints/indexes:

- unique `event_key`;
- indexes `(event_name, occurred_at)`, `(owner_user_id, occurred_at)`,
  `(organization_id, occurred_at)`, and `expires_at`;
- one owner scope; organization context never replaces user ownership;
- dimensions serialized and size-limited before persistence;
- no anonymous owner/identifier in initial 20B;
- payload immutable; only lifecycle state may change;
- optional-event cleanup is idempotent and recovery guarded;
- normal product APIs cannot query cross-user event rows.

Anonymous analytics requires a separate approved design for a short-lived,
purpose-specific pseudonymous subject and versioned pepper. It is deliberately
absent from the initial schema.

Implementation resolution:

- `owner_user_id` and `decision_id` are non-null because the approved slice is
  authenticated and explicit-opt-in only;
- no `organization_id` is stored; organization context is a bounded actor
  class and individual consent remains authoritative;
- no `anonymized_at` or `deleted_at` event state is stored because withdrawal,
  account deletion, and expiry use idempotent hard deletion for optional event
  rows;
- immutable decisions remain until account life plus 30 days, then the shared
  cleanup authority removes them.

### `0023` lifecycle

```text
user decision
  -> immutable decision
  -> current projection
  -> approved event
  -> account export projection
  -> withdrawal stops future events
  -> account deletion/retention hook
  -> dry-run cleanup
```

The migration must not:

- reinterpret existing terms/privacy acceptance;
- backfill analytics consent;
- backfill analytics events from audit/log/quota/history;
- enable collection;
- introduce an external processor or browser SDK;
- add an anonymous stable identifier.

---

## 3. Proposed `0024` — monitoring schedules and runs

Candidate tables:

- `monitoring_schedules`;
- `monitoring_schedule_runs`.

Key fields:

- explicit owner user and optional organization scope;
- target type/ID resolved through existing resource policies;
- cadence and IANA timezone;
- next/last occurrence;
- missed-run policy;
- active/paused/deleted state;
- source Phase 17 job/result;
- quota/entitlement snapshot reference where approved;
- unique `(schedule_id, scheduled_for)`;
- due/status and tenant indexes.

Lifecycle:

- create/update/delete uses existing actor/organization authority;
- dispatch and execution revalidate membership/target;
- account/organization deletion pauses/cancels and disposes jobs through
  existing lifecycle;
- no browser/web-process timer;
- rollback disables dispatcher and preserves inspectable runs.

---

## 4. Proposed `0025` — notification domain

Candidate tables:

- `notification_preferences`;
- `notification_destinations`;
- `notifications`;
- `notification_deliveries`.

Key constraints:

- preference unique by server-derived subject/category/channel;
- intent unique by code-owned idempotency key;
- destination verification/revocation state;
- no plaintext signing secret/provider credential;
- delivery status/attempt/safe error/provider reference only;
- owner/organization authorization separate from preference and entitlement;
- expiry indexes and existing lifecycle hooks.

Lifecycle:

- account/organization deletion revokes destinations and cancels deliveries;
- membership removal follows Phase 17 authorization revocation;
- export includes safe preference/inbox/destination-state metadata;
- external delivery evidence retention requires approval;
- rollback disables intent/external submission and retains in-app fallback.

---

## 5. Proposed `0026` — plans, entitlements, and usage

Implemented Phase 20F correction: `0026` seeds the immutable `free-v1`
catalog and PostgreSQL applies an exclusion constraint preventing overlapping
effective user assignments. Resolver reads do not initialize catalog or
assignment rows; missing, partial, invalid, or ambiguous state falls back to
the existing legacy authority in shadow mode.

Candidate tables:

- `plan_versions`;
- `plan_entitlements`;
- `entitlement_assignments`;
- `billable_usage_events`.

Key constraints:

- activated plan/entitlement versions immutable;
- version/effective date uniqueness;
- assignment subject/effective range and source;
- unique `(unit_key, idempotency_key)` usage;
- source type/ID, quantity, period, reversal, and reconciliation;
- no analytics dimensions or private input;
- unknown plan fails to reviewed fallback;
- existing `users.plan` and quota settings remain rollback authority during
  shadow comparison.

Do not make billable usage a foreign-key dependency of `usage_quotas`; the
ledgers have different semantics.

---

## 6. Reserved `0027` — deferred billing sandbox state

Candidate tables:

- `billing_customers`;
- `billing_subscriptions`;
- `billing_webhook_receipts`;
- optional `billing_entitlement_changes`.

Key constraints:

- opaque bounded provider IDs;
- unique provider/event receipt;
- payload hash and normalized allowlist, not full payload;
- persisted verified receipt before business-state application;
- normalized state version/reconciliation lineage;
- no card/payment details;
- no entitlement from arrival order/timestamp alone;
- authorized short-lived portal links are not stored durably;
- sandbox/production mode separation.

`0027` is intentionally reserved/deferred for billing and has not been
fabricated. The portfolio profile has no billing implementation.

---

## 7. Implemented `0028` — organization invitations and seat authority

Migration `20260824_0028` directly follows `20260821_0026`. It adds:

- `organization_invitations`;
- organization subject support in `entitlement_assignments`;
- immutable `portfolio-org-v1` / `limit.organization.seats.count = 5` seed.

Key constraints:

- hashed one-time invitation token;
- expiry/status/role/inviter/destination binding;
- atomic active-plus-reserved seat checks;
- existing organization/membership/final-owner authority unchanged;
- entitlement assignment linkage;
- audit and organization export integration.

Plaintext is returned only to the immediate create/resend demo caller; hashes
are never exposed. Browser links put the plaintext token in a URL fragment so
it is not sent in HTTP navigation URLs. No support impersonation, plan
assignment through invitation input, external email delivery, pricing, payment,
subscription, or commercial profile is implemented.

Phase 20H is COMPLETE for the portfolio profile and merged as
`54329c6911fa1fada2160cc98ac0a57a3aaa5acc`; this is implementation evidence,
not production activation or external-delivery evidence.

---

## 8. Implemented `0029` — customer and privacy requests

Implemented table:

- `customer_requests`.

Key fields:

- exact code-owned request type: `support`, `feedback`, `abuse_report`,
  `privacy_access_export`, or `privacy_deletion`;
- `owner_user_id` with `RESTRICT`, plus optional server-authorized
  `organization_id` with `SET NULL`;
- code-owned workflow and verification state;
- bounded subject/description;
- closed timestamps and optional bounded resolution code;
- safe audit lineage only.

Authority boundary:

- the row tracks intake, server-derived verification, and bounded workflow state;
- existing account/organization export and deletion services perform the
  actual operation;
- no attachment in the initial schema;
- no automatic LLM, analytics, or log forwarding;
- no attachments, assignees, provider IDs, arbitrary metadata, legal hold, or
  invented retention period. `0027` remains reserved/deferred for billing;
  `0029` is implemented for Phase 20I-1, merged as
  `8fb2fd6e998e740cba9bd29078597b5a9c1cbfa3`. Accepted Phase 20I-2 is
  `1465601712c29988360d7017cd9a6e7f1a5d007f`. Phase 20I-2/3 is browser/status
  and BFF-boundary work only on `agent/v1-phase-20i-2-request-status-ui`; it
  creates no new migration or customer-request authority. Both checkpoints
  remain under
  `docs/decisions/phase_20i_support_privacy_status_approval.md`. Phase 20G
  remains **DEFERRED**.

Browser boundary for 20I-2:

- `/support` uses the existing owner-scoped API only through the curated
  same-origin BFF customer-request routes; it does not author workflow,
  verification, ownership, provider, or billing fields;
- the collection, detail, and close BFF paths reject non-empty query strings
  before upstream forwarding, so this unused channel cannot carry or log
  request content;
- subject and description remain volatile unsaved browser state and are not
  written to URLs, browser storage, cookies, titles, metadata, analytics,
  notifications, logs, LLM/RAG, or external services;
- `/status` consumes only safe health success/failure and presents coarse
  availability, with no internal database/provider/tenant or customer detail;
- no external helpdesk/status provider, subscriber collection, SLA/uptime
  assertion, production support operation, commercial claim, or automatic
  LLM/RAG processing is implemented. Phase 20I completes only after exact-head
  hosted CI is green; Phase 20G remains **DEFERRED**.

---

## 9. Ownership and deletion review

| Domain | Owner/scope | FK posture | Account deletion | Organization deletion | Export authority |
| --- | --- | --- | --- | --- | --- |
| Privacy decisions | User | `RESTRICT` pending explicit lifecycle | Delete/anonymize or restrict only under approved evidence policy | Not organization-controlled | Existing account export |
| Analytics events | User; optional org context | `RESTRICT` to force explicit cleanup | Delete or irreversibly anonymize under approved policy | Remove/delete org-context rows under approved policy | Existing account export; future org export |
| Schedules/runs | User or organization | Explicit owner/org FKs | Pause/cancel/tombstone; dispose jobs | Pause/cancel/tombstone; dispose jobs | Existing account; future org export |
| Notifications/destinations | User or organization | Explicit owner/org FKs | Revoke/cancel/delete by retention | Revoke/cancel/delete by retention | Existing account; future org export |
| Plan assignments | User or organization | Explicit subject representation | End assignment; retain required audit | End assignment; retain required audit | Existing account; future org export |
| Usage | User or organization | Explicit subject representation with restricted evidence state | Delete/anonymize or legally restrict | Same | Existing account; future org export |
| Billing | User/organization customer mapping | Explicit subject plus provider IDs | Cancel/end; retain only required evidence | Same; billing owner rules | Normalized account/org commercial export |
| Customer/privacy request | User owner; optional organization context | `owner_user_id RESTRICT`; `organization_id SET NULL` plus explicit lifecycle cleanup | Existing authorized account deletion explicitly removes owned private rows | Clear organization context while preserving owner-only row | Existing account export for owner only; no organization export |

`CASCADE` must not be chosen merely for convenience. `SET NULL` must not create
unscoped rows accessible to normal product queries. Every FK and cleanup order
requires PostgreSQL migration tests.

---

## 10. Migration and rollback gates

Before implementing each revision:

1. reconfirm Alembic head and branch history;
2. obtain applicable human approvals;
3. document row counts, lock duration, backfill, indexes, and failure mode;
4. add models and reversible migration without enabling runtime flags;
5. run SQLite compatibility where supported;
6. run PostgreSQL upgrade/downgrade/upgrade from a production-like prior
   schema;
7. test ownership, tenant isolation, concurrency, export, deletion, retention,
   cleanup dry run, and recovery guard;
8. prove no secret/private payload exposure;
9. deploy schema disabled;
10. activate only after slice-specific shadow/sandbox evidence.

Rollback rules:

- disable writers/dispatch/application before downgrade;
- do not downgrade through immutable consent, usage, billing, audit, or legal
  evidence without an approved data disposition;
- preserve existing quotas, jobs, JSON RAG, and public demo;
- keep real Vast rentals disabled;
- never reset or delete production data to make a migration pass.

---

## 11. Review blockers

No model is approved for implementation.

| Review | Required outcome | Status |
| --- | --- | --- |
| Architecture | Table boundaries, lifecycle registry approach, FK/delete semantics, schema split | **Blocked** |
| Privacy/legal | Purpose/consent evidence, retention, withdrawal, export/deletion, legal hold | **Blocked** |
| Security | Tenant query patterns, identifiers, callback/destination/billing secrets, admin roles | **Blocked** |
| Product | Taxonomy, preferences, schedules, notifications, entitlement semantics | **Blocked** |
| Finance/commercial | Usage units, billing evidence, plans, seats, tax/refund/trial/grace | **Blocked** |
| Operations | Cleanup/recovery, provider evidence, monitoring, rollback ownership | **Blocked** |

The next schema change is ineligible until its applicable review is recorded.
