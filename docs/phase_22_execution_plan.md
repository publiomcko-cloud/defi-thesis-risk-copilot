# V1 Phase 22 Execution Plan - Final Release Validation

Status: **ACTIVE - HOLD.** This is a validation and approval phase; it adds no
product capability or migration. On 2026-09-23, repository release controls
were remediated and GitHub recorded a successful Vercel production deployment
of required candidate `abc83d36c115b4122a1a1964fde101fbf9c407e4`. The public
Render backend still reports older commit `6f07ef9`, and no authorized Render
deployment interface is available here. That is a
`BLOCKED_EXTERNAL - RENDER DEPLOYMENT AUTHORITY REQUIRED` hold, not evidence
that the candidate is running on Render.

## Authority And Scope

The governing contract is [future_phase_contracts.md](future_phase_contracts.md)
section 22, with deployment requirements in [deployment.md](deployment.md) and
deferred commercial work in [productization_backlog.md](productization_backlog.md).
Phase 22 may validate the portfolio deployment but may not activate billing,
paid plans, analytics collection, external notifications/helpdesk, paid model
inference, private training, real Vast rentals, or any commercial feature.

The release candidate is the Phase 21 closeout merge:

```text
base / required candidate: abc83d36c115b4122a1a1964fde101fbf9c407e4
branch: agent/v1-phase-22-final-release-validation
alembic head: 20260911_0034
reserved revision: 0027 intentionally absent
```

## Evidence States

| State | Meaning |
| --- | --- |
| `VERIFIED` | Dated, bounded evidence directly confirms the requirement in the named environment. |
| `NOT_APPLICABLE_TO_PORTFOLIO_PROFILE` | The capability is intentionally outside the portfolio deployment. |
| `BLOCKED_EXTERNAL` | A provider, deployed configuration, or external environment prerequisite is unavailable or unverified. |
| `BLOCKED_HUMAN_APPROVAL` | A qualified owner, legal reviewer, or release approver must supply evidence. |
| `DEFERRED_PRODUCTIZATION` | The work is retained for product mode and is not activated by this phase. |
| `FAILED` | Direct evidence contradicts a required release condition. |
| `PENDING` | Work is not yet executed; it is not a positive result. |

External evidence records must include the requirement, environment, date/time,
safe reference, verifier, result, limitations, and rollback path. They never
contain credentials, tokens, cookies, mailbox content, personal data, private
source bodies, or secret-bearing screenshots.

## Workstreams

| Workstream | Required evidence | Current state | Exit condition |
| --- | --- | --- | --- |
| Baseline and schema | Candidate SHA, merged PR #36, one Alembic head, no fabricated `0027`, safe defaults | `VERIFIED` locally on 2026-09-23 | Preserved through final exact-head validation. |
| Repository regression | Full PostgreSQL/backend/frontend/browser/Compose/security/Phase 19 suite and exact-head hosted checks | `PASS` | Fresh local evidence and required hosted categories are green; the Draft PR check view is the authoritative final-SHA record. |
| Public portfolio smoke | HTTPS frontend/demo/status and backend health/readiness/deployment status | `VERIFIED` for bounded unauthenticated endpoints | Re-run only after the candidate is deployed. |
| Deployment provenance | Render and Vercel deployments both identify the candidate SHA | `BLOCKED_EXTERNAL` | Vercel candidate provenance is verified; an authorized Render operator must deploy and safely prove the exact candidate. |
| Production configuration | Read-only provider configuration audit and header/origin/cookie evidence | `BLOCKED_EXTERNAL` | Approved platform access, redacted categorical inventory, and candidate deployment. |
| Supabase auth and SMTP | Custom SMTP plus disposable-account confirmation, recovery, reset, refresh/logout, and MFA evidence | `BLOCKED_EXTERNAL` | Approved SMTP/configuration and safe disposable-account evidence. |
| Tenant and organization isolation | Two disposable users, removal/revocation, knowledge boundary, and lifecycle evidence on candidate deployment | `BLOCKED_EXTERNAL` | Approved disposable identities and candidate deployment. |
| Storage and pgvector | Provider bucket/RLS, pgvector/readiness, rollback rehearsal, and JSON fallback evidence | `DEFERRED_PRODUCTIZATION` | Separate policy/provider approval; do not enable merely for this phase. |
| Worker/provider operations | Trusted worker, alerting, backup/restore, secret rotation, rate-limit rollout, and incident ownership evidence | `BLOCKED_EXTERNAL` / `BLOCKED_HUMAN_APPROVAL` | Provider and named-owner evidence, with isolated drills where approved. |
| GitHub release controls | Branch/ruleset protection, merge gates, security features, and immutable-action enforcement | `VERIFIED` | Active `main-release-gate` ruleset `23890276`, free security features, and native SHA pinning are recorded below. |
| Legal and release approval | Qualified review of terms, privacy, retention, consent, and public claims; release owner approval | `BLOCKED_HUMAN_APPROVAL` | Human evidence stored in the approved private operations system. |

## Remediated Repository Controls

The repository administrator applied active ruleset `23890276`
(`main-release-gate`) to `~DEFAULT_BRANCH` on 2026-09-23. It requires pull
requests, current-head status checks, resolved review threads, and these exact
GitHub Actions contexts: `Backend and PostgreSQL`, `Frontend`, `Docker Compose
Config`, `CodeQL (python)`, `CodeQL (javascript-typescript)`, `Workflow Policy
and SBOM`, `Dependency Review`, `Secret Scan`, `Dependency and Container
Security`, and `Isolated failure exercises`. It blocks ref deletion and
non-fast-forward updates. The required-approval count remains zero because this
is a single-maintainer repository; ordinary direct pushes are still prohibited.

The only bypass is GitHub's predefined repository-admin role in
`pull_request` mode. GitHub reports `current_user_can_bypass` as
`pull_requests_only`: an emergency recovery still requires a pull request and
produces GitHub's bypass/audit trail. Repairing a malformed ruleset remains a
repository-administrator setting action, not an ordinary development bypass.

Dependency graph evidence is available through the repository SBOM endpoint;
Dependabot alerts and security updates, secret scanning, and secret-scanning
push protection are enabled. GitHub Actions native
`sha_pinning_required=true` is enabled, complementing the repository's
full-length action-SHA workflow policy. Generic-pattern and validity-check
secret scanning remain unavailable in the present GitHub feature set and are
`BLOCKED_EXTERNAL - GITHUB PLAN/FEATURE AVAILABILITY`; no scanner exclusion or
weakened rule was added.

## Hard Stops And Rollback

The missing Render candidate deployment prohibits the remaining public
portfolio release validation, real-account testing, production migration
actions, and any commercial-launch claim. No production downgrade, feature
activation, provider purchase, real rental, paid inference, customer email,
payment object, or customer-data test is permitted to work around it.

The deployment recovery path is operator-owned: Vercel already has a successful
candidate deployment record; an authorized Render operator must deploy the
same candidate, record a bounded identifier, and verify safe status plus
health/readiness. If rollback is needed, use the platform's approved deployment
rollback; Alembic downgrade is not production data recovery.

## Completion Model

Phase 22 may report a healthy portfolio deployment separately from commercial
launch approval. `22 PASS` requires every contract gate, including external
provider and qualified human evidence. Until then the result is `22 HOLD`.
The detailed current state and next evidence requirements are in
[phase_22_evidence_matrix.md](phase_22_evidence_matrix.md) and
[phase_22_release_validation.md](phase_22_release_validation.md).
