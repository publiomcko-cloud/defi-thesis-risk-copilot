# V1 Phase 20 Execution Plan — Product Analytics and Commercial Readiness

Status: **Planned — planning branch only; no Phase 20 runtime capability is implemented**

Branch: `agent/v1-phase-20-product-analytics-commercial-readiness`

Authority:

- [`future_phase_contracts.md`](future_phase_contracts.md), especially the Phase 20 contract, defines scope and completion gates;
- [`current_state.md`](current_state.md) defines the implemented and deployed baseline;
- [`phase_19_evidence_matrix.md`](phase_19_evidence_matrix.md) defines the operational evidence that remains external;
- [`architecture.md`](architecture.md), [`deployment.md`](deployment.md), and [`testing.md`](testing.md) define permanent trust, rollout, and validation boundaries.

This document defines implementation dependencies and review gates. It does not select an analytics, consent, email, webhook, messaging, billing, status, or support provider. Provider integration is blocked until an approved architecture decision record (ADR) documents alternatives, data flows, security, privacy, cost, failure behavior, and exit strategy.

---

## 1. Goal and non-negotiable boundaries

Phase 20 adds:

- privacy-conscious product measurement;
- durable scheduled monitoring;
- user-controlled in-app and approved external notifications;
- server-owned, versioned plan entitlements;
- reconcilable usage metering;
- billing-provider sandbox foundations;
- organization commercial workflows;
- customer support, status, feedback, abuse, and privacy-request operations;
- qualified legal, privacy, finance, and commercial readiness.

It preserves:

- the Phase 15 public-safe anonymous demo;
- Phase 16 identity, ownership, organization, consent, quota, export, deletion, and audit boundaries;
- Phase 17 durable jobs, scoped workers, idempotency, cancellation, recovery, and cost controls;
- Phase 18 server-derived tenant retrieval and JSON RAG fallback;
- Phase 19 request bounds, rate limits, redaction, security checks, incident runbooks, and external operational gates;
- deterministic risk scoring and non-advisory research behavior;
- `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=false` until controlled deployment evidence is approved;
- `VAST_DRY_RUN=true` and `VAST_REAL_RENTALS_ENABLED=false`.

Phase 20 does not add wallets, signing, custody, trading, personalized financial advice, client-controlled plans, automatic live-payment activation, support impersonation, or unreviewed marketing/legal claims.

Phase 22 retains final deployed-provider validation and launch approval.

---

## 2. Required terminology and separate authorities

The implementation must keep these concepts separate in code, persistence, APIs, monitoring, and documentation.

| Concept | Purpose | Persistence | Source of truth | Must not become |
| --- | --- | --- | --- | --- |
| Network rate limit | Protect API, BFF, and compute from burst or sustained abuse | Phase 19 privacy-preserving rate-limit buckets | Shared limiter policy keyed by server-derived scopes | A plan entitlement, invoice quantity, or product-usage statement |
| Product quota | Bound product actions within a period | Existing `usage_quotas`, later resolved from entitlements | Atomic server-side quota service | A billable ledger or request-frequency control |
| Billable usage | Reconcile a chargeable unit exactly once | Immutable usage-meter ledger with idempotency and source lineage | Server-recorded completion/reversal events plus reconciliation | An analytics event, mutable quota counter, or client-provided quantity |
| Plan entitlement | Define feature access and hard limits for a versioned plan | Immutable plan/entitlement versions and server-owned assignments | Entitlement resolver using active assignment and effective dates | A browser flag, editable user field, JWT claim, or unverified provider payload |
| Product analytics | Measure approved product behavior for an explicit purpose | Purpose-bound event store and optional approved exporter | Code-owned taxonomy plus consent/legal-basis gate | Operational telemetry, security audit, billing evidence, or raw user content |
| Consent/preference evidence | Prove the applicable user decision and policy version | Append-only decision ledger plus current projection | Server-recorded decisions and approved policy versions | A mutable checkbox with no historical evidence |

Operational telemetry, product analytics, security/audit records, billing evidence, and support records remain separate domains with distinct purposes, access, retention, export, and deletion rules. Analytics opt-out never suppresses required security, audit, reliability, billing, or legal records.

---

## 3. Target architecture

```text
Browser or backend domain action
  -> authenticated or anonymous server-derived actor
  -> code-owned product event registry
  -> purpose and consent/legal-basis gate
  -> bounded first-party event record
  -> optional approved analytics exporter

Durable schedule
  -> operator scheduler tick
  -> PostgreSQL due-row claim
  -> idempotent Phase 17 job
  -> watchlist or monitoring evaluation
  -> notification intent
  -> preference gate
  -> entitlement gate when the channel or feature is plan-controlled
  -> in-app delivery or approved external delivery job

Product action
  -> server-owned entitlement resolution
  -> product quota reservation or consumption
  -> immutable usage event when applicable
  -> reconciliation

Verified billing callback
  -> immutable verified receipt
  -> idempotent normalization
  -> authoritative provider-state reconciliation when ordering is uncertain
  -> normalized subscription state
  -> server-owned entitlement assignment
```

Every user, organization, schedule, notification, usage, billing, support, and privacy query derives tenant scope from the authenticated actor and active membership. Client-provided IDs, plan names, quantities, destinations, or provider states never establish authorization.

---

## 4. Cross-cutting lifecycle and security decisions

### 4.1 Identifier and ownership policy

- Use bounded repository-style string IDs with domain prefixes.
- User-owned rows have explicit user ownership; organization rows require active membership and role checks.
- Anonymous analytics remains disabled unless a documented legal basis or consent policy permits a short-lived pseudonymous server identifier.
- External processor identifiers are opaque, bounded, server-only metadata.
- Do not store access/refresh tokens, cookies, provider credentials, webhook secrets, payment details, raw strategy text, private source content, private object keys, or complete provider payloads in Phase 20 domain rows.

### 4.2 Versioning and immutability

- Event definitions, purposes, metadata schemas, and retention classes are code-owned and versioned.
- Consent policies are server-owned and versioned.
- `privacy_preferences` is a current projection, not the historical authority.
- Consent grants, withdrawals, re-consent, and policy transitions require immutable evidence. Reuse an existing Phase 16 append-only consent record only if it captures purpose, decision, policy version, actor/scope, timestamp, and withdrawal linkage; otherwise add a Phase 20 decision ledger.
- Activated plan and entitlement versions are immutable. Changes create new versions with effective dates.
- Notification templates, delivery adapters, webhook-signature versions, usage-unit definitions, and billing normalization versions are recorded.
- Billable usage, billing receipts, and audit records use reversals or superseding state rather than destructive mutation.

### 4.3 Export, deletion, and retention authority

- Existing Phase 16 account and organization export/deletion services remain authoritative.
- Phase 20 extends those services through registered projections and lifecycle hooks; it must not implement a second export or deletion authority.
- Privacy-request rows track intake, identity verification, status, deadlines, communication, and orchestration only.
- Analytics withdrawal stops future optional collection immediately.
- Account/organization deletion cancels schedules and pending deliveries, revokes destinations, removes or anonymizes optional analytics according to approved policy, and preserves only required billing/audit/legal evidence in a restricted state.
- Legal holds and required retention must be explicit, narrow, audited, and excluded from normal product serving.
- Cleanup is idempotent, supports dry run, and integrates with existing recovery-evidence guards before destructive actions.

### 4.4 Provider and callback security

- Browser code receives only public configuration and safe display metadata.
- Credentials and signing keys are server/worker-only.
- External callbacks use exact routes, measured body limits, signature verification before processing, replay windows, immutable idempotent receipts, safe normalized fields, and generic errors.
- A verified receipt is persisted before business-state application.
- Webhook arrival order and provider timestamps alone cannot determine subscription authority.
- When a provider lacks a trustworthy monotonic event version or ordering guarantee, retrieve authoritative current subscription state before changing entitlements.
- Entitlements are derived only from reconciled normalized subscription state.
- Outbound webhooks use SSRF-resistant validation, DNS/IP policy, redirect denial, bounded response reads, timeouts, replay-resistant signatures, and per-destination limits.
- External notification content contains minimal metadata or authenticated links by default, not private report/source bodies.
- Commercial and organization billing changes are audited.

---

## 5. Provider decision gates

No provider is selected by this plan. Before adding an adapter or SDK, create an ADR under `docs/decisions/` that records alternatives, scoring, data flows, subprocessors, data location, secrets, sandbox/production separation, failure mode, cost, portability, and exit plan.

| Capability | Alternatives to evaluate | Required criteria |
| --- | --- | --- |
| Product analytics | First-party PostgreSQL; PostHog cloud/self-hosted; Plausible; another reviewed processor | Consent/legal-basis controls, allowlisted events, data location, DPA/subprocessors, export/deletion, server ingestion, identifier policy, retention, cost, lock-in, outage behavior |
| Consent management | First-party records/UI; Cookiebot; OneTrust; another reviewed CMP | Regional rules, proof/versioning, withdrawal, accessibility, cookie blocking, export/deletion, data location, cost |
| Transactional email | Postmark; Resend; Amazon SES; another reviewed service | Domain authentication, deliverability, suppression/unsubscribe, verified callbacks, DPA, sandbox, retention, cost |
| Outbound webhook delivery | First-party Phase 17 adapter; Svix; Hookdeck or equivalent | Signing/replay, retries/dead letter, SSRF controls, verification, tenant isolation, observability, payload retention, portability |
| Messaging | Telegram Bot API; reviewed multi-channel provider; defer | Destination verification/revocation, privacy, secret handling, regional availability, abuse controls, evidence, cost |
| Billing | Stripe Billing; Paddle; Lemon Squeezy; another reviewed provider; remain unpaid | Processor versus merchant-of-record obligations, markets/currencies, tax/VAT, sandbox, webhook guarantees, lifecycle, portal/refunds, DPA, fees, migration/export |
| Status page | Statuspage; Better Stack; Instatus; first-party static status | Independent availability, incident API, subscriber privacy, custom domain, access, retention, cost |
| Customer support | First-party intake; Help Scout; Zendesk; Freshdesk; another reviewed system | DPA/privacy, role controls, export/deletion, audit, SLA workflows, attachment scanning, cost, exit path |

Approval requirements:

1. product and engineering approve capability and operational fit;
2. security approves data flow, secrets, callbacks, abuse controls, and failure mode;
3. privacy/legal approves purpose/legal basis, DPA, subprocessors, retention, data location, and user-facing copy;
4. finance/commercial approves usage units, plan semantics, tax, refund, trial, cancellation, grace, and merchant-of-record responsibilities;
5. sandbox credentials use approved server-side secret storage;
6. adapters remain disabled until focused security, lifecycle, failure, and rollback tests pass.

External prerequisites remain explicit:

- Phase 19 centralized telemetry, alert delivery, provider restore drills, production secret rotation, protected-branch enforcement, and controlled deployment evidence;
- operator-owned sandbox accounts, verified domains/destinations, callback origins, and revocation procedures;
- qualified privacy/legal/finance ownership;
- Phase 22 final deployed-provider and launch approval.

---

## 6. Dependency graph and implementation subphases

Phase 20 uses a dependency graph, not a fully linear chain.

```text
20A common definitions, threat model, evidence matrix, and ADR process
  ├─> 20B consent-aware analytics, only after analytics privacy/legal approval
  ├─> 20C durable schedules, independent of optional analytics
  ├─> 20F entitlements and usage metering, independent of optional analytics
  └─> 20I first-party support/status/privacy-request foundations where no provider is required

20C plus approved notification definitions
  └─> 20D in-app notifications

20D plus approved provider ADR and Phase 19 provider prerequisites
  └─> 20E external-channel sandbox development
       └─> customer activation only after applicable 20F entitlements

20F plus approved billing ADR
  └─> 20G billing sandbox

20F plus existing organization authority
  └─> 20H organization commercial workflows
       └─> optional 20G subscription mapping

20A–20I plus all required reviews and evidence
  └─> 20J closeout
```

Parallel work is allowed only when schemas and authorization boundaries are independent and every dependency/review gate is complete.

### Phase 20A — Definitions, privacy contract, threat model, and decision records

| Item | Plan |
| --- | --- |
| Objective | Define approved analytics purposes, event taxonomy, metadata allowlists, retention classes, consent behavior, usage units, entitlement vocabulary, notification categories, and provider decision process. |
| Dependencies | Merged Phase 19 foundations; existing Phase 16 consent/export/deletion authority; named product, engineering, security, privacy/legal, and finance owners. |
| Data/migrations | No runtime migration. Specify proposed revisions `0023`–`0029` and reconfirm migration head at implementation time. |
| Deliverables | `docs/phase_20_threat_model.md`; `docs/phase_20_evidence_matrix.md`; provider ADR template; event-purpose/metadata/retention/consent matrix; usage-unit and entitlement registry proposal; notification category/destination classification; data-flow and lifecycle diagrams. |
| Boundaries | No runtime collection, tables, SDKs, provider secrets, sends, payments, or client-facing commercial behavior. |
| Tests/evidence | Link checks, schema examples, threat-model review, data-flow review, confirmation that no runtime/env/migration changed. |
| Completion | Definitions and decision owners are approved; unresolved choices are explicit; independent subphase gates are documented. |

Gate to 20B: privacy/legal approves analytics purposes, legal basis/consent, immutable decision evidence, retention, export, and deletion. Missing approval blocks 20B, not unrelated 20C/20F work.

### Phase 20B — Consent-aware first-party product analytics

| Item | Plan |
| --- | --- |
| Objective | Implement bounded first-party analytics without an external SDK. |
| Dependencies | 20A analytics approval; Phase 16 identity/anonymous lifecycle; Phase 19 redaction/correlation. |
| Data/migrations | Proposed `0023`: `privacy_preferences` current projection; append-only `privacy_preference_decisions` unless an existing Phase 16 record satisfies the full evidence contract; append-only `product_analytics_events`. Include purpose, schema/policy version, server-derived scope, bounded dimensions, consent/legal-basis snapshot, timestamps, expiry, and deletion/anonymization state. |
| Backend/frontend | Code-owned registry, server emitter, consent/legal-basis gate, preference APIs/UI, export projection, deletion/lifecycle hooks. Emit only at approved server-owned completion points. |
| Configuration | Disabled by default; first-party mode; server-only pseudonymization pepper; approved versions; retention; bounded sampling. |
| Boundaries | No raw queries, strategies, sources, email, IP, URL, user agent, referrer query, identifiers in dimensions, or arbitrary browser events. |
| Tests | Grant, withdrawal, re-consent, policy transition, concurrent updates, event allowlists, duplicate prevention, anonymous policy, tenant isolation, redaction, retention, export/deletion, and independence from audit/telemetry. |
| Rollout | Deploy disabled; synthetic/private test scope; rollback disables emission while preserving approved evidence for lifecycle cleanup. |
| Completion | Optional analytics obeys approved purpose and user decisions; immutable consent evidence, export/deletion, retention, and no-sensitive-data tests pass. |

### Phase 20C — Durable scheduled monitoring

| Item | Plan |
| --- | --- |
| Objective | Add user/organization schedules for existing watchlist or monitoring evaluations through Phase 17 jobs. |
| Dependencies | 20A schedule/usage definitions; Phase 17 worker/recovery; existing watchlists/alerts; Phase 19 queue monitoring. Analytics is not a prerequisite. |
| Data/migrations | Proposed `0024`: `monitoring_schedules` and `monitoring_schedule_runs`; owner/org scope, target, normalized cadence, IANA timezone, next/last run, missed-run policy, status, limits, idempotency, source job, result, timestamps, tombstone; unique `(schedule_id, scheduled_for)`. |
| Backend/frontend | Exact job contract, bounded PostgreSQL due-row claim, operator scheduler, create/list/detail/pause/resume/delete APIs, UI and run history. |
| Configuration | Disabled by default; batch/lag/horizon limits; cadence floor; active-schedule limits; scoped worker. Use a maintained timezone/recurrence library. |
| Boundaries | Scope and target are server-derived; active membership is revalidated at dispatch and execution; no arbitrary URLs/providers. |
| Tests | DST, invalid zones, next-run math, missed-run policies, one-winner claims, idempotent job creation, saturation, worker loss, membership removal, quota/cost denial, cancellation, retention, export/deletion, browser E2E, PostgreSQL contention. |
| Rollout | Dry-run due calculation, then synthetic schedules at low cadence. Rollback disables dispatcher and pauses schedules. |
| Completion | Work survives restarts, runs once, respects scope/quota/cost, handles DST/missed runs, and can be paused/deleted safely. |

### Phase 20D — Notification domain and in-app delivery

| Item | Plan |
| --- | --- |
| Objective | Add user-controlled categories/preferences and durable in-app notifications before customer external delivery. |
| Dependencies | 20A notification definitions; 20C schedule outcomes or existing alerts; Phase 16 ownership. Optional analytics is not required. |
| Data/migrations | Proposed `0025`: notification preferences, destinations, notifications/intents, and deliveries. Preferences are unique by subject/category/channel; intents are idempotent; destinations have verification/revocation; deliveries record safe normalized status. |
| Backend/frontend | Preference/inbox APIs, read/archive state, approved intent creation, category/severity filters, timezone/quiet hours, digest configuration, accessible UI. |
| Configuration | Notifications and in-app delivery disabled by default; retention, digest bounds, and per-user/category limits. |
| Boundaries | Content is bounded and excludes report/source bodies. Membership is checked independently of preference. |
| Tests | Isolation, defaults/off behavior, duplicate suppression, quiet hours, digesting, membership removal, lifecycle, retention, accessibility, browser E2E, quota/rate-limit separation. |
| Rollout | Synthetic in-app intents first. Rollback disables intent creation while existing inbox records follow retention. |
| Completion | Users control in-app delivery; duplicate intents and tenant leakage are prevented. |

### Phase 20E — Approved external notification delivery

| Item | Plan |
| --- | --- |
| Objective | Add only channels approved by ADR; email and signed webhooks are candidates, Telegram may be deferred. |
| Dependencies | 20D; provider/security/privacy ADR; Phase 17 jobs; relevant Phase 19 outbound, monitoring, alert, and secret-management evidence. |
| Data/migrations | Prefer `0025`; add only normalized adapter metadata when required. Never persist raw credentials or full payloads. |
| Backend/frontend | Exact delivery-job schema, adapter, destination verification, signature versions, unsubscribe/revocation, retry/dead-letter, status UI, aggregate diagnostics. |
| Configuration | Per-channel disabled flags; sandbox mode; server/worker-only credentials; timeouts, response bounds, retries, and channel ceilings. |
| Boundaries | Before 20F, only synthetic or administrator-controlled sandbox destinations may be used. Customer plan-gated activation requires server-owned entitlement checks. In-app remains fallback. |
| Tests | Provider fakes, signature/replay, verification/revocation, SSRF/private-IP/DNS-change/redirect denial, retries/dead-letter, idempotency, bounce/suppression, quiet hours, rate limits, redaction, outage, lifecycle, browser status. No real send in CI. |
| Rollout | One sandbox channel at a time. Customer activation only after applicable 20F entitlement gates and approvals. |
| Completion | Sandbox delivery is secure and recoverable; disabled adapters preserve in-app behavior. Customer activation is not claimed prematurely. |

### Phase 20F — Usage metering and versioned plan entitlements

| Item | Plan |
| --- | --- |
| Objective | Introduce server-owned plan versions, hard feature entitlements, and immutable usage while preserving existing quota behavior during migration. |
| Dependencies | 20A usage/entitlement definitions; Phase 16 quota/plan compatibility; Phase 17 job/cost reservations. Optional analytics is not required. |
| Data/migrations | Proposed `0026`: immutable plan versions, plan entitlements, effective-dated assignments, and billable usage events with server-derived unit/quantity, source lineage, idempotency, period, reversal, and reconciliation state. |
| Backend/frontend | Registry/resolver, safe catalog/current-plan/usage APIs, server-owned usage recorder, reconciliation command, read-only account/billing view until verified commercial workflow. |
| Configuration | Entitlements and metering disabled by default; fallback plan and reconciliation bounds; existing quotas remain rollback authority. |
| Boundaries | Browser/JWT/provider claims cannot grant access. Usage does not contain analytics dimensions or private inputs. Admin exemptions are explicit and audited. |
| Tests | Effective dates, forgery denial, quota parity, hard denial, immutability, idempotency/reversal, concurrency, retry without double metering, org scope, retention/export, reconciliation mismatch, browser summaries. |
| Rollout | Shadow-resolve against current policy; record non-billed usage; compare; enable selected hard checks. |
| Completion | Four core controls remain separate; entitlements are enforceable and usage is exactly-once/reconcilable. |

### Phase 20G — Billing-provider sandbox foundation

| Item | Plan |
| --- | --- |
| Objective | After an approved ADR, support sandbox customer/subscription mapping, verified callbacks, normalized lifecycle, portal links, and entitlement updates. No live payment. |
| Dependencies | 20F; billing ADR; finance/tax/legal review; relevant Phase 19 controls; provider sandbox. |
| Data/migrations | Proposed `0027`: billing customers, subscriptions, immutable webhook receipts, and optional entitlement-change lineage. Store opaque IDs, normalized status, plan mapping, periods, payload hash, provider event/version metadata, processing state, and audit lineage; no card details or full payloads. |
| Backend/frontend | Provider adapter, signature endpoint, persist-before-process receipt, idempotent normalizer, authoritative state fetch/reconciliation, subscription state machine, entitlement assignment, sandbox checkout/portal, status UI, audits, reconciliation CLI. |
| Configuration | Billing disabled; sandbox mode; exact product/price mapping; server-only secrets; return-origin allowlist; trial/grace policy; production fails closed. |
| Boundaries | Verified receipt alone does not automatically establish current entitlement. Never trust arrival order or timestamps alone. Use provider monotonic version where reliable; otherwise retrieve current authoritative state. Entitlements derive only from reconciled normalized state. |
| Tests | Invalid/valid signature, replay, duplicate, stale, concurrent, reordered events, uncertain ordering with authoritative fetch, unknown products, collisions, trial/cancel/past-due/grace/reactivation, portal authorization, body bounds, redaction, outage, reconciliation, legal retention. |
| Rollout | Fake, then synthetic provider sandbox. No live prices/payment. Rollback disables checkout and event application while preserving receipts/state and assigning reviewed fallback entitlements. |
| Completion | Sandbox works end to end; only reconciled state changes entitlements; stale and reordered callbacks cannot regress state. |

### Phase 20H — Organization commercial workflows

| Item | Plan |
| --- | --- |
| Objective | Complete expiring invitations, seat limits, ownership transfer, billing contact/plan owner, export/deletion orchestration, workspace settings, role administration, and audit export. |
| Dependencies | 20F entitlements/seats; optional 20G mapping; existing Phase 16 organization authority. |
| Data/migrations | Proposed `0028`: hashed one-time organization invitations and commercial profile with billing owner/contact and entitlement linkage. |
| Backend/frontend | Issue/resend/revoke/accept invitation, atomic active-plus-reserved seats, ownership transfer, billing contacts, existing export/deletion orchestration, workspace settings, audit export, UI. |
| Configuration | Invitation expiry/resend, seat reservation, export bounds. External invite email only after approved 20E; otherwise secure in-app/admin flow. |
| Boundaries | Tokens are hashed, short-lived, one-time, and destination-bound where appropriate. Scope is server-derived; final-owner and active-job rules remain. |
| Tests | Expiry/replay/revoke/collision, existing-account linking, concurrent final seat, downgrade/removal, owner transfer, billing-owner authorization, export/deletion hooks, audit redaction, membership/job races, browser E2E, PostgreSQL locks. |
| Rollout | Begin with state and in-app settings; disable new invites/transfers for rollback while preserving memberships. |
| Completion | Invitation/seat state is atomic and tenant-safe; commercial roles and lifecycle are explicit. |

### Phase 20I — Customer support, status, feedback, abuse, and privacy requests

| Item | Plan |
| --- | --- |
| Objective | Establish bounded customer-facing intake, request tracking, response targets, help/onboarding, release notes, and status process. |
| Dependencies | 20A privacy/support definitions; Phase 19 incident/status ownership; provider ADR only when an external system is selected. 20B is required only for analytics-specific preference/export behavior. |
| Data/migrations | Proposed `0029`: first-party customer/privacy request tracking when selected, with type, owner/org, severity, state, bounded text, verified contact preference, role assignment, due/closed timestamps, external reference, retention, and audit linkage. Avoid attachments initially. |
| Backend/frontend | Public-safe/authenticated intake, user request status, feedback/abuse categories, privacy-request orchestration, admin triage without impersonation, help/privacy/status pages, release-note workflow. |
| Authority boundary | Phase 20 records intake, verification, deadlines, status, and communication. Existing Phase 16 account/organization export and deletion services perform the actual operation and remain authoritative. |
| Security | Public intake reveals no account existence. Text is bounded, escaped, excluded from analytics/logs, and never automatically sent to an LLM. Recent authentication and existing job/legal-hold/retention rules apply before export/deletion. |
| Tests | Spam/rate/body bounds, isolation, generic responses, transitions/SLAs, recent-auth verification, orchestration idempotency, existing export/deletion integration, retention, redaction, provider fallback, status-link safety, accessibility/browser E2E. |
| Rollout | Help/status first; synthetic requests; external adapters only after ADR. Rollback external delivery while retaining first-party status and emergency contact information. |
| Completion | Processes are usable, private, bounded, operationally owned, and reuse existing lifecycle authority. |

### Phase 20J — Legal, privacy, commercial review and closeout

| Item | Plan |
| --- | --- |
| Objective | Reconcile implemented behavior with qualified legal/privacy/commercial review and produce Phase 20 evidence. |
| Dependencies | Required 20A–20I capabilities and reviews; provider contracts/DPAs; finance/tax/refund decisions; relevant Phase 19 external evidence. |
| Data/migrations | No planned migration. Review-driven data changes return to the owning subphase. |
| Work | Terms, privacy/cookie controls, acceptable use, financial-research disclaimer, subscription/refund/support copy, subprocessors, retention table, onboarding/help, release notes, commercial views. |
| Boundaries | Internal drafts are not legal certification. Public claims match deployed capabilities. No paid launch before qualified review and Phase 22 approval. |
| Tests/evidence | Legal-copy routes, consent version/re-consent, browser consent, subprocessor/data-flow reconciliation, full regression/security/recovery suites, provider sandbox evidence, no-secret review. |
| Completion | Every Phase 20 contract gate is evidenced and qualified review is recorded; Phase 22 retains final launch approval. |

---

## 7. Proposed migration sequence

Names are planning reservations, not committed revisions. Reconfirm the migration head and split revisions when locking, downgrade, or lifecycle risk requires it.

| Proposed revision | Scope | Rollback boundary |
| --- | --- | --- |
| `0023` | Privacy current projection, immutable decision evidence if needed, product analytics events | Disable collection; preserve required decision evidence; remove/anonymize optional events according to approved policy |
| `0024` | Monitoring schedules and runs | Disable dispatcher and pause schedules before schema rollback |
| `0025` | Notification preferences, destinations, intents, and deliveries | Disable creation/delivery and preserve visible records through retention |
| `0026` | Plan versions, entitlements, assignments, and billable usage | Revert resolver to existing quota policy; fail closed if immutable usage would be lost |
| `0027` | Billing customer/subscription/receipt normalized state | Disable billing application; do not discard legally/audit-required receipts |
| `0028` | Organization invitations and commercial profile | Revoke pending invitations before destructive downgrade; memberships remain authoritative |
| `0029` | Customer/support/privacy request tracking | Disable intake; preserve required open/privacy requests and evidence |

All migrations must:

- upgrade from a production-like Phase 19 database without reset;
- define ownership, retention, deletion, and legal-hold behavior;
- use bounded indexed callback/provider identifiers;
- enforce state and uniqueness constraints where practical;
- pass upgrade/downgrade/upgrade before activation;
- fail closed rather than discard immutable consent, usage, billing, audit, or legal evidence.

---

## 8. API and frontend surface plan

Exact routes may be refined, but ownership and authority boundaries are fixed.

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

The BFF adds only exact approved route families. Provider callbacks do not use browser cookies and are never proxied through a generic BFF route. Frontend pages display disabled/not-configured states honestly and do not show upgrade, send, or subscription actions before server capability and entitlement gates are enabled.

---

## 9. Validation matrix

Every implementation subphase runs the baseline in [`testing.md`](testing.md) plus focused tests.

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

Additional Phase 20 evidence includes:

- analytics purpose, consent, immutable decision, retention, export, and deletion tests;
- metadata leakage tests;
- scheduler, seat, usage, receipt, and entitlement idempotency/contention tests;
- timezone/DST and missed-run datasets;
- callback signature, replay, stale/reordered-event, body-bound, and SSRF tests;
- provider fakes plus approved sandbox tests with synthetic identities;
- plan/quota/usage/entitlement separation;
- existing export/deletion authority integration;
- browser preference, schedule, inbox, usage, billing, organization, support, and privacy flows;
- recovery/deletion across active jobs, deliveries, and schedules;
- no real payment, customer data, production provider send, or Vast rental in CI.

---

## 10. Rollout and rollback gates

Implementation rollout follows the dependency graph, not a mandatory single chain.

```text
20A approved common definitions
  ├─> 20B analytics after analytics-specific approval
  ├─> 20C scheduler dry-run and synthetic durable runs
  ├─> 20F entitlement shadow comparison and non-billed usage ledger
  └─> 20I first-party help/status/request foundations

20C -> 20D in-app notifications
20D -> 20E approved external-channel sandbox
20F -> customer activation of plan-gated external channels
20F -> 20G billing fake and provider sandbox
20F -> 20H organization seats/invitations
20A–20I -> 20J qualified review and closeout
```

Global rollback order:

1. disable billing checkout and subscription-state application;
2. disable external notification submission;
3. disable schedule dispatch;
4. return entitlement resolution to the existing server quota configuration;
5. disable usage and optional analytics writes;
6. preserve immutable consent, audit, billing, and usage evidence;
7. keep public demo, synchronous fallback, durable jobs, JSON RAG, and prior-phase data available.

---

## 11. Phase completion gates

Phase 20 cannot be marked `Complete` until:

1. analytics taxonomy, purposes, legal basis/consent, immutable decision evidence, retention, export, deletion, and processor decisions are approved and tested;
2. schedules execute through durable jobs with timezone, idempotency, missed-run, quota, cancellation, and recovery behavior;
3. notification preferences, verification, entitlement gates, rate limits, retries, dead-letter, unsubscribe, and deletion work for every enabled channel;
4. network limits, product quotas, billable usage, and plan entitlements are demonstrably separate;
5. entitlement state is server-owned, versioned, and cannot be forged by a browser, JWT claim, or unverified provider event;
6. billable usage reconciles and never double-counts retries;
7. a selected billing sandbox passes signature, receipt persistence, idempotency, stale/reordered/concurrent event handling, authoritative reconciliation, lifecycle, portal, and rollback tests;
8. organization invitations, seats, ownership transfer, billing contact, export/deletion hooks, and audit export pass authorization and concurrency tests;
9. support, status, feedback, abuse, and privacy-request processes have owners, retention, response targets, and tested flows while existing export/deletion services remain authoritative;
10. provider ADRs, DPAs, subprocessors, secret ownership, and exit plans are documented;
11. qualified legal/privacy/commercial review is recorded and public copy matches implemented/deployed behavior;
12. all prior safety, tenant, deterministic-risk, durable-job, JSON fallback, Phase 19 security, and disabled-real-Vast boundaries pass;
13. CI is green and remaining deployed launch validation is handed explicitly to Phase 22.

Scaffolding, a pricing page, a plan label, a provider mock, an unverified webhook, or an internal legal draft is not Phase 20 completion.

---

## 12. Recommended first implementation task

Start with **Phase 20A only**.

Deliver:

- `docs/phase_20_threat_model.md`;
- `docs/phase_20_evidence_matrix.md`;
- provider ADR template and scored alternatives;
- event-purpose, metadata, retention, and consent matrix;
- consent/anonymous analytics policy and immutable evidence decision;
- usage-unit and entitlement registry proposal;
- notification category/destination classification;
- proposed `0023` schema and lifecycle review;
- documentation-only validation.

Do not create tables, emit events, install SDKs, configure provider secrets, or add UI/API behavior until the relevant 20A review gate is approved.
