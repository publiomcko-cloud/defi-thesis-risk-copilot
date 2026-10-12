# Phase 22 Release Validation Record

Status: **22 HOLD.** This record contains bounded validation evidence only. It
does not certify production launch, external providers, legal compliance, or
commercial operation.

## Candidate And Observation

| Field | Value |
| --- | --- |
| Required candidate | `abc83d36c115b4122a1a1964fde101fbf9c407e4` (PR #36 merge) |
| Security-corrected main source revision | `9c9403aa71a52050de7d4a892beff675458386b6` (PR #39 merge); not deployed and not designated as a new release candidate |
| New external deployment candidate | None designated; all historical deployment evidence below remains tied to `abc83d36c115b4122a1a1964fde101fbf9c407e4` |
| Phase 22 branch | `agent/v1-phase-22-final-release-validation` |
| Repository migration head | `20260911_0034` only; `0027` intentionally absent |
| Initial observation time | 2026-09-23T11:42Z |
| Corrective observation time | 2026-09-23T16:43Z |
| Render target | `srv-d9bt2461a83c73bt5vg0` (`defi-thesis-risk-copilot`), existing production web service for this repository, branch `main` |
| Last successful Render deployment before this attempt | `dep-d9jj1mnaqgkc739najsg`, source commit `0c31d7f4598ce66da4f353f2d48c32d49474bb3b` (an ancestor of the candidate); public `/api/deployment/status` reports `6f07ef9` from the configured `DEPLOYMENT_COMMIT` release metadata |
| Render deployment attempt | `dep-db6ghojrjlhs738e933g`, exact candidate `abc83d36c115b4122a1a1964fde101fbf9c407e4`, submitted 2026-10-12; terminal result `update_failed` at 2026-10-12T16:21:41Z |
| Render deployment result | Build succeeded; container startup failed during migration `20260727_0018` because PostgreSQL extension `vector` is not installed in the existing database. No database mutation or retry was made. |
| Public backend evidence | After the failed attempt, `/health`, `/ready`, and `/api/deployment/status` returned HTTPS 200; readiness reported database and RAG index true on the still-serving prior deployment. |
| Public frontend evidence | Canonical Vercel `/`, `/demo`, and `/status` returned HTTPS 200 |
| Vercel provenance result | **VERIFIED:** GitHub deployment `6612919047` records successful Vercel Production deployment of exact candidate `abc83d36` |
| Render provenance result | **HOLD / FAILED ATTEMPT:** exact candidate deployment failed at startup; public endpoint still reports old commit `6f07ef9` |

`6f07ef95b36a0b4cd96c91836c8965004b0d82e7` is the older `Add scheduled
Phase 17 worker` commit and is an ancestor of the candidate by 21 commits.
Health and readiness show that a live service is responsive; they do not
establish that the required release candidate is deployed to Render. Render's
deployment API identifies the target as the repository's production web service
on `main`, using Docker context `.` and `./Dockerfile.backend`. The bounded
startup logs show the database extension prerequisite; they do not justify a
speculative code or configuration change.

## Deployment Inventory

| Component | Observed state | Evidence boundary |
| --- | --- | --- |
| Vercel frontend | GitHub deployment `6612919047` successfully deployed exact candidate `abc83d36` to `Production`; canonical public routes responded 200 | The immutable deployment alias is Vercel-auth protected. The GitHub deployment record, rather than public HTML, establishes commit provenance. |
| Render backend | Service `srv-d9bt2461a83c73bt5vg0` (`defi-thesis-risk-copilot`), source branch `main`; last successful deployment `dep-d9jj1mnaqgkc739najsg` used source commit `0c31d7f4598ce66da4f353f2d48c32d49474bb3b`; candidate deployment `dep-db6ghojrjlhs738e933g` ended `update_failed`; public status reports `6f07ef9` from `DEPLOYMENT_COMMIT` metadata | Candidate build succeeded, but startup failed when migration `20260727_0018` required an uninstalled PostgreSQL `vector` extension. Candidate is not live, so no release-metadata variable correction was made. The database prerequisite needs separate authorization before another attempt. |
| Supabase database/auth | Backend says database connected and authentication enabled | Provider configuration, migration head, SMTP, redirects, and policies are externally unverified. |
| Object storage | No public activation evidence | Default-disabled repository capability; provider policy and RLS evidence absent. |
| pgvector | The existing database lacks PostgreSQL `vector`, as reported by startup migration `20260727_0018` | The primary path remains disabled; extension provisioning for migration startup is a separate database prerequisite and does not establish primary cutover approval. |
| Trusted worker | Candidate-specific Phase 17 worker run `35878131521` on `abc83d36` timed out; later automatic cron run `38288308792` on main `9c9403aa` completed at workflow level | The candidate run timed out in `POST /internal/workers/v1/claim` after 20 seconds. The later run used the existing `schedule` event and succeeded as a GitHub job in `production-worker`; it does not establish deployed-candidate provenance or whether a job was claimed. No manual dispatch or candidate-specific rerun was made. |
| SMTP/email | No configuration evidence | Custom SMTP is mandatory for product launch and remains blocked. |
| Monitoring/alerts | Local/isolated foundation only | Receiver, pager, escalation, and owner evidence absent. |
| Backup/restore | Runbook/template only | Provider backup, restore drill, RPO/RTO, and owners absent. |
| Notifications/helpdesk/billing | No activation evidence | Deferred productization; no provider was selected or enabled. |
| Model provider/Vast | Public status reports provider disabled; Vast disabled with dry-run posture | No paid inference, real training, or real rental was performed. |

## Safe Deployment Posture Observed

The bounded public status response confirms production environment, public demo
mode, authentication enabled, database connectivity, synthesis disabled, model
provider disabled, semantic RAG disabled, and Vast disabled/dry-run. A read-only
Render environment audit inspected categories only; no values were recorded.
The target had 25 direct environment variables and zero attached environment
groups. The public endpoint did not expose the listed flags, so their values
below come from that Render audit rather than repository defaults.

| Configuration key/category | Observed category |
| --- | --- |
| `APP_ENV` | `production` |
| `PUBLIC_DEMO_MODE` | enabled |
| `AUTH_ENABLED` | enabled |
| `AUTH_PROVIDER` | present |
| `FRONTEND_ORIGIN` | present |
| `PRODUCT_ANALYTICS_ENABLED` | absent |
| `SCHEDULE_DISPATCH_ENABLED` | absent |
| `KNOWLEDGE_STORAGE_ENABLED` | absent |
| `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED` | absent |
| `LLM_SYNTHESIS_ENABLED` | disabled |
| `VAST_DRY_RUN` | enabled |
| `VAST_REAL_RENTALS_ENABLED` | disabled |
| Monitoring/synthetic flags | none configured |

No provider, analytics, scheduling, storage, pgvector-primary, paid inference,
or real Vast activation was made. The absent pgvector-primary flag is distinct
from the PostgreSQL `vector` extension prerequisite required by the candidate
migration at startup.

Repository configuration retains fail-closed constraints: production analytics,
schedule dispatch, and pgvector-primary are rejected by settings validation;
production private storage requires scanning and server credentials; production
authentication requires a server BFF audit secret; and production worker API
requires a server token pepper. These are architecture controls, not evidence of
the live provider configuration.

## Scheduled Worker Evidence

GitHub scheduled workflow `35878131521` checked out exact `main` candidate
`abc83d36` and failed only in `Claim and process one durable job` at
2026-09-23T14:59Z. The bounded observed failure is `TimeoutError: The read
operation timed out` from the worker runner's 20-second claim request. The
known credential remains masked; no database URL, credential, job payload, or
raw sensitive response was retained. The candidate-specific run was not
manually rerun because the 2026-10-12 Render candidate deployment failed at
startup and the public service still reports `6f07ef9`.

After PR #39 merged, GitHub automatically ran the existing Phase 17 Scheduled
Worker cron as workflow run `38288308792` at `2026-10-12T18:03:06Z`, event
`schedule`, on main SHA `9c9403aa71a52050de7d4a892beff675458386b6`. Its
`process-one-job` job completed successfully at `18:03:31Z` in the
`production-worker` environment. The workflow checks out `main` and invokes
`python -m app.jobs.worker_runner --once`. This run was not manually dispatched
or requested as a Phase 22 test. Its workflow-level success does not establish
that a durable job was claimed, nor does it establish provenance for the
undeployed candidate `abc83d36`. No raw logs or job payload were inspected or
retained. This automatic run does not replace the historical candidate timeout
or clear the worker/deployment evidence gate.

## Render Candidate Deployment Failure

The exact reviewed candidate deployment `dep-db6ghojrjlhs738e933g` built
successfully, then exited with status 1 during container startup. The startup
path ran Alembic migrations and failed on `20260727_0018` with the explicit
prerequisite that a database administrator install PostgreSQL extension
`vector`. Render marked the deployment `update_failed` at
`2026-10-12T16:21:41Z`. The production database was not modified, the
deployment was not retried, no environment variables were changed, and no
runtime code or migration was edited. The required external action is an
authorized DBA provision of this extension, followed by a separately reviewed
deployment attempt.

After failure, public `/health` returned HTTPS 200/healthy, `/ready` returned
HTTPS 200 with database and RAG index ready, and `/api/deployment/status`
returned HTTPS 200 with the expected safe feature posture. It still reported
`6f07ef9`; these responses describe the prior deployment, not the candidate.

## Local Exact-Head Regression

Status: **VERIFIED locally on 2026-09-23; required hosted checks passed on
`d89b5bb92bf66029d1ba696f34951ead67130b40`.**
The Phase 22 working tree contained documentation-only changes above the
reviewed `abc83d36` implementation. The following isolated commands completed
with exit status 0 and do not prove a deployed/provider condition:

- clean `npm ci`; backend dependency installation and `pip check`; Python
  compilation; and the static safe-default assertion;
- fresh PostgreSQL 16/pgvector database preflight, zero-to-`20260911_0034`
  migration, full PostgreSQL-enabled backend `pytest`, and explicit
  `0034 -> 0033 -> 0034` migration cycle;
- deterministic public-corpus evaluation (`7/7`, 100% precision@1 and recall,
  zero citation issues) and local public-demo runtime preparation;
- frontend type check, BFF/MFA/security/accessibility/phase contracts,
  production build, and browser E2E;
- development and production Compose rendering;
- workflow/lockfile/exception policy checks, source-lockfile SBOM generation,
  `pip-audit`, production `npm audit`, full-history Gitleaks (344 commits),
  Trivy filesystem scan, and HIGH/CRITICAL scans of fresh backend/frontend
  images, all clean;
- the isolated Phase 19 exercise catalog, including load metrics, admission,
  worker-loss/retry recovery, outage recovery, migration rollback, and negative
  authorization checks.

Local CodeQL is not installed in this validation environment. Required hosted
checks passed on `d89b5bb`: Backend and PostgreSQL, Frontend, Docker Compose,
CodeQL Python/JavaScript, Workflow Policy and SBOM, Dependency Review, Secret
Scan, Dependency and Container Security, isolated Phase 19 failure exercises,
and Vercel preview. The Draft PR check view is the authoritative final-SHA
record for documentation-only status updates.

### Historical hosted results before the dependency correction

On documentation head `2da78205fb005d3b9c566642428c8e11fe792f51`, nine of the
ten required checks passed: Backend and PostgreSQL, Frontend, Docker Compose
Config, both CodeQL languages, Workflow Policy and SBOM, Dependency Review,
Secret Scan, and Isolated failure exercises. `Dependency and Container
Security` failed because `pip-audit` found eight known advisories for unchanged
dependency `pypdf` 6.16.1. This documentation-only phase does not change runtime
dependencies; the current-head security gate remains on hold for a separately
reviewed dependency correction. No Vercel status/deployment was recorded for
this documentation head. The existing successful Vercel Production deployment
`6612919047` remains tied to runtime candidate `abc83d36`.

The same required security check failed again on documentation head
`dd646ecfb4ae6a553cb874d94ebea4a10838726b`; the other nine required contexts
passed. No Vercel status/deployment was emitted for that documentation head.

### Subsequent dependency security correction and Phase 22 reconciliation

On 2026-10-12, PR #39 independently reviewed and corrected the dependency
findings. It upgraded backend `pypdf` from 6.16.1 to 6.20.0 and frontend
`next` 15.5.25 to 15.5.27, `sharp` 0.35.4 to 0.35.5, and `source-map-js`
1.2.1 to 1.2.2. All ten required branch-protection contexts passed on exact PR
head `c6d7cfdce8d81170184ef995dc8ea832f86ff1d9`. PR #39 was marked ready and
merged through the normal protected workflow as merge commit
`9c9403aa71a52050de7d4a892beff675458386b6`, with first parent
`abc83d36c115b4122a1a1964fde101fbf9c407e4` and second parent
`c6d7cfdce8d81170184ef995dc8ea832f86ff1d9`.

The Phase 22 documentation branch was then reconciled with updated `main`.
Its historical candidate remains `abc83d36c115b4122a1a1964fde101fbf9c407e4`;
the security-corrected `main` commit is an undeployed source revision, not a
new or replacement deployment candidate. No deployment, database action,
migration change, provider activation, or worker rerun followed the merge.
All ten required exact-head contexts passed on the reconciled PR #37 revision
listed below. PR #37 remains open and draft. Its current branch head and check
results are maintained in the GitHub PR/check records.

The post-merge push workflows on `9c9403aa71a52050de7d4a892beff675458386b6`
completed successfully for backend/PostgreSQL, frontend, Compose, CodeQL for
Python and JavaScript/TypeScript, workflow policy/SBOM, secret scan, and
dependency/container security. The push-event `Dependency Review` job was
skipped because that required context runs for pull requests; it passed on the
exact PR #39 head before merge. No scanner thresholds or branch rules changed.
The external release blocker remains **`BLOCKED_EXTERNAL — PGVECTOR EXTENSION
PROVISIONING AUTHORIZATION REQUIRED`**. The production database was not changed.

On reconciled PR #37 head `5d1003b701df53d22fba85015e1bebb971047892`, all ten
required exact-head contexts passed: Backend and PostgreSQL, Frontend, Docker
Compose Config, CodeQL (python), CodeQL (javascript-typescript), Workflow Policy
and SBOM, Dependency Review, Secret Scan, Dependency and Container Security,
and Isolated failure exercises. The Vercel preview integration also succeeded.
The PR remained open and draft. A subsequent evidence-only documentation
commit advances the branch; the current head's own exact check results are
authoritative in the GitHub PR record.

## Auth, Isolation, And Storage Gates

No candidate deployment plus owner-approved disposable test identities were
available. Consequently signup/confirmation, recovery/reset, refresh/logout,
MFA, two-user resource isolation, organization membership removal, organization
knowledge metadata, and storage/RLS probes were not run. They are
`BLOCKED_EXTERNAL`, not inferred from local tests or past hosted CI.

No custom SMTP configuration or delivery evidence was supplied. This is
`BLOCKED_EXTERNAL - CUSTOM SMTP PROVIDER/CONFIGURATION REQUIRED` for the full
product-release gate. Default/development mail behavior is not equivalent.

Private durable knowledge and pgvector primary remain
`DEFERRED_PRODUCTIZATION`. JSON fallback remains the approved portfolio posture;
no production cutover, bucket policy, object operation, RLS probe, or provider
restore was attempted.

## Operations, Security, And Controls

The repository has immutable workflow pins, hosted CI/security checks, isolated
Phase 19 failure exercises, restore/secret runbooks, and guarded rate-limit,
worker, storage, and provider paths. These are repository evidence only.

Actual Render/Vercel/Supabase configuration, browser cookie attributes,
CORS/BFF origins, shared-rate-limit rollout, worker connectivity, telemetry,
alert delivery, incident ownership, backup/restore, and secret rotation require
approved external or human evidence. They remain `BLOCKED_EXTERNAL` or
`BLOCKED_HUMAN_APPROVAL` as listed in the matrix.

The 2026-09-23 corrective GitHub REST audit verified active repository ruleset
`23890276` for `main`. It requires pull requests, resolved review threads,
current-head checks, blocks ref deletion and non-fast-forward updates, and
requires the ten actual GitHub Actions contexts named in the evidence matrix.
The single-maintainer recovery mechanism is deliberately restricted to the
repository-admin role through a pull request; GitHub reports
`current_user_can_bypass=pull_requests_only`.

Native Actions immutable-SHA enforcement is enabled and complements the
repository's fully pinned workflow source policy. The dependency-graph SBOM
endpoint returned 200; Dependabot alerts/security updates, secret scanning, and
push protection are enabled. Generic-pattern and validity-check scanning are
not available through the current GitHub feature set, so they remain
`BLOCKED_EXTERNAL - GITHUB PLAN/FEATURE AVAILABILITY`, with no rule exclusion
or scanner suppression.

## Legal Review Checklist

Status: **BLOCKED_HUMAN_APPROVAL - QUALIFIED HUMAN REVIEW REQUIRED.**

Before commercial launch, a qualified reviewer must record conclusions in the
approved private evidence system for terms, privacy notice, retention/deletion,
consent/cookies, financial-research disclaimers, acceptable use, subprocessors
and transfers, security/availability claims, support/status claims, billing and
tax statements, and jurisdiction-specific obligations. This repository records
no legal advice, identities, contact details, or private review material.

Repository copy scanning found no affirmative primary-document claim that this
portfolio is production-ready, SLA-backed, certified, compliant, or offering
paid billing/provider activation. That limited scan does not replace deployed
UI review or qualified legal review.

## Supported Claims And Prohibited Claims

Supported now: the public portfolio is reachable; bounded health/readiness and
public demo/status routes responded successfully on the observation date; the
repository retains fail-closed defaults and completed architecture evidence.

Not supported: Render candidate deployment provenance, real-user auth/email
results, tenant/organization isolation on the candidate, provider
backup/restore, centralized telemetry/pager operation, legal approval,
commercial launch, production storage/RLS, real Vast/model execution, or
paid/external capability activation.

## Decision Matrix

| Decision | Result | Basis |
| --- | --- | --- |
| Repository / Architecture Regression | `VERIFIED` on PR #37 exact head `5d1003b` | The historical `pypdf` finding was corrected in PR #39; all ten required contexts passed on its exact head `c6d7cfd` and also on reconciled PR #37 head `5d1003b`. Any later PR #37 head requires fresh exact-head checks; the GitHub PR record identifies the current SHA and result. |
| Public Portfolio Deployment Validation | `HOLD` | Vercel candidate provenance is verified; the Render candidate build succeeded but startup failed because the existing database lacks the required `vector` extension. |
| External Provider / Operations Gates | `HOLD` / `DEFERRED` | SMTP, provider config, worker, monitoring, backup/restore, and rate-limit evidence are unavailable; storage/pgvector/billing remain deferred. |
| GitHub Release Controls | `VERIFIED` for PR #39 and PR #37 head `5d1003b`; Phase 22 remains on hold | Active `main` ruleset, native SHA pinning, dependency-graph evidence, Dependabot, secret scanning, and push protection remain enabled; PR #39 passed all ten required exact-head checks and merged normally. PR #37 passed all ten on exact head `5d1003b`; any subsequent head must pass its own exact checks. |
| Qualified Legal / Privacy / Commercial Review | `HOLD` | Qualified human evidence is absent. |
| Commercial Production Launch Approval | `NOT APPROVED` | Mandatory provenance, external, operational, and human gates remain unsatisfied. |

## Resume Criteria And Rollback

Before resuming public deployment validation, an authorized database
administrator must provision the PostgreSQL `vector` extension required by
`20260727_0018` under blocker **`BLOCKED_EXTERNAL — PGVECTOR EXTENSION
PROVISIONING AUTHORIZATION REQUIRED`**. Then an authorized operator can consider a new deployment of
the exact reviewed candidate and provide a successful bounded deployment
identifier plus endpoint provenance. Vercel's exact-candidate deployment is
already recorded in GitHub. The platform rollback path, if needed, is a
deployment rollback to the last approved build; it must not use a production
database downgrade as recovery.

After Render provenance is verified, the remaining tests require approved
disposable identities, read-only platform configuration access, custom SMTP
approval, external backup/restore evidence, named operational ownership, and
qualified legal/privacy/commercial review. No activation is authorized by this
document.
