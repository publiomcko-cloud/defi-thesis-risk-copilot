# Phase 19 Threat Model

Status: **19A baseline implemented locally; review and operational rollout evidence pending.**

This is the living threat model for V1 Phase 19. It records no credentials, customer content, storage keys, or personal data. Security/audit records remain separate from operational telemetry and retain their existing authorization and retention rules.

| Asset or boundary | Threat | Phase 19A mitigation and evidence | Residual risk / next owner |
| --- | --- | --- | --- |
| Browser, BFF, API | Correlation header injection, proxy spoofing, rate-limit bypass, or log forging | IDs are pattern-validated, bounded, generated on invalid input, and returned as safe response headers. BFF forwards only normalized IDs. The 19B limiter accepts forwarded client IPs only from configured trusted CIDRs and stores salted scope hashes. | Configure exact Render/Vercel proxy CIDRs and run preview shadow evidence before enforcement. CSP, CSRF, CORS, and SSRF hardening: 19C. |
| API and error path | Secret, cookie, token, source, or storage-key logging | JSON formatter redacts sensitive field names/value patterns and omits exception tracebacks. Tests prove nested redaction. | Approved central exporter, retention, and access policy: 19D/19E. |
| Durable job and worker boundary | Loss of browser-to-worker causality | Server-owned correlation ID is stored only in internal job context and forwarded in worker control-plane headers; executor thread context is retained. | Queue saturation, worker loss, and replay exercises: 19H. |
| Readiness surface | Privileged configuration or tenant disclosure | Admin-only metadata endpoint and local CLI expose readiness booleans only; no URLs, credentials, keys, source content, or tenant data. | Synthetics, storage probes, alerting, and RBAC dashboards: 19D/19I. |
| Object/vector storage and RAG | Tenant leakage, poisoned source, corrupt vector, broad cutover | Phase 18 server-derived filters and JSON fallback remain unchanged; pgvector primary stays disabled. | Upload scanning, deployed policy checks, controlled shadow evidence: 19C/19I and final approval in Phase 22. |
| Identity and administration | Account takeover, recovery/MFA abuse, privileged misuse, audit tampering | Existing Phase 16 authentication, role, MFA, and audit boundaries are preserved; operational endpoint requires platform admin. | Deployed two-user/MFA evidence and incident exercises: 19G/Phase 22. |
| Public compute and providers | Rate-limit bypass, DoS, provider-cost abuse, secret exposure | 19B supplies a disabled-by-default PostgreSQL shared limiter with IP/session/user/verified-org scopes, burst/sustained windows, retry metadata, and fail-closed compute/job behavior in enforce mode. Phase 17 reservation controls remain unchanged; real Vast rentals remain disabled. | Alert owner, production proxy configuration, preview shadow evidence, and staged enforcement remain required. Provider failure and cost exercises: 19H. |
| Supply chain and recovery | Compromised dependency, database/object outage, failed migration | Existing CI and migration checks remain required. The 2026-07-28 production dependency audit reports three high-severity advisories: direct `next` and transitive `postcss`/`sharp`. | Dependency remediation and protected-branch scan policy: 19F. The open high-severity advisories block Phase 19 completion. Backup/restore: 19E; incident runbooks: 19G. |

## 19A acceptance evidence

- Backend request middleware propagates a validated correlation ID to API responses and structured logs.
- Frontend API calls create a browser correlation ID; the BFF normalizes/forwards it to FastAPI and returns it only as a safe response header. When configured, the BFF forwards only a syntactically valid provider client IP; FastAPI honors it only from a configured trusted proxy CIDR.
- Submitted durable jobs retain a server-owned correlation ID in internal context; worker control-plane calls and executor execution preserve it.
- `backend/scripts/check_operational_readiness.py` and `GET /api/admin/operations/readiness` are read-only. The endpoint requires a platform administrator.
- No external telemetry exporter, dashboard, or alert integration is configured or enabled in 19A.

Review date: 2026-07-28. Owner: platform engineering. Re-review before enabling any external telemetry, shared limiter, upload scanner, or Phase 18 shadow deployment.
