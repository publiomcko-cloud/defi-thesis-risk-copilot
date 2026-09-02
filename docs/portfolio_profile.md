# Portfolio Implementation Profile

Status: **Phase 20J closeout validation in progress**

This repository is currently developed as a production-grade portfolio anchor, not as an actively commercialized SaaS product.

The goal is to demonstrate realistic architecture, security, data engineering, AI engineering, multi-tenant backend design, durable workflows, lifecycle handling, testing, and operational discipline while avoiding the ongoing legal, provider, tax, payment, support, and production-operations burden of running a commercial service.

The architecture must remain deliberately convertible back into a product. Product-only requirements are preserved in [`productization_backlog.md`](productization_backlog.md) rather than removed.

---

## 1. Authority and precedence

For current implementation decisions:

1. this portfolio profile defines which roadmap capabilities are required now;
2. [`phase_20_execution_plan.md`](phase_20_execution_plan.md) defines the active Phase 20 portfolio sequence;
3. [`future_phase_contracts.md`](future_phase_contracts.md) remains the broader product-capable target contract and historical source of commercial requirements;
4. [`productization_backlog.md`](productization_backlog.md) records requirements intentionally deferred from the active portfolio profile;
5. permanent security, tenant-isolation, deterministic-risk, lifecycle, migration, and recovery boundaries remain authoritative regardless of profile.

The portfolio profile may reduce operational/commercial scope, but it must not weaken security or data-integrity requirements.

---

## 2. Portfolio objective

The public repository and demo should show that the system can be engineered like a serious SaaS platform without claiming that all commercial operations are live.

The portfolio should demonstrate:

- deterministic DeFi risk analysis with model-assisted explanation;
- source-grounded retrieval and explicit provenance;
- managed identity, BFF boundaries, authorization, organizations, and quotas;
- durable jobs, worker protocols, retries, cancellation, idempotency, and recovery;
- tenant-safe knowledge/RAG architecture with production features safely gated;
- security controls, structured operational evidence, migrations, and rollback;
- consent-aware first-party analytics architecture;
- durable scheduling;
- in-app event-driven notifications;
- server-owned versioned entitlements and non-billable usage metering;
- organization invitations, roles, seat controls, and concurrency safety;
- bounded first-party support/privacy-request orchestration;
- evaluated AI/model routing and research intelligence in Phase 21.

The portfolio does not need to operate a real commercial business to demonstrate these engineering capabilities.

---

## 3. Required Phase 20 portfolio scope

| Slice | Portfolio requirement | Current direction |
| --- | --- | --- |
| 20A | Required | Governance, threat, evidence, data-model, provider and taxonomy foundations |
| 20B | Required | Consent-aware first-party analytics; implemented, production collection remains disabled |
| 20C | Required | Durable user-owned scheduled monitoring through Phase 17 jobs |
| 20D | Required | User-controlled in-app notifications and preferences |
| 20E | Omitted optional demonstration | No synthetic delivery adapter is implemented; the provider-neutral boundary remains documented for future work. |
| 20F | Required | Versioned entitlements plus non-billable, exactly-once/reconcilable usage metering |
| 20G | Not required | Real billing/provider work is deferred; an optional fake billing state machine may be used only as architecture evidence |
| 20H | Required | Invitations, roles, ownership transfer, synthetic seat entitlements, organization lifecycle |
| 20I | Required, reduced | Minimal first-party support, feedback, privacy request tracking and public-safe status process |
| 20J | Required | Portfolio architecture closeout; exact-head hosted validation is required before Phase 20 completion, not commercial/legal launch certification |

Phase 21 should begin after the required Phase 20 portfolio slices are complete. Phase 21 has higher portfolio value than completing real payment, helpdesk, messaging, or marketing integrations.

---

## 4. Portfolio-safe implementation decisions

### Scheduled monitoring

Implement real durable scheduling behavior because it demonstrates significant backend architecture:

- PostgreSQL due-row claiming;
- Phase 17 durable jobs;
- restart survival;
- one-winner concurrency;
- idempotent occurrences;
- IANA timezone and DST handling;
- missed-run coalescing;
- quota/cost denial;
- authorization revalidation;
- pause/resume/delete lifecycle.

Initial portfolio policy:

- authenticated user ownership first;
- code-owned monitoring targets only;
- minimum cadence one hour;
- hourly, six-hourly, daily, and weekly presets;
- at most five active schedules per user;
- missed runs coalesce to at most one replacement run;
- occurrences more than 24 hours overdue are skipped and recorded;
- 30-day schedule-run history.

Organization-owned scheduling may remain disabled until the Phase 20H authority model exists.

### In-app notifications

Implement the in-app domain without requiring an external provider.

Initial categories:

- `monitoring.risk_alert`;
- `schedule.status`;
- `job.status`;
- `account.lifecycle`.

Product notifications default off where user preference is appropriate. Content is bounded and must not contain raw strategies, reports, sources, private documents, support descriptions, credentials, or provider payloads.

Support severity, quiet hours, digest preferences, idempotent intents, lifecycle, retention, accessibility, and tenant isolation.

### External notification architecture

A real email, messaging, or delivery provider is not required for portfolio completion.

Preferred demonstration boundary:

```text
NotificationAdapter
  -> InAppAdapter
  -> FakeEmailAdapter
  -> optional SignedWebhookSandboxAdapter
```

A synthetic webhook adapter may demonstrate signatures, replay protection, SSRF defenses, retry/dead-letter handling, idempotency, redaction, and secret rotation without enabling uncontrolled external delivery in the public demo.

Telegram and real transactional-email providers are deferred to productization.

### Entitlements and metering

Implement versioned server-owned plan and entitlement architecture because it demonstrates mature SaaS backend design.

Initial plan:

`free-v1`

It mirrors the existing server-owned policy and adds the portfolio schedule limit:

- 25 analyses/day;
- 100 simulations/day;
- 100 options analyses/day;
- 100 market-data fetches/day;
- 50 active saved theses;
- 25 active watchlists;
- 5 active schedules.

An optional `portfolio-pro-preview-v1` may exist only for tests/demonstration. It has no public price and cannot be purchased.

Initial non-billable usage units should cover:

- completed analysis reports;
- completed simulations;
- completed options analyses;
- successful schedule runs.

Failed, rejected, canceled, quota-denied, or incomplete actions do not count. Retries must not double meter. Corrections use immutable reversals/adjustments.

Usage and entitlements remain separate from network limits, operational telemetry, analytics, and existing quota counters.

### Organization workflows

Keep the technically valuable organization work while removing commercial-provider dependence:

- hashed one-time invitations;
- seven-day expiry;
- resend/revoke invalidation;
- pending invitations reserve seats;
- five active-or-reserved seats for the portfolio plan;
- owner/admin invitation authority;
- atomic final-seat checks;
- ownership transfer with recent authentication;
- explicit organization export/deletion authority;
- billing-contact fields, if retained, remain metadata only and grant no authorization.

Organizations already above a new synthetic seat limit are not destructively modified; new invitations are blocked until they return within the limit or receive another test entitlement.

### Support, status, and privacy requests

Implement only the provider-free architecture necessary to demonstrate bounded customer operations:

- `support`;
- `feedback`;
- `abuse_report`;
- `privacy_access_export`;
- `privacy_deletion`.

Use first-party request tracking with bounded text, explicit state transitions, tenant isolation, audit linkage, and reuse of existing Phase 16 export/deletion authorities.

No attachments initially. Request bodies are excluded from analytics, normal logs, and automatic LLM processing.

A simple public-safe status page/process is sufficient. Subscriber email collection and external helpdesk/status providers are deferred.

---

## 5. Portfolio deployment boundary

The public demo is intentionally constrained.

Portfolio completion does not imply activation of every implemented production-capable feature.

The following may remain disabled in the public deployment:

- optional product analytics collection;
- private durable RAG/storage cutover;
- real Vast.ai rentals;
- external notification delivery;
- payment and billing providers;
- paid plans;
- external support/helpdesk providers;
- customer-facing webhooks;
- production model/provider routes that lack completed operational evidence.

Synthetic and first-party implementations may still be considered complete when their required code, migration, security, lifecycle, concurrency, failure, and rollback evidence pass.

---

## 6. Portfolio definition of done

A portfolio slice is complete when:

1. the implementation matches the selected portfolio scope;
2. tenant and authorization boundaries are explicit and tested;
3. migrations are reversible and tested on PostgreSQL where relevant;
4. normal, failure, retry, concurrency, cancellation, deletion, and recovery behavior is tested;
5. client-controlled values cannot grant authorization, plan state, provider state, or trusted data;
6. synthetic/provider-disabled paths fail safely;
7. public demo behavior remains bounded and non-sensitive;
8. CI and security checks are green;
9. docs describe implemented versus disabled behavior accurately;
10. product-only activation requirements are preserved in the productization backlog instead of being falsely marked complete.

Phase 20J may therefore close Phase 20 as **Complete — Portfolio Profile** without claiming legal certification, paid-launch readiness, or live provider activation.

---

## 7. Conversion back to a product

The portfolio architecture must preserve clean adapter and policy boundaries so productization is incremental rather than a rewrite.

The conversion path is:

```text
portfolio-complete architecture
  -> choose target markets and commercial model
  -> qualified legal/privacy/tax review
  -> complete provider ADRs and contracts
  -> configure production telemetry/operations evidence
  -> activate production storage/providers behind existing interfaces
  -> validate billing and external delivery in sandbox
  -> run controlled deployment and migration evidence
  -> Phase 22 product launch validation
  -> explicitly enable commercial capabilities
```

Real provider integrations must plug into reviewed interfaces rather than become new sources of authorization or business truth.

Provider callbacks remain inputs to reconciliation. Server-owned normalized state remains authoritative.

---

## 8. Permanent non-goals

The portfolio profile does not add:

- wallet connection;
- transaction signing;
- custody;
- automated trade execution;
- personalized financial advice;
- client-controlled entitlements;
- browser-controlled billing state;
- automatic trust of discovered sources;
- secrets in browser configuration;
- real paid-provider use in CI;
- claims that disabled or synthetic capabilities are commercially live.
