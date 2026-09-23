# Phase 22 Evidence Matrix

Status: **ACTIVE - HOLD.** Evidence is intentionally separated between direct
repository/public checks and provider or human prerequisites. GitHub controls
and Vercel candidate provenance are verified; the Render candidate deployment
is blocked by unavailable deployment authority.

Candidate: `abc83d36c115b4122a1a1964fde101fbf9c407e4` (PR #36 merge)

| Gate | State | Environment / dated safe evidence | Limitation and required next step |
| --- | --- | --- | --- |
| Repository baseline | `VERIFIED` | Phase 22 began at merged PR #36 commit `abc83d36` on 2026-09-23; the Phase 22 working tree adds validation documentation only. | Must remain the reviewed implementation base of the Phase 22 PR. |
| Migration lineage | `VERIFIED` | Local `alembic heads` returned only `20260911_0034`; revisions `0030` through `0034` are linear; `0027` is absent. | Does not inspect the production database. |
| Static safe defaults | `VERIFIED` | `Settings` defaults keep analytics, schedule dispatch, pgvector primary, real Vast rentals, and synthesis disabled. | The public status endpoint exposes only part of deployed configuration. |
| Repository regression | `VERIFIED` | 2026-09-23 fresh PostgreSQL/pgvector database: preflight, zero-to-`0034` migration, full `pytest`, `0034 -> 0033 -> 0034`, corpus evaluation, runtime preparation, frontend type/contracts/build/browser E2E, Compose render, supply-chain checks, clean image scans, and isolated Phase 19 catalog all exited 0. Hosted required categories passed on `88a4cdf`; the final documentation SHA is verified in Draft PR #37. | Local/hosted regression evidence never establishes deployed/provider state. |
| Backend health/readiness/docs | `VERIFIED` | 2026-09-23T17:09Z public `GET /health`, `/ready`, and `/docs` each returned HTTPS 200; readiness reported database and RAG index true. | These safe endpoints do not establish candidate provenance, migration head, backup, or tenant boundaries. |
| Backend deployment status | `BLOCKED_EXTERNAL` | 2026-09-23T17:09Z public `GET /api/deployment/status` returned HTTPS 200 and safe production/public-demo/auth/database/disabled-provider fields, but commit was `6f07ef9`. A second authority audit found no Render CLI/session, API integration/credential, deploy hook, repository webhook, or available GitHub App-installation interface. | `6f07ef9` is an ancestor, not candidate `abc83d36`; an authorized operator must deploy and prove the candidate. |
| Vercel candidate provenance | `VERIFIED` | GitHub deployment `6612919047` for exact SHA `abc83d36` completed `success` in Vercel `Production` at 2026-09-23T11:35:12Z. Canonical `/`, `/demo`, and `/status` each returned HTTPS 200 again at 17:09Z. | The public canonical routes do not themselves disclose a commit; GitHub's Vercel deployment record is the provenance evidence. |
| Render/Vercel configuration inventory | `BLOCKED_EXTERNAL` | No approved Render/Vercel configuration interface or CLI session is available in this validation environment. | Read-only categorical audit after candidate deployment; never record values. |
| Supabase auth configuration | `BLOCKED_EXTERNAL` | Public status says authentication is enabled. Supabase provider, verified-email, redirects, SMTP, cookie, and service-role configuration are not publicly inspectable. | Approved read-only Supabase audit. |
| SMTP and email delivery | `BLOCKED_EXTERNAL` | No custom SMTP provider/configuration or disposable mailbox evidence supplied. | Owner-approved custom SMTP and safe disposable-account flows. |
| Deployed auth, recovery, MFA | `BLOCKED_EXTERNAL` | No approved disposable accounts or candidate deployment. | Candidate deployment plus manually controlled test identities; remove identities afterward. |
| Two-user and organization isolation | `BLOCKED_EXTERNAL` | No approved disposable identities or candidate deployment. | Exercise private, organization, removal, and knowledge routes against candidate deployment. |
| Private storage / RLS | `DEFERRED_PRODUCTIZATION` | Code defaults keep private storage disabled; no provider bucket policy evidence exists. | Do not enable; policy, scanner, RLS, restore, and owner approval are required first. |
| pgvector primary cutover | `DEFERRED_PRODUCTIZATION` | Primary flag defaults false; local migration/preflight evidence is historical only. | Maintain JSON fallback until approved provider cutover evidence exists. |
| Worker, real Vast, and model provider | `BLOCKED_EXTERNAL` | Public status reports Vast disabled/dry-run and model provider disabled. Scheduled Phase 17 worker run `35878131521` on candidate `abc83d36` failed in `POST /internal/workers/v1/claim` with a 20-second `TimeoutError`; setup and dependency steps succeeded, with no authentication/schema/provider failure observed first. The required rerun was not made because Render candidate provenance remains blocked. | No real rental/inference. After authorized Render candidate deployment, rerun the existing workflow once; diagnose only if the bounded claim still fails. |
| Rate-limit rollout | `BLOCKED_EXTERNAL` | Repository supports guarded/shadow modes; deployed mode, proxy CIDRs, and pepper are not observable safely. | Read-only environment audit and approved rollout decision. |
| Monitoring, alerting, incident ownership | `BLOCKED_EXTERNAL` / `BLOCKED_HUMAN_APPROVAL` | Repository has local/isolated foundations and runbooks only. | External receiver/pager evidence and named private ownership record. |
| Backup, restore, and secret rotation | `BLOCKED_EXTERNAL` / `BLOCKED_HUMAN_APPROVAL` | Local restore verifier and secret-inventory template expressly do not prove provider configuration. | Approved isolated provider restore and owner-held rotation evidence. |
| GitHub release controls | `VERIFIED` | 2026-09-23 active ruleset `23890276` applies pull-request, current-head, resolved-conversation, deletion, and force-push protections to `main`; it requires the ten actual GitHub Actions contexts. Admin bypass is `pull_request` only. Native Actions SHA pinning, dependency graph/SBOM (`200`), Dependabot alerts/security updates, secret scanning, and push protection are enabled. | Required reviewer count remains zero for the single maintainer. Generic-pattern and validity-check scanning are `BLOCKED_EXTERNAL - GITHUB PLAN/FEATURE AVAILABILITY`; no protection is suppressed. |
| Public product claims | `VERIFIED` (repository copy) | 2026-09-23 repository scan found no affirmative unsupported production/SLA/compliance/paid-provider claim in primary README/current-state copy. | Deployed UI/legal text remains unverified until the candidate is deployed. |
| Qualified legal/privacy/commercial review | `BLOCKED_HUMAN_APPROVAL` | No qualified written review or release-owner approval was supplied. | Record private evidence reference and approved conclusions without legal advice in this repository. |
| Commercial launch approval | `BLOCKED_HUMAN_APPROVAL` | Mandatory provenance, provider, backup/operations, and legal gates are incomplete. | Cannot be approved in Phase 22's current state. |

The current release path is an authorized Render deployment of `abc83d36`, then
bounded safe-status/health/readiness evidence and only approved non-destructive
external validation. Local tests, prior hosted CI, Vercel evidence, or a healthy
old Render deployment cannot substitute for that action.
