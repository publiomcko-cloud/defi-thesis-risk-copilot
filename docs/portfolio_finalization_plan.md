# Portfolio Finalization Plan — Deep Research and Scheduled Monitoring

Status: **PROPOSED EXECUTION PLAN / NO IMPLEMENTATION AUTHORIZATION**.
Target: [Portfolio Completion Contract](portfolio_completion_contract.md).
This is a forward-looking portfolio release sequence **inside Phase 22**, not a revision of historically completed Phases 17–21 or acceptance of local R3 experiments.

## Strategy

Build a useful owner-operated research application first; retain the deterministic core and strict trust boundaries. Complete bounded AI research and scheduled monitoring with the minimum safe execution topology, not an enterprise-grade worker fleet. Avoid repetitive architecture experiments and test loops without a new discriminating question.

Choose a clearly separated deployment profile:
- **Public demo:** anonymous/read-only and bounded deterministic analysis, with no private research ingestion, private provider keys, or scheduled worker dispatch.
- **Private owner research:** authenticated reports, approved optional LLM route and curated retrieval, persisted thesis history; scheduled monitoring **only after** qualifying actual worker temporal/capacity/recovery paths and owner-authorized activation.
- **Deferred commercial:** independent high-availability witness, managed failover, billing, external alert delivery, enterprise load, multi-region operation.

The existing deployed service and GitHub `main` are the source of truth for *current capabilities*. Local R3 archives are candidate/evidence only. Do not infer their integration or release approval.

## F0 — Evidence reconciliation and freeze

Deliver a source/evidence inventory: GitHub `main` HEAD, exact R3.26–R3.32-R parent/candidate identities, artifact locations, hashes, changed paths, owner decisions, historical-failure register, and included/excluded runtime features. Validate raw archives before importing changes. Treat the R3.32-R reviewer verdict as **NO-GO for current integration**: strict deadline equality, pre-lock witness eligibility, post-sample lease semantics, forward jumps and lock ordering still require resolution.

Exit when the owner can select an explicit candidate and knows which paths are safe to enable. No cherry-picking an unreviewed experimental migration, no production deploy, no implicit source disposition for R3.15 decisions.

## F1 — Bounded Research Copilot vertical slice

Implement a thin, observable orchestration layer using the existing market adapters, deterministic risk/scenario services, curated RAG, Phase 21 report/provenance machinery and one explicitly approved model route. Do not build autonomous general-purpose browsing or another independent job engine.

The minimal public/private API/UI contract should support initiating research, viewing progress and final report, optional bounded second research pass for missing evidence, model/provider fallback, saving/reopening/comparing/exporting, and cancellation only where that path is safe. The LLM writes explanatory claims, not financial facts or risk scores. Keep checked-in defaults disabled until authorized.

Validation: one documented real-source and real-approved-model example, one provider failure, one malicious-source injection, one stale market-data event, one private-tenant isolation check and deterministic computation parity. No live paid provider is needed in CI; validate a real provider separately with owner-approved cost/privacy controls.

## F2 — Temporal safety prerequisite for enabled schedules

Determine a safe private topology for monitor execution. Prefer reusing Phase 17 durable workers, Phase 20C schedules and Phase 20D in-app notifications. Do not enable dispatch while the R3 claim/cancel/recovery and time-authority hazards remain.

Bounded implementation candidates require separate owner approval and review:
1. Strict deadline predicate (exclude equality).
2. Locks acquired before authoritative decision-time sample; prevent stale pre-lock witness tickets from conferring eligibility.
3. Document decision-time guarantee vs possible later commit/response and prove lease fencing/state cleanup remains safe.
4. Order locks consistently across claim, cancel, ACK, recovery and capacity reconciliation.
5. Specify and implement owner-approved forward-jump anomaly policy; default fail-closed under unclassified anomalies.
6. If selecting persisted floor, use it as **database-local** temporal authority with a *clearly simulated* restore gate; never claim independent failover/PITR safety.
7. Verify TLS origin pinning, credential handling and actual image-startup/allowlist on the selected code candidate.

F2 may use a deliberately narrower safe scheduling mode for 1–4 owner-controlled concurrent operations. Simpler does not mean permitting inconsistent leases or cross-tenant data exposure.

Stop F2 and keep scheduling disabled if any of the enabled-path correctness conditions fails. This does **not** block F1 analytical portfolio completion; it blocks the stronger `PERSONAL_RESEARCH_READY_WITH_MONITORING` milestone.

## F3 — Scheduled watch and research follow-up

Create an owner-facing feature slice connecting existing schedules to bounded evaluation of saved thesis/watch metrics and source freshness, recording actual occurrences and emitting in-app notifications for meaningful deltas. Do not rerun expensive LLM research on every tick. Optional AI deep dives must be opt-in, budgeted and labeled.

Required tests: due-row one-winner, timezone/DST, at-most-one replacement after downtime, >24h overdue skip, hourly minimum, five-watch quota, tenant revoke/deletion, idempotent notification, no-change silence, stale-data warning, upstream outage, retry/recovery/cancel, forward-clock anomaly closed gate, one real running isolated configured schedule.

Schedule dispatch remains off until F2 passes and owner authorizes exactly which private environment may execute it.

## F4 — Product usability and portfolio showcase

Validate the shipped build with actual database configuration and selected flags (without unsafe public secrets). Required personal walkthrough:
1. Sign in, create thesis, research protocols and cite sources.
2. Run deterministic risk/stress analysis, request bounded LLM research, inspect unknowns/contradictions.
3. Save and compare two report versions; export Markdown.
4. Configure a watch, run a monitored occurrence, observe a meaningful in-app alert, pause/delete and verify no later dispatch.
5. Demonstrate failure/rollback safety without claiming enterprise recovery.

Capture screenshots/demo data using no sensitive positions, private keys or credentials. Update demo walkthrough, README, current state, deployment evidence (only after individually authorizing any R3.15-reserved path), testing and changelog once real behavior is validated.

## F5 — Release decision and closure

Select an exact source commit/container digest and enabled-feature matrix. Owner verifies G0–G5 in the completion contract. A reviewer with evidence independent of implementer claims should challenge critical authorization, state and temporal paths; if identity separation cannot be proven, say so rather than manufacturing authenticated approval.

Conclude as one or more explicit milestones:
- `PORTFOLIO_DEMO_COMPLETE`: public demonstration and deterministic analytics safely deployed.
- `PERSONAL_RESEARCH_READY`: actual authenticated bounded AI-assisted deep research runs successfully.
- `PERSONAL_RESEARCH_READY_WITH_MONITORING`: additionally, the scheduled watch path is safely enabled and validated end-to-end.
- `PRODUCTIZATION_DEFERRED`: billing, independent recovery authority, managed HA, external delivery, training/provider expansion.

Use **Phase 22 ACTIVE — HOLD** until the owner accepts the intended final enabled-profile gates; no local experimental R3 status changes that automatically. Leave unsupported external/product requirements in the productization backlog, not marked complete.

## Acceptance priorities and evidence discipline

- **Blocking**: data/tenant/credential exposure, fake citations, risk-score overrides, stale-worker side effects, inconsistent lease/capacity, unsafe scheduled execution, unverified live-provider private data policy, broken persistence on enabled paths.
- **Acceptable if explicitly labeled**: limited concurrent users, c32 stress tails, simulated witness/PITR demonstration, lack of enterprise SLO, disabled real billing/email/GPU, historical defects proven unreachable in shipped config.
- **Never claim resolved solely by rerun**: seven inherited R3 incidents, PG16/17 intermittent causes, R3.30 c8 regression.
- Benchmark only when deciding a concrete change; portfolio experimental comparison target is <=30% throughput loss, <=50% relative p99 increase at c1/c4/c8, with absolute latency recorded. These do not override transaction correctness.
- Prefer a single final combined focused + relevant full + image/browser validation per exact candidate. Preserve first failures, re-run diagnostically only, and prohibit open-ended qualification loops.

## Ownership and change management

ChatGPT prepares scope, risk decisions, acceptance contract and bounded Codex instructions; owner explicitly approves source changes, architecture semantics, flags, PR merge and release; implementer works in isolated branches/workspaces; independent reviewer verifies sealed identity and findings without silently certifying their own work.

All ten R3.15 owner decisions remain pending (notably Docker, control service, migrations, CI and deployment). Historical documentation and archives are immutable records, not artifacts to rewrite to match a new roadmap. Every step must state "implemented", "enabled", "tested", "reviewed", and "approved" separately.
