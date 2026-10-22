# Portfolio Completion Contract — Research Copilot and Personal Monitoring

Status: **TARGET CONTRACT / NOT IMPLEMENTATION ACCEPTANCE** (2026-10-22).
Profile: **portfolio-first + restricted personal research**, not commercial SaaS.
Phase 22 remains **ACTIVE — HOLD** until enabled-scope gates below pass.
This contract changes the definition of *portfolio completion*, not the historical acceptance of Phases 0–21, and does not authorize deployment, merge, workers, model providers, or owner-reserved R3 decisions.

Read with [portfolio profile](portfolio_profile.md), [current state](current_state.md), [finalization plan](portfolio_finalization_plan.md), [agent design](agent_design.md), and [productization backlog](productization_backlog.md).
This document governs *future scope/acceptance*, never overrides security, data ownership, deterministic risk authority, existing approved phase contracts, or the owner decision table.

## 1. User outcome and definition of completion

The project is finished for this profile when its owner can use a deployed, access-controlled DeFi research workspace to:

1. Enter or revisit a thesis; identify the protocols, assumptions, missing inputs, and risks.
2. Research it through bounded, source-grounded retrieval and current or clearly labeled cached/manual market data.
3. Run deterministic risk scoring, stress scenarios, and options analysis where relevant.
4. Request deeper multi-step AI research and obtain a reviewed, attributable report with sources, dated observations, uncertainty, contradictions, and actionable *research questions* rather than capital-execution instructions.
5. Save, reopen, compare, and export reports/thesis revisions.
6. Configure a private, user-owned scheduled watch that reevaluates an approved monitoring target and surfaces source changes, stale inputs, deterministic thresholds, or material thesis changes in the in-app notification center.

A public read-only/synthetic demo may remain less capable than the authenticated personal workspace. Do not call a disabled route, stub, sample report, or mock LLM a live end-to-end feature. For *personal-ready* signoff, one actual end-to-end enabled personal research run and one safely executed scheduled monitoring occurrence must be demonstrated. An agent orchestration test must include real tool boundaries; model quality and factual claims require source checks, not persuasive prose.

No wallet connectivity, signing, custody, execution, automated allocation, guaranteed yield, or personalized trade advice.

## 2. Current capability versus intended flow

The checked-in repository already documents:
- Deterministic analysis, market adapters, RAG over curated/public sources, simulations, options, persisted reports/exports, revisions/comparisons, discovery and a human review queue.
- Optional report synthesis with model/prompt governance and explicit promotion; `LLM_SYNTHESIS_ENABLED=false` remains the default.
- Phase 17 durable jobs/workers and Phase 20C durable user-owned schedules/Phase 20D in-app notifications as implemented foundations; production schedule dispatch remains disabled.
- Phase 21D research intelligence (assumptions, catalysts, staleness, scenario diffs, monitoring questions), implemented deterministically rather than by an autonomous deep-research model.

These components do **not** establish an enabled iterative research agent, an activated production AI provider, or a qualified scheduled private workflow. Those are integration/acceptance tasks.

**Worker** = execution substrate (claim, lease, cancellation, progress, retry, idempotent completion).
**Research agent** = bounded logical orchestration of research tools, models, and deterministic calculations. Multiple logical research steps need not mean multiple distributed worker processes.

## 3. Research Copilot workflow and contracts

```text
Owner-owned thesis / research request
 -> authorize subject + resources, record run budget
 -> parse strategy, identify entities and unanswered questions
 -> retrieve curated/approved protocol evidence + provenance
 -> fetch bounded public or owner-supplied market observations
 -> deterministic scoring, scenarios, options (as applicable)
 -> bounded model-assisted synthesis + verification
 -> optional follow-up research on explicit evidence gaps (bounded)
 -> report with dated sources, assumptions, contradictions, confidence and limits
 -> persist versioned result; compare/export; optionally create an owner-approved watch
```

Minimum orchestration contract:
- Tool-call allowlist, typed inputs/outputs, maximum steps, wall-time/token/cost budget, cancellation points, and progress state; no unbounded recursive search.
- Separate verified facts/calculations from LLM interpretation; preserve immutable risk fields, market values, sources, disclaimers, and missing-data indicators.
- Attach source URLs/versions/retrieval timestamps, observation timestamps, and explicit stale/cache/manual/synthetic labels. Unavailable data is recorded, not filled by the LLM.
- Treat web/RAG content as untrusted instructions. Discovery and evaluation do not imply `approved_for_rag`; approval and ingestion are separate human actions.
- A model failure or no approved route produces a truthful deterministic report. Only claim *AI-assisted* for a successful approved model call; do not leak private thesis text to an unapproved provider.
- The owner can inspect the run history, cancel if supported, regenerate with changed inputs, and identify the model and tool provenance. The agent cannot approve its own sources or take market positions.

Minimum acceptance demonstration: a nontrivial strategy investigated across at least two attributable source types; a genuine approved-model explanatory step; two bounded research iterations or one justified stop based on retrieved evidence; risk/stress calculation; visible unknowns and source freshness; report persist/reopen/compare/export; one safe deterministic fallback on model/tool failure.

## 4. Scheduled monitoring — REQUIRED for personal-ready profile

Use the existing Phase 20C user-owned schedule and Phase 20D notification foundations rather than inventing a separate scheduler. Required target: an owner-approved saved thesis/watch, selected deterministic thresholds, source-staleness checks, and optionally a bounded research question.

**User experience:** create/edit/pause/resume/delete a watch, inspect next scheduled run and last outcome, run it manually, receive an in-app notification only for a meaningful change or failure requiring attention, open the linked report/diff, and acknowledge/dismiss without exposure of private strategy content in notification metadata.

**Execution contract:**
- Authenticated ownership and tenant scope must be derived server-side and rechecked when a due occurrence is claimed and completed. Never allow one user to inspect another user's targets or notifications.
- Retain the existing initial portfolio limits unless formally revised: minimum cadence **one hour**, at most **five active schedules per user**, hourly/6-hourly/daily/weekly presets, timezone-aware/DST behavior, missed-run coalescing, skip occurrences over 24 hours overdue, and 30-day run history.
- PostgreSQL due-row one-winner claim, idempotent occurrence identity, atomic job/capacity accounting, generation/lease fencing, safe retries/backoff, and fail-closed behavior after cancellation, deletion, revocation, or restore uncertainty.
- Each occurrence must use a bounded source/data refresh and deterministic comparison first. Invoke optional LLM follow-up **only** under explicit owner/provider/privacy approval and cost controls; never require an LLM for an ordinary no-change tick.
- Store evaluation timestamp, data freshness, source provenance, baseline/report version, changed metrics, skipped/missing inputs, reason for alert/no-alert, and execution outcome. Do not send raw confidential report text in alerts.
- Scheduled monitoring and worker dispatch stay **OFF** in public/production configuration until the exact enabled code paths pass temporal/concurrency/TLS/tenant and deployment gates. A simulated schedule cannot be presented as active monitoring.
- External email/Telegram/webhook delivery and 24/7 availability are not required. In-app delivery is sufficient.

Acceptance demonstration: at least one real isolated authenticated hourly-equivalent occurrence (time may be advanced in a controlled disposable test), one unchanged run with no duplicate notification, one changed-source/threshold alert, one restart/retry, concurrent dispatch with one winner, one cancellation/deletion, and one safe denial/fail-closed temporal anomaly. For the restricted personal environment, demonstrate actual configured scheduled execution before declaring the capability enabled.

## 5. Security and temporal correctness — never waived

**Hard invariants:** user/tenant isolation; no secret exposure; TLS and approved worker origin for credentials; server-owned authorization; no stale-generation execution; no duplicate capacity release; no terminal cancellation with active unaccounted lease; transactionally consistent state; non-overridable deterministic fields; prompt-injection boundaries; reviewed source trust.

The sealed *local* R3.26–R3.31 evidence is not integrated into checked-in `main`. The supplied R3.32-R reviewer report describes a verified experimental chain but rejects application integration pending:
- Strict `decision_time < deadline` (equality must not be eligible).
- Eligibility derived **after** acquisition of relevant locks; pre-lock witness tickets must not silently advance decision time.
- Defined post-sample-to-commit/response semantics and lease safety.
- A single documented lock order for claims, acknowledgements, cancellation, recovery, and reconciliation.
- Explicit owner-approved forward-clock-jump rule. Until authorized detection/reconciliation behavior is defined, anomalous time samples must fail closed, without silently expiring leases or releasing capacity.
- A restore/replay gate demonstrably remaining closed until state/generation/capacity reconciliation. Same-host witness evidence is a *portfolio simulation*, not independent recovery authority.

Preferred **experimental** direction: PostgreSQL persisted decision-time floor with labeled simulated restore gate, behind disabled-by-default feature flags, only after bounded corrections, owner approval, and review. A global floor is **not approved** for application integration or production. Disabled workers/schedules need not block deterministic read-only portfolio demo signoff, but **personal-ready with monitoring enabled** cannot waive these invariants.

The earlier R3.31 portfolio performance targets (throughput decrease <=30%; relative p99 increase <=50% at measured concurrency 1/4/8) are *provisional portfolio evaluation rules*, not production SLOs. Record absolute p99; c32 is stress diagnosis, not a gate. Preserve original failed repeats and unresolved historical regression; no fresh c2/c3 benchmarking is mandatory absent a correctness reason.

## 6. Bounded completion gates

- **G0 Evidence/release scope:** reconcile checked-in `main` with the exact sealed R3 source lineage; independently verify manifests and retained blockers; select an integration candidate explicitly; keep ten R3.15 owner decisions pending unless individually decided.
- **G1 Personal research:** authorized end-to-end research run with real approved LLM and tool/RAG integration; deterministic fallback; bounded steps/cost; source/claim verification.
- **G2 Analytical workspace:** deterministic scoring, stress/options, data freshness, saved report/revisions/comparison/export and user-facing UX pass.
- **G3 Private monitoring:** due dispatch, one-winner, idempotency, replay/cancel/recovery, in-app change alert, audit/freshness and privacy gates pass on the *enabled* candidate.
- **G4 Security, persistence, deploy:** actual built image starts without source mounts; exact-context controls; PG16/17 tests relevant to changed paths; isolated authentication/TLS tests; migrations, restart and local restore checked; public demo defaults remain restricted.
- **G5 Portfolio release:** owner signoff on a fixed candidate and enabled-feature matrix; focused regression and real browser/deployed smoke; reproducible demo walkthrough, accurate README/current_state and disabled-feature labels. Archive evidence and unresolved deferred failures.

Run a **bounded** test matrix: focused changed-path tests, one standard relevant full regression on the final candidate, and exact-head built-image/browser smoke; rerun only a failing test to diagnose it and preserve the first failure. Do not create unending test cycles merely to obtain a green rerun.

A failure is not automatically a release blocker if causally proven confined to a disabled/nonshipping path; mark and preserve it. A security, tenancy, or integrity defect affecting enabled personal workflows **is** a blocker. No author may infer correctness solely from a final green rerun.

## 7. Out of scope for portfolio closure

Commercial billing/paid plans, independent witness infrastructure, managed multi-region failover, enterprise RPO/RTO, customer support provider, external notifications, continuous autonomous agents, GPU rentals, training/fine-tuning, and mass-concurrent worker fleets remain deferred. A basic tested local backup/restore procedure for personal data and a documented recovery limitation are required if personal persistence is enabled.

All source/owner decisions and R3.13/R3.14/R3.19 historical failure records remain preserved with their existing status. The owner must approve forward-jump semantics and any affected R3.15 source disposition separately. The completion decision is **PORTFOLIO_COMPLETE / PERSONAL_RESEARCH_READY**, not commercial launch or general production safety certification.
