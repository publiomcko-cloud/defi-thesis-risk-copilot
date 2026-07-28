# V1 Phase 19 Execution Plan — Production Operations and Security

Status: **In Progress — 19A through 19D implemented locally; deployment evidence pending**

This plan implements the [Phase 19 contract](future_phase_contracts.md#v1-phase-19--production-operations-and-security). Read it with [current state](current_state.md), [architecture](architecture.md), [deployment](deployment.md), [testing](testing.md), and the [Phase 18 archive](archive/v1_phase_18/).

## 1. Goal and non-negotiable boundary

Phase 19 makes the deployed control plane, workers, storage, identity, and tenant boundaries observable, hardened, recoverable, and supportable. It does not introduce wallets, signing, custody, trade execution, personalized advice, or autonomous capital allocation.

Phase 18 is merged, but durable storage, ingestion, embeddings, shadow retrieval, corpus import, and pgvector-primary retrieval remain feature-gated. Curated Markdown/local JSON RAG remains the production fallback. Phase 19 may collect controlled readiness, shadow, and isolated synthetic primary-path evidence, but it must not perform a broad customer cutover or make a final launch claim. Final deployed validation and launch approval remain Phase 22. Real Vast.ai rentals remain disabled.

## 2. Threat-model baseline

Create and maintain `docs/phase_19_threat_model.md` before activating an operational control. It must record assets, actors, trust boundaries, entry points, abuse cases, mitigations, residual risk, owner, review date, and evidence for:

- account takeover, session theft, recovery/MFA abuse, privileged-admin misuse, and audit tampering;
- BFF/API request forwarding, SSRF, proxy-header/CORS/CSRF/cookie errors, quota/rate-limit bypass, and denial of service;
- tenant leakage, broken object authorization, public storage exposure, malicious uploads, poisoned sources, prompt injection, and vector/citation corruption;
- worker credential theft, duplicate/replayed jobs, queue exhaustion, provider failure, and provider-cost abuse;
- secret exposure, supply-chain compromise, database/object-storage outage, and failed migrations.

All controls derive scope server-side, redact tokens/cookies/credentials/storage keys/source content/PII, and preserve Phases 15–18 behavior. Operational telemetry and security/audit records must remain separate concepts with distinct access and retention policies.

## 3. Ordered implementation slices

Every slice updates the threat model, documentation, deployment runbook, evidence record, and tests. A slice is incomplete without a rollback exercise and the required baseline regressions.

### 19A — Observability and readiness foundation

| Item | Plan |
| --- | --- |
| Objective | Establish privacy-safe, structured operational signals before changing request enforcement or retrieval activation. |
| Dependencies | Completed Phases 15–18; approved log/error/trace destination and data-processing review. |
| Implementation files | `backend/app/core/logging.py`, request middleware, `backend/app/main.py`, job/worker lifecycle services, BFF route handlers, `frontend/src/lib/api.ts`, `backend/scripts/check_operational_readiness.py`, and `docs/phase_19_threat_model.md`. |
| Migrations | None initially. Any durable metric/event store needs an additive revision, indexes, retention policy, and deletion/export impact review. |
| Environment | Disabled-by-default `OBSERVABILITY_ENABLED`, server-only exporter endpoint/credentials, release ID, sampling, bounded queue/backpressure, clock/timezone standard, and redaction configuration; no browser secret. |
| Tests | Browser-to-BFF-to-API-to-job/worker/retrieval correlation IDs; redaction; readiness; exporter timeout/outage/backpressure; bounded buffering; no response/log secrets; browser E2E propagation. |
| Rollout gate | Preview-only, non-mutating readiness and redacted sample logs. Define the telemetry schema, sampling, retention, dashboard access, and deletion policy before production export. Anonymous/public behavior must be unchanged. |
| Rollback | Disable export while retaining safe local request IDs; exporter failure must not block normal requests or create unbounded memory/disk growth; no schema or RAG-primary change. |
| Completion | Documented signal inventory, correlation chain, retention/access matrix, safe readiness CLI/endpoint, and preview evidence. |

### 19B — Distributed rate limiting and abuse controls

| Item | Plan |
| --- | --- |
| Objective | Replace single-process public limits with shared enforcement while keeping server-owned product quotas distinct. |
| Dependencies | 19A; selected managed Redis/database limiter; Render/Vercel proxy-header policy; alert destination. |
| Implementation files | Rate-limit provider abstraction, FastAPI dependencies/middleware, BFF edge handling, configuration, admin-safe metrics, deployment runbook. |
| Migrations | None for Redis. A database limiter needs additive counter/lease tables, expiry indexes, cleanup, and migration rehearsal. |
| Environment | Server-only provider URL/credential, trusted proxies, per-IP/session/user/org/action keys, burst/sustained policies, retry metadata, endpoint-specific fail-open/fail-closed matrix. |
| Tests | Concurrent limiter behavior, proxy spoofing, IP/session/user/org separation, retry headers, quota independence, provider outage behavior, clock skew, atomicity, and abuse alerts. |
| Rollout gate | Shadow counters, then low-risk reads, then bounded compute. Privileged or cost-bearing mutations cannot silently fail open. |
| Rollback | Use platform/WAF throttling and reduced route capacity as the safe degraded mode. Sensitive and cost-bearing actions remain fail-closed. The current in-process limiter may be used only as a documented temporary fallback for low-risk traffic where a single-instance boundary is explicit; it must not be represented as equivalent shared enforcement. |
| Completion | Shared limits active for documented route classes, observed burst/sustained behavior, tested provider-outage policy, and no hybrid-auth regression. |

Implementation status: **implemented locally, feature-gated.** The selected shared store is the existing PostgreSQL/Supabase database, using a privacy-preserving fixed-window table rather than a new paid Redis service. The limiter applies IP plus anonymous-session or authenticated-user scopes to bounded compute, and IP/user/verified-organization scopes to durable-job admission. It supports burst and sustained windows, `shadow` and `enforce` modes, `429` retry metadata, aggregate administrator diagnostics, expiry cleanup, and PostgreSQL contention tests. It remains disabled by default. A preview must first configure a server-only pepper and exact trusted proxy CIDRs, run `shadow` mode, inspect aggregate signals, define an alert owner, and only then enable `enforce` mode for low-risk bounded compute. Cost-bearing job submission fails closed when the enabled limiter database path is unavailable.

### 19C — Edge, BFF, API, and malicious-upload security

| Item | Plan |
| --- | --- |
| Objective | Harden browser, BFF, API, adapter, and source-upload boundaries. |
| Dependencies | 19A; final production origins; WAF capability decision; threat-model approval. |
| Implementation files | Next.js headers/CSP configuration, BFF allowlist/header forwarding, FastAPI CORS/CSRF/proxy controls, adapter URL validation, upload scanner/quarantine interface, deployment configuration. |
| Migrations | None expected. Scanner quarantine/audit retention needs an additive state table and revision. |
| Environment | CSP report endpoint, HSTS eligibility, allowed origins, secure-cookie policy, trusted proxy CIDRs, WAF/bot rules, request-size limits, scanner endpoint/credential. |
| Tests | CSP/HSTS/frame/MIME/referrer/permissions headers; CORS matrix; cookie-backed CSRF analysis; BFF host/path/redirect SSRF rejection; proxy spoofing; MIME/signature mismatch; parser/PDF/archive bounds; decompression-bomb limits; scanner failure fails closed. |
| Rollout gate | Report-only CSP before enforcement where appropriate. Enable HSTS only after all production subdomains are HTTPS-safe. Require scanning before private-source activation. |
| Rollback | Revert a faulty CSP directive through controlled config while retaining minimum safe headers; keep unscanned objects quarantined. |
| Completion | Approved policy matrix and automated browser/API negative coverage. |

Implementation status: **implemented locally, feature-gated.** The frontend now
ships baseline MIME, frame, referrer, permissions, and opener policies plus a
report-only CSP by default. HSTS is disabled until the operator confirms every
covered domain is HTTPS-safe. The API accepts exact configured CORS origins,
uses explicit request methods/headers, rejects browser mutations from other
origins, and bounds declared request bodies. The BFF verifies mutating browser
origins, accepts only an origin-only backend configuration, keeps its path
allowlist, and rejects upstream redirects. Private storage is still disabled;
when production storage is deliberately enabled, scanning must be required and
a configured scanner must return a bounded `{\"status\": \"clean\"}` response
before object storage is called. Scanner failure fails closed. WAF/bot rules,
scanner/quarantine deployment evidence, CSP reports, HSTS approval, and final
production-origin evidence remain pending.

### 19D — Centralized monitoring, synthetics, SLOs, and alerting

| Item | Plan |
| --- | --- |
| Objective | Monitor user-visible availability and report/job/retrieval dependencies with actionable reliability objectives. |
| Dependencies | 19A signals; approved alert channel/on-call owner; safe synthetic tenant. |
| Implementation files | Metrics/exporters, dashboards-as-code/config, synthetic scripts, alert rules, status-page adapter interface, operations runbooks. |
| Migrations | None unless durable alert acknowledgements are later justified and redacted. |
| Environment | Metrics/error/trace destinations, dashboard RBAC, alert routing, platform-stored synthetic credentials, thresholds, escalation policy, and maintenance-window controls. |
| Tests | Liveness/readiness; authenticated synthetic flow; queue depth/age; worker heartbeat; storage/pgvector readiness; retrieval latency/empty/error rate; provider failure; alert deduplication/redaction; synthetic credential revocation. |
| Rollout gate | Define SLIs, SLOs, error budgets, severity, owner, and runbook link for each page-worthy alert. Test alerts route to a non-production receiver before paging. |
| Rollback | Mute a faulty rule through an audited change, retain health checks and evidence for tuning, and never disable all detection for a dependency. |
| Completion | Actionable uptime, queue, worker, storage, retrieval, auth, quota/rate-limit, and provider signals with tested escalation and documented SLOs. |

Implementation status: **implemented locally, feature-gated.** The new
aggregate-only snapshot measures database/JSON-fallback readiness, queue depth
and age, job/worker state, provider cleanup failures, and bounded retrieval
event latency/empty rate. It returns local candidate alerts with stable keys and
runbook IDs only; it has no webhook, pager, status page, exporter, tenant
identifier, query, or source content. The private administrator view and the
`run_synthetic_checks` command are disabled by default. External telemetry,
alert delivery, dashboard RBAC, safe synthetic-tenant deployment, error-budget
evidence, and storage/pgvector probes remain required rollout work.

### 19E — Backup, restore, retention, and secret operations

| Item | Plan |
| --- | --- |
| Objective | Prove recovery and make secret lifecycle auditable without exporting secrets. |
| Dependencies | Supabase/PostgreSQL and object-storage backup capabilities; defined RPO/RTO; key owners; platform secret-store access; isolated restore target. |
| Implementation files | `docs/operations/backup_restore_runbook.md`, `docs/operations/secret_inventory.md`, restore verification scripts, cleanup integration, deployment checklists. |
| Migrations | None for runbooks. Any backup manifest or rotation-audit record requires additive redacted schema and retention controls. |
| Environment | Database backup schedules/retention, provider-native object versioning where available or an explicit immutable backup/export strategy, encryption verification, secret-inventory references, rotation cadence, emergency revocation, worker rotation, and encryption-key migration plan. |
| Tests | Restore sanitized backup to an isolated project; verify reports/jobs/knowledge metadata/object references; measure RPO/RTO; migration backup/rollback; rotate/revoke a non-production worker credential and service credential. |
| Rollout gate | Successful documented restore drill; no production data copied into local development; owners approve RPO/RTO; secret inventory contains identifiers/owners/locations, never values. |
| Rollback | Restore only through the runbook. Alembic downgrade is never data recovery. |
| Completion | Tested restore evidence, approved RPO/RTO, current secret owners/inventory, rotation and emergency-revocation drills. |

### 19F — CI/CD and supply-chain security

| Item | Plan |
| --- | --- |
| Objective | Require security and migration quality before `main` changes. |
| Dependencies | Repository/org permission for protection; scanner selection; documented false-positive and exception process. |
| Implementation files | `.github/workflows/*`, dependency/container/SBOM config, pinned-action policy, CODEOWNERS/review policy if available, security-response runbook. |
| Migrations | None. |
| Environment | Scanner tokens only in GitHub secrets; least-privilege workflow permissions, artifact retention, protected-branch required checks. |
| Tests | Secret-scan fixture safety, dependency/container scans, lockfile review, migration cycle, preview secret isolation, action pin check, required-check evidence, and pull-request permission review. |
| Rollout gate | Informational scan period to triage baseline, then critical/high findings block merges according to the approved policy. Any exception is time-bounded, owned, and recorded. |
| Rollback | Disable a broken new scanner only with a recorded reason, expiry, owner, and bounded alternative; never remove current passing CI checks. |
| Completion | Protected `main`, required scans/tests, dependency-update process, findings workflow, SBOM where practical, and secret-free previews. |

### 19G — Incident-response and security-operations runbooks

| Item | Plan |
| --- | --- |
| Objective | Make detection, containment, recovery, communication, evidence handling, and retrospective actions executable rather than implicit. |
| Dependencies | 19A–19F signals, ownership, backup/restore, and secret-rotation procedures. |
| Implementation files | `docs/operations/incidents/` runbooks, severity matrix, contact/escalation map, evidence-handling rules, and tabletop scripts. |
| Migrations | None expected. Incident tickets and evidence remain in approved operational systems, not raw repository files. |
| Environment | On-call/escalation references, status-page and communication channels, emergency access procedure, and audit-safe evidence location. |
| Tests | Tabletop exercises for credential leak, account takeover, tenant exposure, malicious source, queue duplication, runaway provider cost, database/storage outage, vector corruption, failed migration, and compromised worker. |
| Rollout gate | Named primary/backup owner, communication authority, containment action, recovery dependency, and evidence path for every runbook. |
| Rollback | Runbook changes are versioned; emergency actions must include restoration and credential-reissue steps. |
| Completion | Required runbooks published, reviewed, exercised, and linked from alerts. Critical gaps block Phase 19 completion. |

### 19H — Load, worker-loss, provider-failure, and recovery exercises

| Item | Plan |
| --- | --- |
| Objective | Validate capacity, saturation, and controlled dependency failure. |
| Dependencies | 19A–19G signals, alerts, and runbooks; isolated environment; approved cost/time limits. |
| Implementation files | Load/failure harnesses, worker-loss scripts, storage/database/provider fakes, accessibility checks, incident exercise records, CI/nightly workflow definitions. |
| Migrations | None unless durable redacted test-run metadata is justified. |
| Environment | Test-only concurrency/timeout/budget controls; no real Vast credentials or rentals. |
| Tests | Accessibility, load/burst/saturation, queue admission, worker loss/lease recovery, provider timeout, object-storage outage, pgvector corruption recovery, migration rollback rehearsal, authorization fuzzing, and database recovery simulation. |
| Rollout gate | Isolated environment, working alerts, cost ceiling; production chaos testing needs explicit approval. |
| Rollback | Stop drivers, drain/recover queues through Phase 17 procedures, disable test-only configuration. |
| Completion | SLO-oriented results, no unresolved critical/high issue, exercised incident runbooks, and documented capacity/failure risk. |

### 19I — Controlled Phase 18 deployment and rollback evidence

| Item | Plan |
| --- | --- |
| Objective | Gather narrow, reversible durable-RAG evidence without a broad customer activation or final launch claim. |
| Dependencies | 19A–19H; private bucket/RLS review; pgvector preflight; scoped worker; synthetic two-user tenants; Phase 18 archive gates. |
| Implementation files | Controlled deployment checklist, readiness/synthetic scripts, dashboard/alert configuration, evidence record. |
| Migrations | No new Phase 18 schema. Rehearse backup/restore around merged `0017`–`0021`. |
| Environment | In production, enable only an approved minimal shadow-mode flag set and keep `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=false`. In a separate isolated preview/staging environment, the primary flag may be enabled temporarily for synthetic traffic to prove the actual report path and rollback. Keep `VAST_DRY_RUN=true` and `VAST_REAL_RENTALS_ENABLED=false` everywhere. |
| Tests | Storage-policy probe, private/organization two-user isolation, synthetic worker ingestion, deployed primary-path synthetic report in isolation, durable-versus-JSON comparison, citation integrity, JSON rollback, and no secret/log exposure. |
| Rollout gate | Written approval, passing synthetic evidence, alerts, backup readiness, explicit scope, tested rollback. Never use customer private data as the first probe. |
| Rollback | Disable durable ingestion/retrieval flags in documented order, retain durable records for investigation, and return reports to JSON RAG. |
| Completion | Controlled shadow and isolated primary-path evidence recorded. Broad customer cutover, final launch approval, and commercial production claims remain Phase 22 decisions. |

## 4. Cross-slice validation and completion matrix

Each implementation slice runs the relevant baseline in [testing](testing.md): backend and PostgreSQL integration, migration upgrade/downgrade/upgrade when schema changes, frontend lint/BFF/MFA/browser checks, worker checks, recovery/cleanup dry runs, and default/worker/production Compose validation. Add focused security, load, accessibility, and failure tests before enabling each respective control.

Maintain a Phase 19 evidence matrix mapping every requirement and completion gate in `future_phase_contracts.md` to its implementation, test, deployment evidence, owner, rollback procedure, and status. Phase 19 cannot be labeled complete while a contract gate is merely planned or while an unresolved critical/high security finding exists.

The current matrix is [`phase_19_evidence_matrix.md`](phase_19_evidence_matrix.md). The current threat model is [`phase_19_threat_model.md`](phase_19_threat_model.md).

No validation uses production customer data, browser-accessible secrets, real provider rentals, or live capital execution.

## 5. Proposed first implementation task

Initial implementation began with **19A**: a redacted structured-log/correlation contract and a non-mutating operational readiness checker. The next completed local slices are **19B**, the feature-gated PostgreSQL shared limiter, and **19C**, feature-gated edge/BFF/API/upload hardening. These slices do not enable Phase 18 durable flags or alter production retrieval authority.

19A status: **implemented locally.** External telemetry export is intentionally not implemented. Preview evidence, retention/access policy approval, dashboard ownership, and alerting remain later Phase 19D/19E operational work.
