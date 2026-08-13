# Phase 20 Evidence Matrix

Status: **In Progress — portfolio profile active**

Current scope is defined by [`portfolio_profile.md`](portfolio_profile.md) and [`phase_20_execution_plan.md`](phase_20_execution_plan.md). Requirements intentionally deferred from the portfolio are preserved in [`productization_backlog.md`](productization_backlog.md).

| Slice | Portfolio status | Evidence state |
| --- | --- | --- |
| 20A | Complete | Governance, threat model, taxonomy, provider-decision and data-model foundations exist |
| 20B | Complete | Migration `0023`, consent-aware first-party analytics, lifecycle integration, PostgreSQL concurrency tests, browser coverage and hosted implementation checks passed before the portfolio-doc refactor |
| 20C | Planned / required | Durable scheduling, DST, one-winner claims, Phase 17 jobs and lifecycle evidence needed |
| 20D | Planned / required | In-app preferences, intents, duplicate suppression, tenant and browser evidence needed |
| 20E | Optional | Synthetic/provider-neutral delivery demonstration only |
| 20F | Planned / required | Versioned entitlements and non-billable usage/reconciliation evidence needed |
| 20G | Deferred | Not required for portfolio completion; preserved for future productization |
| 20H | Planned / required | Invitations, seats, ownership and PostgreSQL concurrency evidence needed |
| 20I | Planned / required, reduced | First-party bounded support/privacy/status evidence needed |
| 20J | Planned / required | Portfolio architecture closeout |

## Phase 20B checkpoint

Phase 20B is implementation-complete for the portfolio profile. Commit `a7bcd42` contains the deployment-disabled consent correction and passed the required implementation validation at that checkpoint.

Production analytics remains disabled. Its later activation is a productization task rather than a Phase 20 portfolio blocker.

## Current branch maintenance

The documentation-only portfolio refactor triggered fresh hosted checks on 2026-08-13. CI, CodeQL, Phase 19 failure exercises, dependency review, secret scan, workflow policy and SBOM checks pass. The Python dependency audit now reports newly known issues in existing dependencies that were not changed by this documentation refactor.

Dependency maintenance and a green rerun are required before this PR should be merged.

## Next functional checkpoint

After dependency maintenance is green, 20C is the next recommended required slice. It must prove durable user-owned schedules, code-owned targets, bounded cadence/timezone behavior, PostgreSQL concurrency/idempotency, Phase 17 job integration, missed-run handling, authorization/quota/cost revalidation, lifecycle cleanup, rollback and browser coverage.

## Portfolio closeout

Phase 20 becomes **Complete — Portfolio Profile** after required 20C, 20D, 20F, 20H, reduced 20I and 20J evidence passes, optional work is accurately labeled, deferred work remains documented rather than falsely completed, no high/critical security regression remains, dependency/security checks are green, migrations and rollback are tested, public feature flags are safe, and CI is green.
