# V1 Phase 22 Execution Plan - Final Release Validation

Status: **ACTIVE - HOLD.** This is a validation and approval phase; it adds no
product capability or migration. On 2026-10-12 the exact reviewed candidate
`abc83d36c115b4122a1a1964fde101fbf9c407e4` was submitted to the identified
production Render backend. Its build succeeded, but startup failed while
applying migration `20260727_0018`: the existing database does not have the
required PostgreSQL `vector` extension. The old deployment remains responsive
and reports `6f07ef9`; the candidate is not running on Render. This is a
`22 HOLD` pending an externally authorized database prerequisite and a later
successful deployment/provenance check.

## Authority And Scope

The governing contract is [future_phase_contracts.md](future_phase_contracts.md)
section 22, with deployment requirements in [deployment.md](deployment.md) and
deferred commercial work in [productization_backlog.md](productization_backlog.md).
Phase 22 may validate the portfolio deployment but may not activate billing,
paid plans, analytics collection, external notifications/helpdesk, paid model
inference, private training, real Vast rentals, or any commercial feature.

The **original Phase 22 deployment candidate** is the Phase 21 closeout merge.
All historical Vercel and Render deployment evidence in this plan refers to
that SHA:

```text
base / required candidate: abc83d36c115b4122a1a1964fde101fbf9c407e4
branch: agent/v1-phase-22-final-release-validation
alembic head: 20260911_0034
reserved revision: 0027 intentionally absent
```

PR #39 later merged a separately reviewed dependency security correction as
`9c9403aa71a52050de7d4a892beff675458386b6`. This is a security-corrected
repository source revision only; it has not been deployed and is not designated
as a replacement release candidate. No new external deployment candidate has
been selected. The original candidate's deployment failures and evidence remain
in force.

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
| Repository regression | Full PostgreSQL/backend/frontend/browser/Compose/security/Phase 19 suite and exact-head hosted checks | `PENDING` for the reconciled Phase 22 documentation head | Historical exact-head failures on `2da7820` and `dd646ec` remain recorded. PR #39 resolved the dependency findings; all ten required checks passed on its exact head `c6d7cfdce8d81170184ef995dc8ea832f86ff1d9`. Rerun all ten on the reconciled Phase 22 head before recording this gate as verified. |
| Public portfolio smoke | HTTPS frontend/demo/status and backend health/readiness/deployment status | `VERIFIED` for bounded unauthenticated endpoints on the currently serving deployment | Render `/health`, `/ready`, and `/api/deployment/status` returned 200 after the failed candidate attempt; this does not prove candidate provenance. |
| Deployment provenance | Render and Vercel deployments both identify the candidate SHA | `FAILED` for the attempted Render candidate; Vercel `VERIFIED` | Render build succeeded but startup failed at migration `20260727_0018` because the existing database lacks `vector`; do not retry until the database prerequisite is handled under separate authorization. |
| Production configuration | Read-only categorical configuration audit and header/origin/cookie evidence | `VERIFIED` for the authorized Render categorical inventory; remaining evidence `BLOCKED_EXTERNAL` | Render service metadata and safe flag categories are recorded in the release validation record; other platform and browser-level configuration remains unverified. |
| Supabase auth and SMTP | Custom SMTP plus disposable-account confirmation, recovery, reset, refresh/logout, and MFA evidence | `BLOCKED_EXTERNAL` | Approved SMTP/configuration and safe disposable-account evidence. |
| Tenant and organization isolation | Two disposable users, removal/revocation, knowledge boundary, and lifecycle evidence on candidate deployment | `BLOCKED_EXTERNAL` | Approved disposable identities and candidate deployment. |
| Storage and pgvector | Provider bucket/RLS, pgvector/readiness, rollback rehearsal, and JSON fallback evidence | `DEFERRED_PRODUCTIZATION` | Separate policy/provider approval; do not enable merely for this phase. |
| Worker/provider operations | Trusted worker, alerting, backup/restore, secret rotation, rate-limit rollout, and incident ownership evidence | `BLOCKED_EXTERNAL` / `BLOCKED_HUMAN_APPROVAL` | Provider and named-owner evidence, with isolated drills where approved. |
| GitHub release controls | Branch/ruleset protection, merge gates, security features, and immutable-action enforcement | `VERIFIED` for PR #39 merge; Phase 22 remains on hold | Ruleset `23890276` remains active and unchanged. PR #39 merged normally after all ten required checks passed on exact head `c6d7cfd`; the reconciled Phase 22 head must also pass all ten checks. |
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

The failed Render candidate deployment prohibits the remaining public
portfolio release validation, real-account testing, production migration
actions, and any commercial-launch claim. The bounded logs identify the
external prerequisite: an authorized database administrator must provision
the PostgreSQL `vector` extension required by migration `20260727_0018` before
a later deployment attempt can be considered. No database change, retry,
production downgrade, feature activation, provider purchase, real rental,
paid inference, customer email, payment object, or customer-data test was made
to work around the failure.

The deployment recovery path is operator-owned: Vercel has a successful
candidate deployment record. The existing Render deployment attempt is
`dep-db6ghojrjlhs738e933g` and failed at startup. After the database prerequisite
is separately authorized and completed, an authorized operator can consider a
new exact-candidate deployment, record its bounded identifier, and verify safe
status plus health/readiness. If rollback is needed, use the platform's
approved deployment rollback; Alembic downgrade is not production data
recovery.

## Completion Model

Phase 22 may report a healthy portfolio deployment separately from commercial
launch approval. `22 PASS` requires every contract gate, including external
provider and qualified human evidence. Until then the result is `22 HOLD`.
The detailed current state and next evidence requirements are in
[phase_22_evidence_matrix.md](phase_22_evidence_matrix.md) and
[phase_22_release_validation.md](phase_22_release_validation.md).
