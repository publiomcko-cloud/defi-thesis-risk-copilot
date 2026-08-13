# Current Agent Handoff — 2026-08-13

Status: **Current development snapshot before Phase 20C**

This file is deliberately time-sensitive. It records the verified project state used to prepare the next implementation session. Always re-check Git, PR, migration, dependency, and CI state before acting if this snapshot is no longer current.

## 1. Snapshot identity

Reviewed source branch:

`agent/v1-phase-20-product-analytics-commercial-readiness`

Verified source head before this memory branch:

`0f0a0db8d21c03b936f3cf5792e0a48113677c10`

Commit:

`chore: remediate dependency security findings`

Memory-review branch:

`agent/project-memory-handoff`

The memory branch was created directly from the verified source head so it includes the complete Phase 20A/20B portfolio refactor and dependency-security correction.

At the snapshot, draft PR #22 for the source Phase 20 branch was open and mergeable. It had not been merged. Verify its current state before any later branch or merge decision.

## 2. Active development profile

The project is currently developed as a **portfolio anchor**, not an actively commercialized SaaS product.

[`../portfolio_profile.md`](../portfolio_profile.md) is the active scope authority. [`../productization_backlog.md`](../productization_backlog.md) preserves real-provider, legal/privacy/tax, billing, production-activation, and commercial-launch work for a future return to product mode.

The portfolio pivot reduces commercial/operational scope only. It does not weaken tenant isolation, authorization, security, migrations, data integrity, recovery, deterministic-risk authority, or rollback requirements.

## 3. Phase status at this snapshot

```text
20A governance/threat/evidence foundation       COMPLETE
20B consent-aware first-party analytics         COMPLETE
20C durable scheduled monitoring                NEXT / REQUIRED
20D in-app notifications                        REQUIRED AFTER INPUT SOURCE
20E secure synthetic delivery adapter           OPTIONAL
20F entitlements + non-billable usage           REQUIRED
20G real billing/provider integration            DEFERRED
20H organization SaaS controls                  REQUIRED AFTER 20F
20I minimal support/privacy/status               REQUIRED / REDUCED
20J portfolio architecture closeout             REQUIRED
Phase 21                                        AFTER 20J
```

20C, 20F, and provider-free portions of 20I are architecturally independent enough to proceed separately, but 20C is the recommended next slice.

## 4. Verified Phase 20B implementation

Alembic head at the reviewed source state is:

`backend/migrations/versions/20260731_0023_add_product_analytics.py`

Migration `0023` creates the Phase 20B analytics/privacy persistence:

- `privacy_preferences` current projection;
- append-only `privacy_preference_decisions`;
- bounded `product_analytics_events`.

Runtime implementation exists under `backend/app/product_analytics/`, including registry, schemas, and service logic.

Implemented behavior includes:

- authenticated individual-user analytics only;
- explicit opt-in and policy-version evidence;
- production collection disabled by default;
- rejection of new affirmative grants when deployment collection is disabled;
- existing stored grants remain withdrawable;
- immutable grant/deny/withdraw decision evidence;
- exactly four approved events: `analysis_completed`, `analysis_failed`, `thesis_saved`, `watchlist_created`;
- bounded code-owned metadata;
- server-owned event emission and idempotency;
- 30-day analytics event retention;
- immediate collection stop and event removal on withdrawal;
- integration with existing Phase 16 account export/deletion authority;
- PostgreSQL concurrency/idempotency coverage;
- accessible Account preference UI.

Production analytics activation remains deferred to future productization review and does not block portfolio development.

## 5. Verified work not yet implemented

The repository/tree review found no Phase 20C schedule runtime or migration after `0023`. In particular, no `monitoring_schedules`/schedule-run implementation exists yet.

The reviewed tree also does not contain the later Phase 20 runtime authorities expected for:

- 20D notification preference/intent persistence;
- 20F versioned entitlement assignments and immutable usage ledger;
- 20G real billing integration;
- 20H portfolio seat/invitation enhancements beyond existing organization foundations;
- 20I new bounded support/privacy-request persistence.

These absences are expected roadmap state, not regressions.

Do not infer implementation from Phase 20A design documents, proposed table names, schemas, or provider scorecards.

## 6. Security/dependency checkpoint

The source head `0f0a0db` completed the latest dependency maintenance:

- `pypdf` `6.14.2 -> 6.15.0`;
- `cryptography` `48.0.1 -> 50.0.0`;
- production `nanoid` override to `3.3.18`;
- supply-chain workflow corrected so an unreached npm audit does not create a misleading missing-file summary failure.

Resolved findings recorded in PR #22:

- `PYSEC-2026-3655`;
- `PYSEC-2026-3656`;
- `PYSEC-2026-3552`;
- `PYSEC-2026-3553`;
- `PYSEC-2026-3554`;
- `GHSA-2v37-7h3g-55p8`.

At that source head, hosted CI, CodeQL, Phase 19 Failure Exercises, Supply Chain Security, Python audit, production npm audit, dependency review, secret scan, repository/config scan, container builds/scans, workflow policy/SBOM, and Vercel preview were green.

Do not assume that dependency audits remain green indefinitely; re-run/verify them at the next implementation checkpoint.

## 7. Next slice: Phase 20C

Authoritative policy is in [`../phase_20_execution_plan.md`](../phase_20_execution_plan.md). Current approved portfolio scope is:

- authenticated user-owned schedules first;
- organization-owned scheduling waits for 20H authority;
- only code-owned watchlist/monitoring targets;
- cadence presets: hourly, six-hourly, daily, weekly;
- minimum cadence: one hour;
- validated IANA timezone and DST behavior;
- maximum five active schedules per user;
- unique occurrence identity from schedule + scheduled time;
- missed runs coalesce to at most one replacement;
- occurrences over 24 hours late are recorded as missed/skipped;
- authorization, quota, capacity, and cost gates are revalidated at dispatch/execution;
- 30-day schedule-run history;
- deletion cancels owned schedules/jobs;
- dispatcher can be disabled as rollback without corrupting history.

20C must reuse Phase 17 durable-job infrastructure rather than inventing a second worker/queue authority.

Required evidence should include at least:

- reversible next migration after `0023`;
- PostgreSQL one-winner due-row claims;
- occurrence idempotency;
- restart survival and worker-loss recovery;
- pause/resume/delete behavior;
- authorization/membership revocation handling;
- quota/capacity/cost denial behavior;
- DST/timezone cases;
- account export/deletion lifecycle integration where applicable;
- backend/PostgreSQL/frontend/browser coverage;
- recovery/rollback and permanent security regression checks.

## 8. Safe defaults that must survive 20C

Preserve:

- `PRODUCT_ANALYTICS_ENABLED=false` in production;
- `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=false` until controlled cutover;
- safe JSON/public retrieval fallback;
- `VAST_DRY_RUN=true`;
- `VAST_REAL_RENTALS_ENABLED=false`;
- server-derived tenant/authorization/plan state;
- Phase 16 lifecycle authority;
- Phase 17 durable-job authority;
- deterministic risk fields as authoritative;
- no wallet/signing/custody/trade execution/personalized financial advice.

## 9. Documentation caveat discovered in this review

The repository has substantial documentation, but `current_state.md` and `development_plan.md` still contain older commercial Phase 20 framing and pre-portfolio status in some sections. They remain valuable detailed/historical sources, but should not override the newer portfolio profile, current Phase 20 execution/evidence files, or verified code state.

This is why the compact memory layer exists.

## 10. Start-of-next-session verification

Before starting 20C or any other slice:

1. read [`PROJECT_MEMORY.md`](PROJECT_MEMORY.md);
2. re-check the current branch/head;
3. re-check PR #22 and whether the Phase 20A/B source work has been merged or superseded;
4. re-check Alembic head — do not blindly assume `0023` if development has advanced;
5. re-check hosted CI/security status;
6. compare code/tree state with this handoff;
7. read the current `portfolio_profile.md`, `phase_20_execution_plan.md`, and `phase_20_evidence_matrix.md`;
8. update this handoff at the next material phase boundary.
