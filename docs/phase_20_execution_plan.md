# V1 Phase 20 Execution Plan — Product Analytics and Commercial Readiness

Status: **Planned — planning branch only; no Phase 20 runtime capability is implemented**

Branch: `agent/v1-phase-20-product-analytics-commercial-readiness`

Authority:

- [`future_phase_contracts.md`](future_phase_contracts.md), especially the
  Phase 20 contract, defines scope and completion gates;
- [`current_state.md`](current_state.md) defines the implemented/deployed
  baseline;
- [`phase_19_evidence_matrix.md`](phase_19_evidence_matrix.md) defines the
  operational evidence that remains external;
- [`architecture.md`](architecture.md), [`deployment.md`](deployment.md), and
  [`testing.md`](testing.md) define permanent trust, rollout, and validation
  boundaries.

This document defines implementation order. It does not select an analytics,
email, webhook, messaging, billing, status, support, or consent-management
provider. Provider integration is blocked until the alternatives and selection
criteria in section 5 are recorded in an approved architecture decision record
(ADR).

---

## 1. Goal

Phase 20 adds privacy-conscious product measurement, durable scheduled
monitoring, user-controlled notifications, server-owned plan enforcement,
reconcilable usage metering, billing sandbox foundations, organization
commercial workflows, customer operations, and qualified legal/commercial
readiness.

It preserves:

- the Phase 15 public-safe anonymous demo;
- Phase 16 identity, ownership, organization, consent, quota, export, deletion,
  and audit boundaries;
- Phase 17 durable jobs, scoped workers, idempotency, cancellation, recovery,
  and cost controls;
- Phase 18 server-derived tenant retrieval and JSON RAG fallback;
- Phase 19 request bounds, rate limits, redaction, security checks, incident
  runbooks, and external operational gates;
- deterministic risk scoring and non-advisory research behavior;
- `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=false` until the existing controlled
  deployment gates are evidenced;
- `VAST_DRY_RUN=true` and `VAST_REAL_RENTALS_ENABLED=false`.

Phase 20 does not add wallets, signing, custody, trading, personalized
financial advice, client-controlled plans, automatic payment activation,
support impersonation, or unreviewed marketing/legal claims.

---

## 2. Required terminology and separate ledgers

The implementation must keep four concepts separate in code, storage, API
responses, monitoring, and documentation.

| Concept | Purpose | Persistence | Enforcement/source of truth | Must not become |
| --- | --- | --- | --- | --- |
| Network rate limit | Protect API/BFF/compute from burst and sustained abuse | Phase 19 privacy-preserving rate-limit buckets | Shared limiter policy keyed by server-derived scopes | A plan entitlement, invoice quantity, or product-usage statement |
| Product quota | Bound how much of a product action may be used in a period | Existing `usage_quotas` counters, later resolved from entitlements | Atomic server-side quota service | A billable ledger or request-frequency control |
| Billable usage | Reconcile a chargeable unit exactly once | New immutable usage-meter ledger with idempotency and source lineage | Server-recorded usage events plus reconciliation | An analytics event, mutable quota counter, or client-provided quantity |
| Plan entitlement | Define feature access and hard limits for a versioned plan | New versioned plan/entitlement catalog and server-owned assignment | Entitlement resolver using active assignment and effective dates | A JWT claim, browser flag, provider payload used without verification, or editable user field |

Operational telemetry and product analytics are also separate:

- operational telemetry exists for reliability/security and follows Phase 19
  redaction and access rules;
- product analytics exists for an approved product purpose, requires the
  applicable consent/legal basis, and has its own taxonomy, retention, export,
  deletion, and processor record;
- security/audit events remain in the existing audit domain and are never
  suppressed by analytics opt-out.

---

## 3. Target architecture

```text
Browser or backend domain action
  -> authenticated/anonymous server-derived actor
  -> product event registry
  -> consent/purpose gate
  -> bounded first-party event record
  -> optional approved analytics exporter

Durable schedule
  -> scheduler tick in an operator runtime
  -> PostgreSQL due-row claim
  -> idempotent Phase 17 job
  -> watchlist/monitoring evaluation
  -> notification intent
  -> preference and entitlement gate
  -> in-app delivery or approved external delivery job

Product action
  -> entitlement resolution
  -> product quota reservation/consumption
  -> immutable billable usage event when applicable
  -> reconciliation
  -> verified billing sandbox webhook
  -> normalized subscription state
  -> server-owned entitlement assignment
```

Every user, organization, schedule, notification, usage, billing, support, and
privacy query derives tenant scope from the authenticated actor and active
membership. A client-provided resource ID, plan name, organization ID, event
quantity, destination, or provider status never establishes authorization.

---

## 4. Cross-cutting data and lifecycle decisions

### 4.1 Identifier and ownership policy

- Use the repository's bounded string IDs with domain prefixes.
- User-owned rows use explicit user foreign keys; organization rows use active
  organization and membership checks.
- Anonymous product analytics is disabled unless a documented consent/legal
  basis and a short-lived pseudonymous server identifier exist.
- External processor identifiers are opaque, bounded, server-only metadata.
- Never store access tokens, refresh tokens, cookies, webhook signing secrets,
  email-provider credentials, billing secrets, raw private strategy text,
  source content, object keys, or complete provider payloads in Phase 20 rows.

### 4.2 Versioning policy

- Event definitions are code-owned and schema-versioned.
- Consent policy versions are server-owned.
- Plans and entitlements are immutable after activation; changes create a new
  plan version with effective dates.
- Notification templates, webhook signature versions, usage-meter definitions,
  and provider adapter versions are recorded.
- Billing webhook normalization is versioned independently from provider event
  versions.

### 4.3 Deletion, export, and retention

- Account export includes understandable analytics, notification, schedule,
  entitlement, usage, subscription, support, and privacy-request metadata only.
- It excludes destination verification secrets, webhook secrets, provider raw
  payloads, internal fraud/risk controls, processor credentials, and internal
  pseudonymization keys.
- Analytics withdrawal stops future optional collection immediately.
- Account/organization deletion cancels active schedules and deliveries,
  revokes destinations, removes or anonymizes optional analytics according to
  the approved retention policy, and preserves only legally required
  billing/audit records in a restricted state.
- Retention cleanup is idempotent, has a dry run, and integrates with the Phase
  19 recovery-evidence guard before destructive operation.

### 4.4 Security policy

- Browser code receives only public configuration and safe display metadata.
- Provider credentials and signing keys are server/worker-only.
- External callbacks use exact route allowlists, measured body limits, replay
  windows, signature verification, idempotent receipt records, and generic
  errors.
- Outbound webhooks use SSRF-resistant destination validation, DNS/IP policy,
  redirect denial, bounded responses, timeouts, and per-destination rate limits.
- Email/Telegram/webhook content contains no private report/source content by
  default; links require normal authenticated authorization.
- Commercial changes and organization billing administration are audited.

---

## 5. Provider decision gates

No provider is selected by this plan. Before an adapter or SDK is added, create
an ADR under `docs/decisions/` that records alternatives, scoring, data flows,
subprocessors, secrets, sandbox behavior, failure mode, cost, exit plan, and
approval.

| Capability | Alternatives to evaluate | Required selection criteria |
| --- | --- | --- |
| Product analytics | First-party PostgreSQL event store; PostHog Cloud/self-hosted; Plausible; another reviewed processor | Consent controls, event allowlist, EU/US data location, DPA/subprocessors, deletion/export API, server-side ingestion, identifier policy, sampling, retention, cost, lock-in, outage behavior |
| Consent management | First-party preference UI/records; Cookiebot; OneTrust; another reviewed CMP | Regional rules, proof/versioning, withdrawal, accessibility, cookie blocking, subprocessor/data location, export/deletion, cost |
| Transactional email | Postmark; Resend; Amazon SES; another reviewed service | Domain authentication, deliverability, suppression/unsubscribe handling, templates, webhook verification, DPA/data location, sandbox, logs/retention, price; Supabase Auth SMTP remains a separate Phase 22 identity gate |
| Outbound webhook delivery | First-party Phase 17 worker adapter; Svix; Hookdeck or equivalent | Signing/replay protection, retries/dead letter, SSRF controls, endpoint verification, tenant isolation, observability, payload retention, cost, portability |
| Messaging | Telegram Bot API directly; a reviewed multi-channel provider; defer channel | User verification, revocation, privacy policy, bot secret handling, regional availability, abuse/rate limits, delivery evidence, cost |
| Billing | Stripe Billing; Paddle; Lemon Squeezy; another reviewed provider; remain unpaid | Processor versus merchant-of-record responsibilities, countries/currencies, tax/VAT, sandbox, webhook guarantees, subscription lifecycle, portal/refunds, DPA, fees, export and migration |
| Status page | Atlassian Statuspage; Better Stack/Better Uptime; Instatus; first-party static status | Independent availability, component model, incident API, subscriber privacy, custom domain, access control, retention, cost |
| Customer support | First-party intake; Help Scout; Zendesk; Freshdesk; another reviewed system | Privacy/DPA, email ingestion, role controls, export/deletion, audit, SLA workflows, attachments/malware, cost, exit path |

Approval requirements:

1. product and engineering approve capability/operational fit;
2. security approves data flow, secret handling, callbacks, and failure mode;
3. privacy/legal reviews DPA, subprocessors, retention, data location, consent,
   and customer terms;
4. finance/commercial reviews billing/tax/refund responsibilities where
   applicable;
5. sandbox credentials are stored only in approved server-side secret stores;
6. an adapter remains disabled until its focused tests and rollback pass.

External prerequisites and blockers:

- Phase 19 centralized telemetry, alert delivery, provider restore drills,
  production secret rotation, protected-branch enforcement, and controlled
  deployment evidence remain external gates; any Phase 20 provider activation
  that depends on one of them is blocked until that evidence exists;
- privacy/legal owners must approve purposes, consent/legal basis, retention,
  processor terms, data location, subprocessors, and user-facing copy;
- finance/commercial owners must approve usage units, plan semantics, tax,
  refund, trial, cancellation, grace, and merchant-of-record responsibilities;
- operator-owned sandbox accounts, verified domains/destinations, secret-store
  ownership, callback origins, and revocation procedures are required before
  any provider test;
- Phase 22 retains final deployed-provider validation and launch approval.

---

## 6. Ordered implementation subphases

### Phase 20A — Privacy contract, taxonomy, and decision records

| Item | Plan |
| --- | --- |
| Objective and scope | Define approved product-analytics purposes, event taxonomy, metadata allowlists, retention classes, consent behavior, usage units, entitlement vocabulary, notification categories, and provider ADR templates. Add no runtime collection or provider integration. |
| Dependencies | Merged Phase 19 foundations; existing terms/privacy consent records; privacy, legal, product, security, and finance owners identified. |
| Data model and migrations | No migration. Produce table/constraint specifications for proposed revisions `0023`–`0029`; confirm current head `20260728_0022` at implementation time. |
| Backend and frontend work | Documentation only: event registry proposal; lifecycle diagrams; endpoint inventory; destination/data-flow inventory; UI wire-level requirements for consent and preferences without implementing pages. |
| Environment/provider configuration | Define disabled defaults and secret/public naming rules. Create ADR template and provider scorecards; do not select or configure a provider. |
| Privacy and security boundaries | Classify every event field by purpose and sensitivity. Ban raw strategy/source content, tokens, cookies, provider payloads, free-form metadata, and client-supplied identity/plan fields. Define operational telemetry versus analytics boundary. |
| Tests and evidence | Documentation link check; taxonomy schema examples validate against proposed bounded metadata rules; threat-model review; privacy data-flow review; confirmation that no runtime/env/migration changed. |
| Rollout and rollback | Planning artifact only. Rollback is reverting documentation; there is no data or runtime effect. |
| Completion criteria | Approved taxonomy/purpose/retention matrix, four-concept quota/metering/entitlement distinction, provider ADR process, proposed migration sequence, named decision owners, and unresolved choices recorded. |

Gate to 20B: privacy/legal must approve the first-party event purpose,
consent requirement, export/deletion policy, and retention classes. If approval
is unavailable, Phase 20 remains `Blocked`; implementation must not guess.

### Phase 20B — Consent-aware first-party product analytics

| Item | Plan |
| --- | --- |
| Objective and scope | Implement a bounded first-party event path and preference controls without an external analytics SDK. Necessary security/audit/operations events remain separate. |
| Dependencies | 20A approval; Phase 16 user/anonymous lifecycle; Phase 19 redaction/request correlation. |
| Data model and migrations | Proposed `20260729_0023`: `privacy_preferences` current projection and `product_analytics_events` append-only rows. Fields include event name/schema/purpose, server-derived user/org or short-lived anonymous scope, bounded dimensions, consent/policy snapshot, occurred/received timestamps, expiry, and deletion/anonymization state. Add event-name/time, user/time, organization/time, and expiry indexes. Use deliberate `SET NULL` only after lifecycle review; default account deletion explicitly deletes optional events. |
| Backend and frontend work | Add code-owned event registry, server emitter, consent gate, preference APIs, account preference UI, and safe account export projection. Instrument only the approved initial taxonomy at server-owned completion points, not arbitrary browser calls. |
| Environment/provider configuration | `PRODUCT_ANALYTICS_ENABLED=false`, `PRODUCT_ANALYTICS_MODE=first_party`, server-only identifier pepper, approved taxonomy/policy versions, retention days, and bounded sampling. No external exporter or browser key. |
| Privacy and security boundaries | Default optional analytics off where consent is required; withdrawal stops future events; no raw query, strategy, source, email, IP, URL, user agent, referrer query, or identifiers in dimensions. Metadata is allowlisted per event. |
| Tests and evidence | Consent grant/withdraw/opt-out, event allowlist/schema bounds, anonymous policy, server-derived scope, tenant isolation, redaction, retention, export/deletion, concurrent duplicate prevention, and no impact on audit/operational telemetry. PostgreSQL migration cycle and browser preference tests. |
| Rollout and rollback | Deploy tables with collection disabled; enable only a synthetic/private test tenant; compare counts and retention; disable emitter for rollback while preserving rows for approved cleanup. |
| Completion criteria | Approved events are emitted exactly once at defined server points, consent/opt-out works, export/deletion works, retention is tested, and no sensitive payload leakage or external processor exists. |

### Phase 20C — Durable scheduled monitoring

| Item | Plan |
| --- | --- |
| Objective and scope | Add user/organization schedules for existing monitoring/watchlist evaluations using Phase 17 jobs. No browser timers or in-process web scheduler. |
| Dependencies | 20B server event semantics; Phase 17 worker/recovery; existing watchlists/alerts; Phase 19 queue monitoring and incident procedures. |
| Data model and migrations | Proposed `20260729_0024`: `monitoring_schedules` and `monitoring_schedule_runs`. Store owner/org scope, target type/id, normalized cadence, IANA timezone, next/last run, missed-run policy, status, limits, idempotency key, source job, result state, timestamps, and tombstone. Unique `(schedule_id, scheduled_for)` run boundary; due/status and tenant indexes. |
| Backend and frontend work | Add exact `monitoring.schedule.execute.v1` job contract and executor; operator scheduler command that claims due rows with PostgreSQL locking and bounded batch size; create/list/detail/pause/resume/delete APIs; schedule UI with timezone/cadence controls and run history. |
| Environment/provider configuration | `SCHEDULED_MONITORING_ENABLED=false`, scheduler batch/lag/horizon limits, allowed cadence floor, per-user/org active schedule limits, worker scope, and no provider credential. Select a maintained timezone/recurrence library through dependency review rather than hand-rolling DST rules. |
| Privacy and security boundaries | Scope/target derived server-side; active membership revalidated at dispatch and execution; schedule bodies contain resource IDs and bounded configuration only; deleted/disabled targets do not run; schedules cannot select arbitrary URLs/providers. |
| Tests and evidence | DST transitions, invalid timezone, next-run math, pause/resume/delete, missed-run skip/coalesce policy, concurrent scheduler one-winner, idempotent run/job creation, queue saturation, worker loss, membership removal, quota/cost denial, cancellation, retention, export/deletion, browser E2E, PostgreSQL contention. |
| Rollout and rollback | Start with dry-run due calculation; then synthetic schedules with worker; enable low cadence and low counts. Roll back by disabling dispatcher and pausing schedules; existing runs/jobs remain inspectable and recoverable. |
| Completion criteria | Due work survives process restarts, is claimed once, executes through Phase 17, handles DST/missed runs, respects ownership/quota/cost, and can be paused/deleted safely. |

### Phase 20D — Notification domain and in-app delivery

| Item | Plan |
| --- | --- |
| Objective and scope | Implement user-controlled notification categories/preferences and durable in-app notifications before any external channel. |
| Dependencies | 20B consent/purpose rules; 20C schedule runs; existing alert events; Phase 16 ownership. |
| Data model and migrations | Proposed `20260729_0025`: `notification_preferences`, `notification_destinations`, `notifications`, and `notification_deliveries`. Preferences are unique by subject/category/channel. Notification intents use an idempotency key and server-derived owner/org. Destinations have verification/revocation state; secret material is never stored plaintext. Deliveries record status, attempt, safe error code, provider/message reference, next attempt, and expiry. |
| Backend and frontend work | Add preference/destination/inbox APIs, unread/read/archive state, in-app notification creation from approved alert/schedule outcomes, inbox/preferences UI, category/severity filters, timezone/quiet hours, digest configuration, and accessible controls. |
| Environment/provider configuration | `NOTIFICATIONS_ENABLED=false`, `IN_APP_NOTIFICATIONS_ENABLED=false`, retention, digest bounds, per-user/category rate limits. No external provider configuration in 20D. |
| Privacy and security boundaries | In-app content is bounded and contains no report/source body. Organization notification visibility requires active membership. Preferences never authorize the underlying resource. Quiet hours use validated IANA timezones. |
| Tests and evidence | Preference isolation, default/off behavior, duplicate intent suppression, severity/category filtering, quiet hours, digest grouping, membership removal, read/archive state, account/org export/deletion, retention, accessibility, browser E2E, and quota/rate-limit separation. |
| Rollout and rollback | Create tables/API with notifications disabled; enable synthetic in-app intents; roll back by disabling intent creation while leaving inbox records readable until retention. |
| Completion criteria | Users control categories and in-app delivery, duplicate intents are prevented, tenant isolation and lifecycle pass, and no external destination/provider is used. |

### Phase 20E — Approved external notification delivery

| Item | Plan |
| --- | --- |
| Objective and scope | Add only channels approved by completed ADRs. Email and signed webhooks are the initial candidates; Telegram remains optional and may be deferred. |
| Dependencies | 20D; provider/security/privacy ADR approval; Phase 17 jobs; Phase 19 outbound security, monitoring, alert delivery, and secret-management gates appropriate to the selected adapter. |
| Data model and migrations | Prefer the 20D schema. Add only adapter-specific normalized metadata through an additive migration if an approved provider requires it. Never persist raw credentials or complete provider payloads. |
| Backend and frontend work | Add exact `notification.deliver.v1` job schema, per-channel executor adapter, destination verification, webhook challenge/signature version, unsubscribe/revocation, retry/dead-letter, safe delivery status UI, and admin aggregate diagnostics. |
| Environment/provider configuration | Disabled per-channel flags; provider mode `sandbox`; server/worker-only credentials; webhook signing key version; timeouts, response-size bounds, retry/backoff, daily destination/channel ceilings. No `NEXT_PUBLIC_*` secret. |
| Privacy and security boundaries | Email must use a verified address/destination. Webhook destinations require verification, HTTPS policy, SSRF/DNS-rebinding defenses, no redirects, signed timestamped payloads, replay limits, and secret rotation. External content is metadata/minimal link by default. |
| Tests and evidence | Provider fakes, signature/replay, destination verification/revocation, SSRF/private-IP/DNS-change/redirect denial, retries/dead-letter, idempotency, unsubscribe, suppression/bounce, quiet hours/digest, rate limits, secret redaction, provider outage, account/org deletion, browser status. No real send in CI. |
| Rollout and rollback | Sandbox only; synthetic verified destination; one channel at a time; monitor failures and queue. Rollback disables channel submission, cancels queued deliveries safely, revokes credentials, and leaves in-app notification available. |
| Completion criteria | Approved channel sandbox works end to end through durable jobs, security and user controls pass, provider failures are recoverable, and disabling the adapter preserves in-app behavior. |

### Phase 20F — Usage metering and versioned plan entitlements

| Item | Plan |
| --- | --- |
| Objective and scope | Introduce server-owned plan versions, hard feature entitlements, and an immutable usage ledger while preserving existing product quota behavior during migration. |
| Dependencies | 20A usage-unit definitions; Phase 16 quotas/plan field; Phase 17 job/cost reservations; analytics separation from 20B. |
| Data model and migrations | Proposed `20260729_0026`: `plan_versions`, `plan_entitlements`, `entitlement_assignments`, and `billable_usage_events`. Plans/entitlements become immutable after activation. Assignments have subject/effective dates/source. Usage events have unit, quantity, source type/id, idempotency key, period, reversal link, and reconciliation status. Add unique source/idempotency constraints and subject/unit/period indexes. |
| Backend and frontend work | Add entitlement registry/resolver, admin-safe catalog APIs, user/org current-plan and usage summary, usage recorder at server-owned completion points, reconciliation command, and account/billing settings UI that is read-only unless a verified commercial workflow exists. Keep `UserModel.plan` as compatibility fallback until shadow comparison passes. |
| Environment/provider configuration | `ENTITLEMENTS_ENABLED=false`, `USAGE_METERING_ENABLED=false`, default/fallback plan version, reconciliation bounds, and no billing provider. Existing quota environment limits remain rollback defaults. |
| Privacy and security boundaries | JWT/browser/provider claims cannot grant plan access. Quantity and unit are calculated server-side. Usage events do not contain analytics dimensions or private input. Admin exemptions remain explicit and audited. |
| Tests and evidence | Entitlement version/effective-date behavior, client-forgery denial, quota resolver parity, hard feature denial, immutable usage/idempotency/reversal, concurrent one-winner, job retry without double meter, organization scope, export/deletion/legal retention, reconciliation mismatch, PostgreSQL contention, browser summaries. |
| Rollout and rollback | Shadow-resolve entitlements against current env quota results; record usage without billing; compare; then enable selected hard checks. Roll back to existing environment quota policy and disable metering writes without changing historical ledger rows. |
| Completion criteria | Four concepts remain separate, server-owned entitlements are versioned and enforceable, billable usage is exactly-once/reconcilable, and existing quotas/public demo do not regress. |

### Phase 20G — Billing-provider sandbox foundation

| Item | Plan |
| --- | --- |
| Objective and scope | After an approved billing ADR, support sandbox customer/subscription mapping, verified webhooks, normalized lifecycle, portal links, and entitlement updates. Do not accept live payment or claim tax/legal readiness. |
| Dependencies | 20F; selected provider ADR; finance/tax/legal review; Phase 19 secret/callback/monitoring controls; provider sandbox account. |
| Data model and migrations | Proposed `20260729_0027`: `billing_customers`, `billing_subscriptions`, `billing_webhook_receipts`, and optional `billing_entitlement_changes`. Store opaque provider IDs, normalized status, plan mapping, period/trial/grace dates, payload hash, event type/version, processing state, and audit lineage. Do not store card/payment details or full webhook payloads. |
| Backend and frontend work | Provider adapter interface; signature-verified webhook endpoint; idempotent/out-of-order processor; normalized subscription state machine; server-owned entitlement assignment; sandbox checkout/portal initiation with exact return URLs; billing settings status UI; audit events; reconciliation CLI. |
| Environment/provider configuration | `BILLING_ENABLED=false`, `BILLING_MODE=sandbox`, provider identifier, server-only API/webhook secrets, exact product/price mapping, return-origin allowlist, grace/trial policy. Production mode must fail closed pending explicit later approval. |
| Privacy and security boundaries | Client cannot set plan/status/price. Webhook signature and replay checks precede processing. Provider event IDs are unique. Out-of-order events use provider timestamps/version rules. Portal URLs are short-lived and returned only to the authorized billing owner. |
| Tests and evidence | Valid/invalid signature, replay, duplicate, out-of-order events, unknown product, customer collision, trial/cancel/past-due/grace/reactivation, entitlement timing, portal authorization, webhook body bounds, redaction, provider outage, reconciliation, refunds/support metadata, export/deletion/legal retention. Use provider sandbox/fakes only. |
| Rollout and rollback | Deploy schema/endpoints disabled; provider fake; provider sandbox synthetic account; no live prices/payment. Roll back by disabling checkout/webhook application, preserving receipts/subscription state, and assigning the reviewed fallback entitlement without deleting billing evidence. |
| Completion criteria | Billing sandbox end to end passes, verified events alone change subscription-derived entitlements, reconciliation is repeatable, and tax/refund/live-payment approval remains explicit. |

### Phase 20H — Organization commercial workflows

| Item | Plan |
| --- | --- |
| Objective and scope | Complete expiring invitations, seat limits, ownership transfer, billing contact/plan owner, organization export/deletion, workspace settings, role administration, and audit export. |
| Dependencies | 20F entitlements/seats; optional 20G sandbox mapping; existing organization/membership final-owner and authorization locks. |
| Data model and migrations | Proposed `20260729_0028`: `organization_invitations` with hashed one-time token/expiry/status/role/inviter, and `organization_commercial_profiles` with billing owner/contact user IDs and entitlement assignment link. Add active invitation/seat lock indexes. Extend existing membership rows only through additive reviewed columns if required. |
| Backend and frontend work | Invitation issue/resend/revoke/accept, atomic active-plus-reserved seat checks, owner transfer, billing contact management, organization export and deletion orchestration, workspace settings, audit export, and organization settings UI. |
| Environment/provider configuration | Invitation expiry/resend limits, seat reservation policy, organization export bounds, provider email channel only if 20E is approved; otherwise in-app/copyable admin flow without exposing raw invite tokens after creation. |
| Privacy and security boundaries | Invitation tokens are hashed, one-time, short-lived, and email-bound where appropriate. Membership and seat scope is server-derived. Final-owner and active-job revocation behavior remains unchanged. Support impersonation is prohibited in Phase 20. |
| Tests and evidence | Invite expiry/replay/revoke/collision, existing-account and pending-invitation linking, concurrent final seat, downgrade/removal, owner transfer/final owner, billing-owner authorization, organization deletion/export, audit export redaction, membership-versus-job races, browser E2E, PostgreSQL locks. |
| Rollout and rollback | Start with invitation state and in-app organization settings; external invite email only after 20E. Disable new invites/transfers for rollback while preserving memberships and pending invite revocation. |
| Completion criteria | Invitation and seat state is atomic and tenant-safe, ownership/billing roles are explicit, export/deletion is complete, and existing Phase 16/17 authorization behavior is preserved. |

### Phase 20I — Customer support, status, feedback, and privacy requests

| Item | Plan |
| --- | --- |
| Objective and scope | Establish customer-visible support intake, feedback, abuse reporting, privacy-request tracking, response targets, help/onboarding, release notes, and status-page process. |
| Dependencies | Provider ADRs where an external support/status system is selected; 20B privacy/export/delete; Phase 19 incident/status/alert ownership. |
| Data model and migrations | Proposed `20260729_0029`: first-party `customer_requests` if selected, with request type, owner/org, severity, state, bounded subject/description, consent/contact preference, assigned team role (not person secret), due/closed timestamps, external reference, retention, and audit linkage. Avoid attachments initially; later attachments require Phase 19 malware scanning/private storage. |
| Backend and frontend work | Authenticated/public-safe intake with abuse controls, user request list/status, feedback categories, privacy export/delete request state, administrator triage without impersonation, support/help/privacy pages, status component/link, and release-note workflow. |
| Environment/provider configuration | `CUSTOMER_REQUESTS_ENABLED=false`, `PRIVACY_REQUESTS_ENABLED=false`, exact public status/support URLs, retention/SLA bounds, external provider server secrets only after ADR. |
| Privacy and security boundaries | Public intake reveals no account existence. Requests are tenant/private. Free text is bounded, escaped, excluded from analytics/logs, and never sent to an LLM automatically. Privacy identity verification/recent auth is required before export/delete. No support-agent login-as-user capability. |
| Tests and evidence | Spam/rate/body limits, tenant isolation, generic unauthenticated response, request transitions, SLA calculation, privacy identity/recent-auth checks, export/delete idempotency, retention, redaction, support-provider outage/fallback, status-link safety, accessibility/browser E2E. |
| Rollout and rollback | Publish help/status information first; enable synthetic support/privacy requests; then approved external ticket/status adapter. Roll back external delivery while retaining first-party request status and emergency contact copy. |
| Completion criteria | Support, abuse, feedback, status, and privacy-request processes are usable, private, bounded, exportable/deletable, operationally owned, and documented without impersonation. |

### Phase 20J — Legal, privacy, commercial review and closeout

| Item | Plan |
| --- | --- |
| Objective and scope | Reconcile implemented Phase 20 behavior with qualified legal/privacy/commercial review and produce launch evidence. This is review/evidence work, not a license for new unplanned product capability. |
| Dependencies | 20A–20I; provider contracts/DPAs; finance/tax/refund decisions; Phase 19 external evidence relevant to any activated provider. |
| Data model and migrations | No planned migration. Any review-driven data change returns to the owning subphase with an additive migration and full regression. |
| Backend and frontend work | Update terms, privacy, cookie/analytics controls, acceptable use, financial-research disclaimer, subscription/refund/support copy, subprocessor list, retention table, onboarding/help, release notes, and account/organization commercial views. |
| Environment/provider configuration | Production flags remain disabled until approved. Record provider production/sandbox separation, secret owners/rotation, callback origins, status/support contacts, and rollback. |
| Privacy and security boundaries | Internal drafts are not legal certification. Public claims must match deployed features. No paid launch before qualified review, tested provider controls, and Phase 22 final release approval. |
| Tests and evidence | Documentation/legal-copy route checks, consent-version migration behavior, cookie/analytics consent browser tests, subprocessor/data-flow reconciliation, full backend/PostgreSQL/frontend/browser/migration/security/worker/recovery/Compose suite, provider sandbox evidence, and no-secret review. |
| Rollout and rollback | Roll out approved copy/consent versions with explicit effective dates and re-consent rules. Roll back feature flags/providers, not required legal/audit records. Incorrect public copy is corrected through reviewed deployment. |
| Completion criteria | Every Phase 20 contract gate is evidenced; billing sandbox, notifications, schedules, metering, entitlements, organization workflows, support/privacy processes pass; qualified legal/commercial review is recorded. Phase 22 still owns final deployed-provider and launch approval. |

---

## 7. Proposed migration sequence

Names are planning reservations, not committed revisions. Reconfirm the current
head and split revisions if PostgreSQL lock or downgrade risk requires it.

| Proposed revision | Scope | Downgrade/rollback boundary |
| --- | --- | --- |
| `20260729_0023` | Privacy preferences and product analytics events | Disable collection first; downgrade only after optional events are exported/removed according to policy |
| `20260729_0024` | Monitoring schedules and runs | Disable dispatcher and pause schedules before schema rollback |
| `20260729_0025` | Notification preferences, destinations, intents, deliveries | Disable intent/delivery creation; preserve user-visible records through retention |
| `20260729_0026` | Plan versions, entitlements, assignments, billable usage | Revert resolver to existing quota env policy; fail closed if immutable usage would be lost |
| `20260729_0027` | Billing customer/subscription/webhook normalized state | Disable billing application; do not downgrade if legally/audit-required receipts would be discarded |
| `20260729_0028` | Organization invitations and commercial profile | Revoke pending invites before destructive downgrade; memberships remain authoritative |
| `20260729_0029` | Customer/support/privacy requests | Disable intake; preserve required open/privacy requests and retention evidence |

All migrations must:

- upgrade from a production-like Phase 19 database without reset;
- include ownership and deletion behavior explicitly;
- use bounded indexed columns for callback/provider IDs;
- include PostgreSQL constraints for state and uniqueness where practical;
- support upgrade/downgrade/upgrade before activation;
- fail closed rather than discard immutable billing/usage/legal evidence.

---

## 8. API and frontend surface plan

Exact route names may be refined during each subphase, but the ownership
boundaries are fixed.

```text
GET/PATCH /api/account/privacy-preferences
GET       /api/account/analytics-events

POST/GET/PATCH/DELETE /api/monitoring/schedules
GET                   /api/monitoring/schedules/{id}/runs

GET/PATCH /api/notification-preferences
POST/DELETE /api/notification-destinations
GET/PATCH /api/notifications

GET /api/account/entitlements
GET /api/account/usage
GET /api/organizations/{id}/entitlements
GET /api/organizations/{id}/usage

POST /api/billing/checkout
POST /api/billing/portal
POST /api/integrations/billing/{provider}/webhook
GET  /api/billing/subscription

POST/GET/DELETE /api/organizations/{id}/invitations
POST            /api/organization-invitations/{token}/accept
POST            /api/organizations/{id}/transfer-ownership
GET             /api/organizations/{id}/export

POST/GET /api/customer-requests
POST     /api/privacy-requests
```

The BFF allowlist must add only exact approved families. Webhook callbacks do
not use browser cookies and are never proxied through a generic BFF route.
Frontend pages must handle disabled/not-configured states honestly and must not
show an upgrade, send, or subscription action before its server capability is
enabled.

---

## 9. Validation matrix

Every implementation subphase runs the baseline in [`testing.md`](testing.md)
plus focused checks.

Backend/PostgreSQL:

```bash
cd backend
source .venv/bin/activate
python -m compileall app scripts
alembic upgrade head
alembic downgrade -1
alembic upgrade head
python -m pytest -q
RUN_POSTGRES_INTEGRATION=true python -m pytest -q -m postgres_integration
python scripts/run_smoke_checks.py
python -m scripts.cleanup_expired_data --dry-run
python -m scripts.recover_durable_jobs --dry-run
```

Frontend/browser:

```bash
cd frontend
npm ci
npm run lint
npm run test:bff
npm run test:mfa
npm run test:mfa:routes
npm run test:accessibility
npm run build
npm run test:e2e
```

Security/operations:

```bash
python3 scripts/supply_chain.py check-workflows
python3 scripts/supply_chain.py check-lockfiles
python3 scripts/supply_chain.py check-security-exceptions
docker compose config
docker compose --profile worker config
docker compose -f docker-compose.production.yml config
```

Additional Phase 20 evidence:

- analytics purpose/consent/retention/export/deletion tests;
- event and notification metadata leakage tests;
- PostgreSQL scheduler/seat/meter idempotency and contention tests;
- timezone/DST and missed-run datasets;
- external callback signature/replay/body/SSRF tests;
- provider fake plus selected sandbox tests with synthetic identities only;
- out-of-order billing lifecycle and reconciliation tests;
- plan/quota/meter/entitlement separation tests;
- browser preference/schedule/inbox/usage/billing/org/support flows;
- recovery and deletion tests across active jobs/deliveries/schedules;
- no real payment, customer data, production provider send, or Vast rental in
  CI.

---

## 10. Rollout order and gates

```text
20A approved definitions and ADR process
  -> 20B first-party analytics disabled, then synthetic consent test
     -> 20C scheduler dry-run, then synthetic durable runs
        -> 20D in-app notifications
           -> 20E one approved external channel in sandbox
              -> 20F entitlement shadow comparison and usage ledger
                 -> 20G billing fake, then provider sandbox
                    -> 20H organization seats/invitations
                       -> 20I support/status/privacy workflows
                          -> 20J qualified review and closeout
```

No later slice bypasses an earlier decision gate. Parallel implementation is
allowed only where schemas and authorization boundaries are independent and
both prerequisite reviews are complete.

Global rollback order:

1. disable billing checkout/webhook application;
2. disable external notification submission;
3. disable schedule dispatch;
4. return entitlement resolution to the existing server quota configuration;
5. disable usage and analytics writes;
6. preserve immutable audit/billing/usage records for investigation;
7. keep public demo, synchronous fallback, durable jobs, JSON RAG, and all
   prior-phase data available.

---

## 11. Phase completion gates

Phase 20 cannot be marked `Complete` until:

1. analytics taxonomy, purpose, consent, retention, export, deletion, and
   processor decisions are approved and tested;
2. schedules execute through durable jobs with timezone, idempotency, missed
   run, quota, cancellation, and recovery behavior;
3. notification preferences, verification, rate limits, retries, dead-letter,
   unsubscribe, and deletion work for every enabled channel;
4. network limits, product quotas, billable usage, and plan entitlements are
   demonstrably separate;
5. entitlement state is server-owned, versioned, and cannot be forged by a
   browser, JWT claim, or unverified provider event;
6. billable usage reconciles and never double-counts job retries;
7. a selected billing provider sandbox passes signature, idempotency,
   out-of-order, lifecycle, portal, and rollback tests;
8. organization invitations, seats, ownership transfer, billing contact,
   export/deletion, and audit export pass authorization and concurrency tests;
9. support, status, feedback, abuse, and privacy-request processes have owners,
   retention, response targets, and tested user flows;
10. provider alternatives/ADRs, DPAs, subprocessors, secret ownership, and exit
    plans are documented;
11. qualified legal/privacy/commercial review is recorded and public copy
    matches implemented/deployed behavior;
12. all prior safety, tenant, deterministic-risk, durable-job, JSON fallback,
    Phase 19 security, and disabled-real-Vast boundaries pass;
13. CI is green and remaining deployed launch validation is handed explicitly
    to Phase 22.

Scaffolding, a pricing page, a plan label, an unverified webhook, a provider
mock, or an internal legal draft is not Phase 20 completion.

---

## 12. Recommended first implementation task

Start with **Phase 20A only**.

Deliver:

- approved event-purpose/taxonomy/metadata/retention table;
- consent and anonymous analytics policy;
- usage-unit and entitlement vocabulary;
- notification category and destination classification;
- provider ADR template and scored alternatives;
- proposed `0023` schema review;
- Phase 20 threat-model/evidence-matrix skeletons;
- documentation-only validation.

Do not create tables, emit events, install SDKs, configure provider secrets, or
add UI/API behavior until the 20A review gate is approved.
