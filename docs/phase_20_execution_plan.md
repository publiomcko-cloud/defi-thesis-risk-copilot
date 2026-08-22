# V1 Phase 20 Execution Plan — Portfolio Architecture Readiness

Status: **In Progress — Phase 20D merged; Phase 20F entitlements and non-billable usage is the next required slice**

Next implementation branch: `agent/v1-phase-20f-entitlements-usage`

Current authority:

- [`portfolio_profile.md`](portfolio_profile.md) — active implementation profile;
- this plan — selected Phase 20 sequence;
- [`phase_20_evidence_matrix.md`](phase_20_evidence_matrix.md) — evidence and completion state;
- [`productization_backlog.md`](productization_backlog.md) — intentionally deferred product-only work;
- [`future_phase_contracts.md`](future_phase_contracts.md) — broader product-capable target contract.

The active goal is to demonstrate production-grade architecture, not to operate a commercial SaaS service. Security, tenant isolation, migrations, lifecycle, deterministic-risk, recovery, and rollback requirements are not reduced.

## 1. Portfolio scope

```text
20A governance/threat/evidence foundation       COMPLETE
  -> 20B consent-aware first-party analytics   COMPLETE

20A
  -> 20C durable scheduled monitoring          REQUIRED
       -> 20D in-app notifications             REQUIRED
            -> 20E secure synthetic adapter    OPTIONAL
  -> 20F entitlements + non-billable usage     REQUIRED
       -> 20H organization SaaS controls       REQUIRED
  -> 20I minimal support/privacy/status        REQUIRED

20G real billing/provider work                  DEFERRED

required selected slices
  -> 20J portfolio architecture closeout       REQUIRED
       -> Phase 21
```

20C, 20F, and provider-free 20I may proceed independently.

## 2. Permanent boundaries

Preserve Phase 15–19 behavior and evidence boundaries. In particular:

- server-derived identity, tenant scope, plan state, quantities, and provider state;
- Phase 16 export/deletion authority;
- Phase 17 durable jobs, retries, idempotency, cancellation, recovery, capacity, and cost controls;
- Phase 18 JSON RAG fallback and tenant-safe retrieval boundaries;
- Phase 19 request bounds, rate limits, redaction, security, incident, and recovery controls;
- deterministic risk values remain authoritative;
- no wallet, signing, custody, trade execution, or personalized financial advice;
- no client-controlled entitlements or provider state;
- no claim that a synthetic or disabled capability is commercially live.

Safe production defaults remain disabled until separate activation gates pass, including analytics collection, private pgvector cutover, and real Vast rentals.

## 3. Phase 20A

Status: **Complete for portfolio profile**.

Keep the existing threat model, evidence matrix, event-purpose/consent/retention taxonomy, machine-checkable event examples, usage-unit/entitlement registry, notification classification, provider ADR template/scorecards, and proposed `0023`–`0029` data-model review. Product-only provider/commercial material remains useful as future productization evidence.

## 4. Phase 20B

Status: **Implementation complete for portfolio profile**.

Migration `20260731_0023`, immutable consent decisions, current preference projection, four bounded first-party events, lifecycle integration, accessible UI, deployment-disabled consent correction, PostgreSQL concurrency/idempotency tests, and hosted CI are complete.

Production analytics activation remains deferred to qualified productization review and does not block later portfolio slices.

## 5. Phase 20C — Durable scheduled monitoring

Locally complete implementation slice. The original implementation and the
authoritative-completion/scheduled-run-quota correction both passed hosted CI;
it merged as `8aeb84cec0427765322cf44b3827eee319e8064e`. Production dispatch remains disabled until
its documented concurrency, recovery, DST, lifecycle, rollback, worker, and
approval evidence has been reviewed. It is not a production activation.

Initial policy:

- authenticated user-owned schedules first;
- organization scheduling waits for 20H authority;
- only code-owned watchlist/monitoring targets;
- cadence presets: hourly, six-hourly, daily, weekly;
- minimum cadence: one hour;
- validated IANA timezone and DST behavior;
- maximum five active schedules per user;
- unique occurrence identity by schedule plus scheduled time;
- missed runs coalesce to at most one replacement;
- occurrences over 24 hours late are recorded as missed and skipped;
- authorization, a fixed 120-per-user UTC-day non-billable scheduled-run quota,
  capacity, and cost gates revalidate at dispatch/execution;
- 30-day run history;
- deletion cancels owned schedules/jobs;
- rollback disables dispatcher without corrupting history.

Use Phase 17 jobs. Test restart survival, one-winner PostgreSQL claims, idempotency, worker loss, pause/resume/delete, authorization revocation, quota/cost denial, export/deletion, DST, and browser behavior.

Implemented boundary: migration `0024`, private schedule/occurrence models,
server-owned `watchlist.evaluate` registry input, `SKIP LOCKED` dispatch,
feature-gated scheduler script/profile, account lifecycle/retention/export
hooks, operations aggregates, and `/schedules`. Evaluation leaves its
occurrence `running`; only the authoritative Phase 17 `complete_job()`
transition records successful completion. Remaining checkpoint evidence is a
separately approved production rollout; organization schedules and all
non-watchlist targets remain out of scope until later slices.

## 6. Phase 20D — In-app notifications

Status: **Merged / production-disabled**.

Initial categories:

- `monitoring.risk_alert`;
- `schedule.status`;
- `job.status`;
- `account.lifecycle`.

Product/status categories default off where user preference applies. Support informational/warning/critical severity, IANA timezone, optional quiet hours, daily digest, idempotent intents, duplicate suppression, lifecycle, accessibility, tenant isolation, and 30-day in-app retention.

For suppressible categories, surfacing is deterministic: category enablement,
then minimum severity, then daily digest availability (moved to the first
permitted boundary when the digest time is quiet), then quiet-hour delay when
digest is disabled. Critical severity does not bypass these preferences.
`account.lifecycle` is mandatory and immediately available.

Content is minimal and code-owned. Do not include raw strategies, reports, sources, private documents, support bodies, credentials, or provider payloads.

External providers are not required for 20D.

Implemented boundary: migration `0025`, server-owned notification preference
and notification records, a code-owned source-event registry, deterministic
idempotency keys with database uniqueness, preference/quiet-hour/digest
surfacing policy, authenticated `/notifications` API, account export and
deletion integration, retention cleanup, and an accessible `/notifications`
workspace with unread count. Source projections are attached to existing
watchlist alert creation, schedule occurrence lifecycle, Phase 17 terminal job
transitions, account export, and MFA lifecycle events. The browser cannot
author category, severity, source, owner, recipient, template, navigation, or
idempotency identity.

Final Phase 20D head `6a943e1bc6293ba88bcd7a8ab6ca68baca822e37`
passed hosted PostgreSQL-backed CI, frontend/browser and Compose checks,
CodeQL, Supply Chain Security including Gitleaks and Trivy, and Phase 19
Failure Exercises. It merged to `main` as
`32dfb91ece2344be5dbbcd2c8d12723bc2378126` on 2026-08-21. Production
activation and external delivery evidence remain separate and are not claimed.

## 7. Phase 20E — Secure delivery demonstration

Optional portfolio slice.

Prefer provider-neutral interfaces and fakes:

```text
NotificationAdapter
  -> InAppAdapter
  -> FakeEmailAdapter
  -> optional SignedWebhookSandboxAdapter
```

A synthetic webhook adapter may demonstrate HTTPS validation, SSRF/private-IP defenses, redirect denial, bounded responses/timeouts, versioned signatures, replay protection, retries/dead letter, idempotency, redaction, and key rotation. No uncontrolled external send is required.

Real email, webhook-delivery, and Telegram providers move to productization backlog.

## 8. Phase 20F — Entitlements and non-billable usage

Status: **Implementation in progress; shadow-only and non-billable.**

Implement immutable versioned plans/entitlements, effective server-owned assignments, shadow comparison with existing quotas, safe fallback, and immutable usage/reversal records.

Initial `free-v1` limits:

- 25 analyses/day;
- 100 simulations/day;
- 100 options analyses/day;
- 100 market-data fetches/day;
- 50 saved theses;
- 25 watchlists;
- 5 active schedules.

An optional `portfolio-pro-preview-v1` may exist only for tests/demonstration. It has no price and cannot be purchased.

Initial non-billable usage units:

- completed report;
- completed simulation;
- completed options analysis;
- successful schedule run.

Failures, cancellations, rejections, quota denials, and incomplete work do not count. Retries cannot double meter. Corrections use linked reversals/adjustments. Usage remains separate from analytics, quotas, rate limits, and any future billing system.

Implemented design: migration `0026` creates versioned plans, plan entitlements,
user-only effective assignments, and an immutable non-billable usage ledger.
`free-v1` is seeded by migration `0026` and resolved only from database state;
the authenticated read endpoint is read-only and users without an assignment
resolve through an implicit server-owned default.
The resolver compares its result to the existing `UserModel.plan` authority but
never admits, rejects, or changes a legacy quota/resource decision. Missing,
ambiguous, invalid, or unknown state returns bounded `free-v1` limits and a
visible mismatch. The only active units are the four versioned units approved
in the owner decision. Meter rows are inserted in the successful report,
simulation, options, and authoritative Phase 17 schedule-completion
transactions; uniqueness at `(unit_key, logical_key)` is the final exactly-once
authority. Account export includes assignments/events and deletion disposes
them. Organization entitlement semantics, billing and commercial retention
remain deferred.

Correction evidence also keeps shadow logs bounded to result, policy key, and
numeric limit comparisons; no raw account identifier is emitted. Phase 20C
lease-loss/retry coverage proves completion usage remains zero until the
authoritative worker completion transaction succeeds, then remains exactly one.

## 9. Phase 20G — Billing

**Deferred from required portfolio scope.**

Do not delay Phase 21 for real payment-provider integration, live checkout, public prices, tax/refund policy, or paid-plan activation.

An optional `FakeBillingProvider` may demonstrate immutable synthetic receipts, normalized subscription states, stale/reordered-event handling, reconciliation, and entitlement updates from reconciled state only. It must remain clearly synthetic.

All real billing work lives in [`productization_backlog.md`](productization_backlog.md).

## 10. Phase 20H — Organization SaaS controls

Required after 20F.

Portfolio rules:

- hashed one-time invitations;
- seven-day expiry;
- resend/revoke invalidates prior active tokens;
- pending invitations reserve seats;
- five active-or-reserved seats under the portfolio plan;
- owner/admin invitation authority;
- owner-only ownership transfer and full lifecycle authority;
- recent-auth ownership transfer;
- atomic final-seat checks;
- existing over-limit organizations are not destructively modified; new invites are blocked until within the limit or assigned another test entitlement;
- invitation input cannot assign a plan;
- external invitation email is not required.

## 11. Phase 20I — Minimal support/privacy/status

Required reduced portfolio slice.

Use first-party bounded request tracking for:

- `support`;
- `feedback`;
- `abuse_report`;
- `privacy_access_export`;
- `privacy_deletion`.

No attachments initially. Bound subject to 120 characters and description to 4,000 characters. Request text is excluded from product analytics, normal logs, and automatic LLM processing.

Phase 20I tracks intake, verification, state, due dates, communication, and orchestration. Existing Phase 16 export/deletion services perform the actual account/organization operation.

A simple public-safe status process is sufficient. External helpdesk/status providers and subscriber email collection are not required.

## 12. Phase 20J — Portfolio architecture closeout

Phase 20 may be marked **Complete — Portfolio Profile** when:

- required 20A–20I selected slices pass their implementation, migration, tenant, concurrency, failure, recovery, lifecycle, rollback, and browser tests;
- 20E, when omitted or synthetic, is accurately documented;
- real 20G remains explicitly deferred rather than falsely completed;
- no unresolved high/critical security regression exists;
- public portfolio flags remain safe;
- docs clearly separate implemented, enabled, synthetic, disabled, and productization-only capabilities;
- CI is green.

Qualified legal certification, real payments, external delivery providers, production analytics activation, and commercial launch are not portfolio-completion gates.

## 13. Phase 21 handoff

After 20J, move to Phase 21 rather than spending portfolio time on deferred commercial integrations.

Prioritize model routing, model/prompt registries, evaluation-before-promotion, deterministic-field preservation, citation/source consistency, prompt-injection defenses, cost/latency evaluation, controlled human feedback, and thesis/catalyst/scenario intelligence.

## 14. Return to product mode

A future productization pass starts from [`productization_backlog.md`](productization_backlog.md): choose markets/business model, obtain qualified reviews, refresh provider ADR evidence, complete Phase 19 deployed operations evidence, validate provider sandboxes, integrate through existing adapters/state authorities, perform controlled deployment, then run expanded Phase 22 product-launch validation.
