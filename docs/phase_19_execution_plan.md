# V1 Phase 19 Execution Plan — Production Operations and Security

Status: **Active — planning complete; implementation has not started**

This plan implements the [Phase 19 contract](future_phase_contracts.md#v1-phase-19--production-operations-and-security). Read it with [current state](current_state.md), [architecture](architecture.md), [deployment](deployment.md), [testing](testing.md), and the [Phase 18 archive](archive/v1_phase_18/).

## 1. Goal and non-negotiable boundary

Phase 19 makes the deployed control plane, workers, storage, identity, and tenant boundaries observable, hardened, recoverable, and supportable. It does not introduce wallets, signing, custody, trade execution, personalized advice, or autonomous capital allocation.

Phase 18 is merged but durable storage, ingestion, embeddings, shadow retrieval, corpus import, and pgvector-primary retrieval remain feature-gated. Curated Markdown/local JSON RAG remains the production fallback. Phase 19 may collect controlled shadow/readiness evidence, but does not enable all Phase 18 production flags or make a final cutover claim. Final deployed validation and launch approval remain Phase 22. Real Vast.ai rentals remain disabled.

## 2. Threat-model baseline

Create and maintain `docs/phase_19_threat_model.md` before activating an operational control. It must record assets, actors, trust boundaries, entry points, abuse cases, mitigations, residual risk, owner, and evidence for:

- account takeover, session theft, recovery/MFA abuse, privileged-admin misuse, and audit tampering;
- BFF/API request forwarding, SSRF, proxy-header/CORS/CSRF/cookie errors, quota/rate-limit bypass, and denial of service;
- tenant leakage, broken object authorization, public storage exposure, malicious uploads, poisoned sources, prompt injection, and vector/citation corruption;
- worker credential theft, duplicate/replayed jobs, queue exhaustion, provider failure, and provider-cost abuse;
- secret exposure, supply-chain compromise, database/object-storage outage, and failed migrations.

All controls derive scope server-side, redact tokens/cookies/credentials/storage keys/source content/PII, and preserve Phases 15–18 behavior.

## 3. Ordered implementation slices

Every slice updates the threat model, documentation, deployment runbook, and tests. A slice is incomplete without a rollback exercise and the required baseline regressions.

### 19A — Observability and readiness foundation

| Item | Plan |
| --- | --- |
| Objective | Establish privacy-safe, structured operational signals before changing request enforcement or retrieval activation. |
| Dependencies | Completed Phases 15–18; approved log/error/trace destination and data-processing review. |
| Implementation files | `backend/app/core/logging.py`, request middleware, `backend/app/main.py`, job/worker lifecycle services, BFF route handlers, `frontend/src/lib/api.ts`, `backend/scripts/check_operational_readiness.py`, and `docs/phase_19_threat_model.md`. |
| Migrations | None initially. Any durable metric/event store needs an additive revision, indexes, and retention policy. |
| Environment | Disabled-by-default `OBSERVABILITY_ENABLED`, server-only exporter endpoint/credentials, release ID, sampling, and redaction configuration; no browser secret. |
| Tests | Browser-to-BFF-to-API-to-job/worker/retrieval correlation IDs; redaction; readiness; disabled-exporter fallback; no response/log secrets; browser E2E propagation. |
| Rollout gate | Preview-only, non-mutating readiness and redacted sample logs. Anonymous/public behavior must be unchanged. |
| Rollback | Disable export while retaining safe local request IDs; no schema or RAG-primary change. |
| Completion | Documented signal inventory, correlation chain, safe readiness CLI/endpoint, and preview evidence. |

### 19B — Distributed rate limiting and abuse controls

| Item | Plan |
| --- | --- |
| Objective | Replace single-process public limits with shared enforcement while keeping server-owned product quotas distinct. |
| Dependencies | 19A; selected managed Redis/database limiter; Render/Vercel proxy-header policy; alert destination. |
| Implementation files | Rate-limit provider abstraction, FastAPI dependencies/middleware, BFF edge handling, configuration, admin-safe metrics, deployment runbook. |
| Migrations | None for Redis. A database limiter needs additive counter/lease tables, expiry indexes, cleanup, and migration rehearsal. |
| Environment | Server-only provider URL/credential, trusted proxies, per-IP/session/user/org/action keys, burst/sustained policies, retry metadata, endpoint-specific fail-open/fail-closed matrix. |
| Tests | Concurrent limiter behavior, proxy spoofing, IP/session/user/org separation, retry headers, quota independence, provider outage behavior, and abuse alerts. |
| Rollout gate | Shadow counters, then low-risk reads, then bounded compute. Privileged mutations cannot silently fail open. |
| Rollback | Return to current in-process limiter without altering product quotas; expire only owned shared keys. |
| Completion | Shared limits active for documented route classes, observed burst/sustained behavior, and no hybrid-auth regression. |

### 19C — Edge, BFF, API, and malicious-upload security

| Item | Plan |
| --- | --- |
| Objective | Harden browser, BFF, API, adapter, and source-upload boundaries. |
| Dependencies | 19A; final production origins; WAF capability decision; threat-model approval. |
| Implementation files | Next.js headers/CSP configuration, BFF allowlist/header forwarding, FastAPI CORS/CSRF/proxy controls, adapter URL validation, upload scanner/quarantine interface, deployment configuration. |
| Migrations | None expected. Scanner quarantine/audit retention needs an additive state table and revision. |
| Environment | CSP report endpoint, HSTS eligibility, allowed origins, secure-cookie policy, trusted proxy CIDRs, WAF/bot rules, request-size limits, scanner endpoint/credential. |
| Tests | CSP/HSTS/frame/MIME/referrer/permissions headers; CORS matrix; cookie-backed CSRF analysis; BFF host/path/redirect SSRF rejection; proxy spoofing; MIME/signature mismatch; parser/PDF/archive bounds; scanner failure fails closed. |
| Rollout gate | Report-only CSP before enforcement where appropriate. Enable HSTS only after all production subdomains are HTTPS-safe. Require scanning before private-source activation. |
| Rollback | Revert a faulty CSP directive through controlled config while retaining minimum safe headers; keep unscanned objects quarantined. |
| Completion | Approved policy matrix and automated browser/API negative coverage. |

### 19D — Centralized monitoring, synthetics, and alerting

| Item | Plan |
| --- | --- |
| Objective | Monitor user-visible availability and report/job/retrieval dependencies. |
| Dependencies | 19A signals; approved alert channel/on-call owner; safe synthetic tenant. |
| Implementation files | Metrics/exporters, dashboards-as-code/config, synthetic scripts, alert rules, status-page adapter interface, operations runbooks. |
| Migrations | None unless durable alert acknowledgements are later justified and redacted. |
| Environment | Metrics/error/trace destinations, alert routing, platform-stored synthetic credentials, thresholds, and escalation policy. |
| Tests | Liveness/readiness; authenticated synthetic flow; queue depth/age; worker heartbeat; storage/pgvector readiness; retrieval latency/empty/error rate; provider failure; alert deduplication/redaction. |
| Rollout gate | Test alerts route to a non-production receiver first; owners and severity/escalation are documented before paging. |
| Rollback | Mute a faulty rule, retain health checks and evidence for tuning. |
| Completion | Actionable uptime, queue, worker, storage, retrieval, auth, quota/rate-limit, and provider signals with tested escalation. |

### 19E — Backup, restore, retention, and secret operations

| Item | Plan |
| --- | --- |
| Objective | Prove recovery and make secret lifecycle auditable without exporting secrets. |
| Dependencies | Supabase/Storage backup capabilities; defined RPO/RTO; key owners; platform secret-store access; isolated restore target. |
| Implementation files | `docs/operations/backup_restore_runbook.md`, `docs/operations/secret_inventory.md`, restore verification scripts, cleanup integration, deployment checklists. |
| Migrations | None for runbooks. Any backup manifest or rotation-audit record requires additive redacted schema and retention controls. |
| Environment | Backup schedules/retention, object versioning, encryption verification, secret-inventory references, rotation cadence, emergency revocation, worker rotation, encryption-key migration plan. |
| Tests | Restore sanitized backup to isolated project; verify reports/jobs/knowledge metadata/object references; measure RPO/RTO; migration backup/rollback; rotate/revoke non-production worker credential. |
| Rollout gate | Successful documented restore drill; no production data copied into local development; owners approve RPO/RTO. |
| Rollback | Restore only through the runbook. Alembic downgrade is never data recovery. |
| Completion | Tested restore evidence, approved RPO/RTO, current secret owners/inventory, rotation and emergency-revocation drills. |

### 19F — CI/CD and supply-chain security

| Item | Plan |
| --- | --- |
| Objective | Require security and migration quality before `main` changes. |
| Dependencies | Repository/org permission for protection; scanner selection; documented false-positive process. |
| Implementation files | `.github/workflows/*`, dependency/container/SBOM config, pinned-action policy, CODEOWNERS/review policy if available, security-response runbook. |
| Migrations | None. |
| Environment | Scanner tokens only in GitHub secrets; least-privilege permissions, artifact retention, protected-branch required checks. |
| Tests | Secret-scan fixture safety, dependency/container scans, lockfile review, migration cycle, preview secret isolation, action pin check, required-check evidence. |
| Rollout gate | Informational scan period to triage baseline, then critical/high findings block merges according to the approved policy. |
| Rollback | Disable a broken new scanner only with recorded reason and bounded alternative; never remove current passing CI checks. |
| Completion | Protected `main`, required scans/tests, dependency-update process, findings workflow, and secret-free previews. |

### 19G — Load, worker-loss, provider-failure, and recovery exercises

| Item | Plan |
| --- | --- |
| Objective | Validate capacity, saturation, and controlled dependency failure. |
| Dependencies | 19A–19F signals and alerts; isolated environment; approved cost/time limits. |
| Implementation files | Load/failure harnesses, worker-loss scripts, storage/database/provider fakes, accessibility checks, incident runbooks, CI/nightly workflow definitions. |
| Migrations | None unless durable redacted test-run metadata is justified. |
| Environment | Test-only concurrency/timeout/budget controls; no real Vast credentials or rentals. |
| Tests | Accessibility, load/burst/saturation, queue admission, worker loss/lease recovery, provider timeout, object-storage outage, pgvector corruption recovery, migration rollback rehearsal, authorization fuzzing, database recovery simulation. |
| Rollout gate | Isolated environment, working alerts, cost ceiling; production chaos testing needs explicit approval. |
| Rollback | Stop drivers, drain/recover queues through Phase 17 procedures, disable test-only configuration. |
| Completion | SLO-oriented results, no unresolved critical/high issue, tested incident runbooks, documented capacity/failure risk. |

### 19H — Controlled Phase 18 deployment and rollback evidence

| Item | Plan |
| --- | --- |
| Objective | Gather narrow, reversible durable-RAG shadow evidence without a final activation claim. |
| Dependencies | 19A–19G; private bucket/RLS review; pgvector preflight; scoped worker; synthetic two-user tenants; Phase 18 archive gates. |
| Implementation files | Controlled deployment checklist, readiness/synthetic scripts, dashboard/alert configuration, evidence record. |
| Migrations | No new Phase 18 schema. Rehearse backup/restore around merged `0017`–`0021`. |
| Environment | Enable only a minimal flag set in approved shadow environment; keep `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=false`, `VAST_DRY_RUN=true`, and `VAST_REAL_RENTALS_ENABLED=false`. |
| Tests | Storage-policy probe, private/organization two-user isolation, synthetic worker ingestion, durable-versus-JSON comparison, citation integrity, JSON rollback, and no secret/log exposure. |
| Rollout gate | Written approval, passing synthetic evidence, alerts, backup readiness, explicit scope, tested rollback. Never use customer private data as first probe. |
| Rollback | Disable durable ingestion/retrieval flags in documented order, retain durable records for investigation, return reports to JSON RAG. |
| Completion | Controlled shadow evidence recorded. Final primary activation, launch approval, and commercial production claim remain Phase 22 decisions. |

## 4. Cross-slice validation

Each implementation slice runs the relevant baseline in [testing](testing.md): backend and PostgreSQL integration, migration upgrade/downgrade/upgrade when schema changes, frontend lint/BFF/MFA/browser checks, worker checks, recovery/cleanup dry runs, and default/worker/production Compose validation. Add focused security, load, accessibility, and failure tests before enabling each respective control.

No validation uses production customer data, browser-accessible secrets, real provider rentals, or live capital execution.

## 5. Proposed first implementation task

Implement **19A only**: a redacted structured-log/correlation contract and a non-mutating operational readiness checker. Its first deployment gate is a preview proving correlation from browser request through BFF/API and, when applicable, job/worker/retrieval activity. It does not add distributed rate limits, enable Phase 18 durable flags, or alter production retrieval authority.
