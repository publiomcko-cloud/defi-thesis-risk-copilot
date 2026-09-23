# Phase 22 Evidence Matrix

Status: **ACTIVE - HOLD.** Evidence is intentionally separated between direct
repository/public checks and provider or human prerequisites. The direct public
provenance check below fails the candidate-deployment gate.

Candidate: `abc83d36c115b4122a1a1964fde101fbf9c407e4` (PR #36 merge)

| Gate | State | Environment / dated safe evidence | Limitation and required next step |
| --- | --- | --- | --- |
| Repository baseline | `VERIFIED` | Phase 22 began at merged PR #36 commit `abc83d36` on 2026-09-23; the Phase 22 working tree adds validation documentation only. | Must remain the reviewed implementation base of the Phase 22 PR. |
| Migration lineage | `VERIFIED` | Local `alembic heads` returned only `20260911_0034`; revisions `0030` through `0034` are linear; `0027` is absent. | Does not inspect the production database. |
| Static safe defaults | `VERIFIED` | `Settings` defaults keep analytics, schedule dispatch, pgvector primary, real Vast rentals, and synthesis disabled. | The public status endpoint exposes only part of deployed configuration. |
| Repository regression | `VERIFIED` | 2026-09-23 fresh PostgreSQL/pgvector database: preflight, zero-to-`0034` migration, full `pytest`, `0034 -> 0033 -> 0034`, corpus evaluation, runtime preparation, frontend type/contracts/build/browser E2E, Compose render, supply-chain checks, clean image scans, and isolated Phase 19 catalog all exited 0. Required hosted checks also passed on documentation-only SHA `d89b5bb92bf66029d1ba696f34951ead67130b40`. | Local/hosted regression evidence never establishes deployed/provider state. Preserve checks through the final documentation-only SHA. |
| Backend health | `VERIFIED` | 2026-09-23T11:42Z, public `GET /health`: HTTPS 200; bounded response said healthy/production. | Liveness is not release provenance. |
| Backend readiness | `VERIFIED` | 2026-09-23T11:42Z, public `GET /ready`: HTTPS 200; database and RAG index true. | Does not prove migration head, backup, or tenant boundaries. |
| Backend deployment status | `FAILED` | 2026-09-23T11:42Z, public `GET /api/deployment/status`: HTTPS 200, production/public-demo/auth enabled, database connected, synthesis disabled, provider disabled, Vast disabled/dry-run; commit was `6f07ef9`. | `6f07ef9` is an ancestor of but not the candidate; deploy and prove `abc83d36` first. |
| Frontend reachability | `VERIFIED` | 2026-09-23T11:42Z, Vercel root, `/demo`, and `/status` each returned HTTPS 200. | Public HTML does not disclose a Vercel commit; provenance is unverified. |
| API documentation reachability | `VERIFIED` | 2026-09-23T11:42Z, Render `/docs` returned HTTPS 200. | Intentional public docs only; no administrative route was exercised. |
| Render/Vercel configuration inventory | `BLOCKED_EXTERNAL` | No approved Render/Vercel configuration interface or CLI session is available in this validation environment. | Read-only categorical audit after candidate deployment; never record values. |
| Supabase auth configuration | `BLOCKED_EXTERNAL` | Public status says authentication is enabled. Supabase provider, verified-email, redirects, SMTP, cookie, and service-role configuration are not publicly inspectable. | Approved read-only Supabase audit. |
| SMTP and email delivery | `BLOCKED_EXTERNAL` | No custom SMTP provider/configuration or disposable mailbox evidence supplied. | Owner-approved custom SMTP and safe disposable-account flows. |
| Deployed auth, recovery, MFA | `BLOCKED_EXTERNAL` | No approved disposable accounts or candidate deployment. | Candidate deployment plus manually controlled test identities; remove identities afterward. |
| Two-user and organization isolation | `BLOCKED_EXTERNAL` | No approved disposable identities or candidate deployment. | Exercise private, organization, removal, and knowledge routes against candidate deployment. |
| Private storage / RLS | `DEFERRED_PRODUCTIZATION` | Code defaults keep private storage disabled; no provider bucket policy evidence exists. | Do not enable; policy, scanner, RLS, restore, and owner approval are required first. |
| pgvector primary cutover | `DEFERRED_PRODUCTIZATION` | Primary flag defaults false; local migration/preflight evidence is historical only. | Maintain JSON fallback until approved provider cutover evidence exists. |
| Worker, real Vast, and model provider | `BLOCKED_EXTERNAL` | Public status reports Vast disabled/dry-run and model provider disabled; no trusted deployed-worker or provider evidence was supplied. | No real rental/inference; obtain approved synthetic worker/provider evidence separately. |
| Rate-limit rollout | `BLOCKED_EXTERNAL` | Repository supports guarded/shadow modes; deployed mode, proxy CIDRs, and pepper are not observable safely. | Read-only environment audit and approved rollout decision. |
| Monitoring, alerting, incident ownership | `BLOCKED_EXTERNAL` / `BLOCKED_HUMAN_APPROVAL` | Repository has local/isolated foundations and runbooks only. | External receiver/pager evidence and named private ownership record. |
| Backup, restore, and secret rotation | `BLOCKED_EXTERNAL` / `BLOCKED_HUMAN_APPROVAL` | Local restore verifier and secret-inventory template expressly do not prove provider configuration. | Approved isolated provider restore and owner-held rotation evidence. |
| GitHub release controls | `FAILED` | 2026-09-23 direct GitHub REST audit: repository rulesets response was empty; `main` branch-protection returned 404; secret scanning, push protection, and Dependabot security updates reported disabled; Actions SHA pinning was not required. | A repository administrator must configure/evidence branch or ruleset PR protections, required checks, security features, and immutable-action enforcement. Repository workflow policy is not a substitute. |
| Public product claims | `VERIFIED` (repository copy) | 2026-09-23 repository scan found no affirmative unsupported production/SLA/compliance/paid-provider claim in primary README/current-state copy. | Deployed UI/legal text remains unverified until the candidate is deployed. |
| Qualified legal/privacy/commercial review | `BLOCKED_HUMAN_APPROVAL` | No qualified written review or release-owner approval was supplied. | Record private evidence reference and approved conclusions without legal advice in this repository. |
| Commercial launch approval | `BLOCKED_HUMAN_APPROVAL` | Mandatory provenance, provider, backup/operations, and legal gates are incomplete. | Cannot be approved in Phase 22's current state. |

`FAILED` is not converted to `VERIFIED` by local tests or prior hosted CI. The
current release path is to align both deployed services with the candidate,
then collect only approved non-destructive external evidence.
