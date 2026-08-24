# Phase 20F Entitlements and Non-Billable Usage Approval Decision

Status: **Approved for portfolio implementation and validation; commercial/billing semantics remain explicitly unapproved and deferred**

Recorded: **2026-08-21**

Decision owner: **Project owner**

This decision closes the project-owner approval gate needed to begin the selected Phase 20F portfolio slice. It authorizes implementation of versioned server-owned entitlements and non-billable usage metering only within the active portfolio profile. It does not authorize real billing, prices, provider subscription authority, paid plans, finance/legal retention policy, or other commercial launch semantics.

## 1. Approved scope

Phase 20F is approved only as a portfolio/non-billable architecture slice.

The approved implementation scope is:

- immutable/versioned server-owned plan and entitlement architecture;
- `free-v1` as the initial authoritative catalog candidate;
- shadow-first entitlement resolution and comparison against existing quota/policy decisions;
- existing quota and safety authorities retained as rollback authority;
- immutable non-billable usage events for the selected portfolio usage units;
- idempotent meter points that count only successful authoritative outcomes;
- retry/recovery behavior that cannot double-meter;
- immutable linked reversals/adjustments for corrections;
- account lifecycle/export integration appropriate to this non-billable portfolio slice;
- migration, PostgreSQL concurrency, rollback, failure, recovery, tenant-isolation, browser/API and security evidence required by the Phase 20 portfolio definition of done.

## 2. Approved plan boundary

The initial catalog candidate is:

```text
free-v1
```

Its portfolio limits remain those already selected in `portfolio_profile.md` and `phase_20_execution_plan.md`:

- 25 analyses per day;
- 100 simulations per day;
- 100 options analyses per day;
- 100 market-data fetches per day;
- 50 active saved theses;
- 25 active watchlists;
- 5 active schedules.

An optional synthetic/test-only preview plan may exist only if needed to prove versioning or resolver behavior. It must have no public price, purchase path, billing-provider linkage, or commercial claim.

## 3. Shadow-first authority

New Phase 20F entitlements begin in shadow mode.

During the Phase 20F implementation and parity-validation stage:

- existing `usage_quotas`, resource-count checks, `UserModel.plan`, server settings, Phase 17 capacity/cost controls, and Phase 19 safety/rate-limit controls remain authoritative for admission and rollback;
- the new entitlement resolver may compute and record a server-owned shadow decision for comparison;
- a mismatch must be observable through bounded operational evidence and tests, not silently change access;
- unknown, missing, invalid, or corrupt entitlement state must never produce unlimited access;
- the new entitlement domain must not weaken any existing safety, authorization, capacity, cost, storage, retention, or rate-limit control.

Any later change from shadow comparison to enforcement requires implementation evidence and must preserve a documented rollback to the existing authorities.

## 4. Approved subject scope

Initial effective Phase 20F semantics are for authenticated individual users.

Organization entitlement, seat, invitation, and organization assignment semantics remain deferred to Phase 20H.

The schema may be designed so future organization subjects can be represented safely, but Phase 20F must not activate organization entitlement semantics or invent 20H authority prematurely.

Anonymous demo policy remains server-owned and cannot be upgraded through an entitlement assignment.

## 5. Approved non-billable usage units

Only these portfolio usage units are approved for active Phase 20F metering:

```text
usage.analysis.completed.v1
usage.simulation.completed.v1
usage.options.completed.v1
usage.schedule.run_completed.v1
```

Other candidate units in `phase_20_usage_entitlement_registry.md` remain unapproved for Phase 20F runtime metering.

In particular, Phase 20F must not activate billing treatment or metering for market-data fetches, notification delivery, storage byte-days, organization seat-days, compute seconds, or model-provider requests unless a later explicit decision approves them.

## 6. Meter semantics

Usage counts only successful authoritative outcomes.

Approved meter points:

- `usage.analysis.completed.v1`: one successfully persisted/completed report/result lineage;
- `usage.simulation.completed.v1`: one successfully completed deterministic simulation operation;
- `usage.options.completed.v1`: one successfully completed options-analysis operation;
- `usage.schedule.run_completed.v1`: one successfully completed schedule occurrence after the authoritative Phase 17/Phase 20C completion path.

The following must record zero original usage:

- failed actions;
- rejected actions;
- cancelled actions;
- quota-denied actions;
- authorization-denied actions;
- incomplete/partial actions;
- abandoned or dead-letter executions that never reach the approved successful meter point.

Retries, lease loss, worker recovery, replay, duplicate requests, and repeated observation of the same logical successful source must not create a second original usage event.

## 7. Idempotency and corrections

Original usage events are immutable.

Required invariants include:

- server-owned quantity and subject identity;
- deterministic/versioned usage-unit identity;
- database uniqueness at the logical meter boundary, including `(unit_key, idempotency_key)` or an equivalent stronger constraint;
- source lineage sufficient to reconcile a usage event with its authoritative product outcome;
- retries/recovery cannot double-meter;
- analytics IDs, browser values, JWT plan labels, or provider callbacks are not usage authority;
- quota counters are not mutated by usage reconciliation.

Corrections use immutable linked reversals or adjustments. Existing original rows are not edited in place to change consumed quantity.

## 8. Separation of concerns

Phase 20F usage and entitlement state remains separate from:

- network rate limiting;
- existing product quota counters;
- Phase 17 capacity and provider-cost controls;
- Phase 19 operational/security telemetry;
- product analytics;
- notification delivery state;
- future billing-provider receipts or subscription state.

No client-controlled plan, entitlement, usage unit, quantity, subject, source, or meter key may grant access or create trusted usage evidence.

## 9. Explicitly deferred/unapproved semantics

The following remain explicitly unapproved and outside Phase 20F:

- real billing;
- prices or public commercial plan presentation;
- checkout, payment, invoicing, refunds, trials, grace periods, or taxes;
- billing-provider customer/subscription state as entitlement authority;
- provider subscription reconciliation;
- paid-plan activation;
- finance/legal evidence-retention requirements;
- legal-hold policy;
- commercial retention terms;
- organization entitlement/seat semantics before Phase 20H;
- real Phase 20G billing behavior.

These remain in the productization backlog or later explicitly approved phases.

## 10. Approval precedence

Within the active portfolio profile, this decision resolves the Phase 20A registry rows and proposed `0026` review blockers only to the minimum extent necessary for the selected Phase 20F non-billable implementation above.

Where older Phase 20A documents still label all candidate Phase 20F plan, entitlement, usage, or migration semantics as `Blocked`, this decision supersedes that placeholder status only for the explicitly approved portfolio subset in this document.

All broader commercial, finance, privacy/legal, provider, organization, storage, external-delivery, or billing semantics remain blocked unless separately approved.

## 11. Implementation evidence still required

This approval makes Phase 20F eligible to implement; it does not mark the phase complete.

Phase 20F must still produce and validate:

- a reviewed reversible successor to proposed migration `0026`;
- immutable/versioned plan and entitlement definitions;
- safe effective assignment semantics for the approved user scope;
- shadow resolver/parity comparison and safe fallback;
- the four approved non-billable usage meter points;
- PostgreSQL uniqueness/concurrency evidence for first assignment/resolution and usage idempotency;
- actual retry/lease-loss/recovery/replay evidence proving no double-metering;
- reversal/adjustment invariants;
- lifecycle/export/deletion integration without inventing commercial retention authority;
- API/UI surfaces only where they improve portfolio evidence, with no client-controlled authorization state;
- migration upgrade/downgrade/upgrade checks;
- backend, PostgreSQL, frontend/browser, Compose, CodeQL, supply-chain, security and existing regression checks;
- documentation that distinguishes shadow, enforced, disabled, synthetic, and deferred behavior accurately.

## 12. Final owner decision

The project owner approves the following statement as the governing Phase 20F implementation decision:

> **Approve Phase 20F only as a portfolio/non-billable architecture slice.** `free-v1` is the initial authoritative catalog candidate; new entitlements begin shadow-first; existing quotas remain rollback/safety authority; usage measures only successful completed analysis, simulation, options, and schedule outcomes; retries do not double-meter; corrections use immutable reversals; organization entitlement semantics remain deferred to 20H; real billing, prices, provider subscription state, finance/legal retention, and commercial plan semantics remain explicitly unapproved/deferred.

Therefore Phase 20F implementation is eligible to begin on `agent/v1-phase-20f-entitlements-usage` under this bounded approval.