# Phase 22 F0 — Portfolio Source Reconciliation and Readiness Handoff

**Review date:** 2026-10-22  
**Scope:** F0 read-only source reconciliation, evidence verification, implementation inventory, blocker classification, and bounded roadmap.  
**Phase state:** ACTIVE — HOLD. F1–F5 are not authorized by this handoff.

## Required statuses

- F0_SOURCE_IDENTITY_STATUS: VERIFIED. Repository is publiomcko-cloud/defi-thesis-risk-copilot. Remote main is 1574d83ab7c0ea0eebef22d0f2d00bc3ce2ed176. Draft PR #42 was open and unmerged at review start, based on that main commit; its reviewed head was 7515e4a640188c676691bc3e50f0f787f4077cc8 on docs/portfolio-research-copilot-finalization-20261022.
- F0_R3_EVIDENCE_PROVENANCE_STATUS: R3.26–R3.31 sealed archive hashes and available manifests verified locally. R3.32-R report findings are present in the inherited session record (reported digest 5a56cd90d3e7bab32fbbdcfea169352eb9e7804fd9329430020af036ba58584f), but a standalone report file was not found in the recovery tree. See evidence-access limitation below.
- F0_RESEARCH_COPILOT_IMPLEMENTATION_STATUS: Deterministic research and report foundations are implemented. Optional one-pass LLM synthesis is implemented but disabled by default and requires a promoted, scope-approved route. A bounded iterative AI research agent is MISSING. No end-to-end personal LLM run or deployment was verified.
- F0_SCHEDULED_MONITORING_IMPLEMENTATION_STATUS: User-owned watchlist schedule CRUD, timezone handling, durable occurrences, job linkage, history, and in-app notifications are implemented foundations. Schedule editing and manual run are MISSING; saved-thesis evaluation is MISSING; dispatch and workers are disabled by code defaults and are not qualified for activation.
- F0_TEMPORAL_BLOCKER_CLASSIFICATION: R3 time, lease, locking, rollback, and recovery issues BLOCK worker-backed asynchronous research and scheduled dispatch. They do not block a bounded synchronous deterministic research path that does not use worker leases or the experimental time floor.
- F0_HISTORICAL_FAILURE_STATUS: Seven historical failures remain PRESERVED_OPEN, H1–H7; none was resolved or reclassified here.
- F0_OWNER_DECISION_REGISTER_STATUS: All ten R3.15 source decisions remain PENDING_EXPLICIT_OWNER_DECISION; accepted_by_agent remains zero.
- F0_F1_IMPLEMENTATION_READINESS: CONDITIONAL GO for a narrow synchronous F1 after a separate F1 authorization and explicit owner approval of the real model route, privacy boundary, and run budgets. Do not route F1 through the current async worker path while its temporal gate is unresolved.
- F0_F2_F3_MONITORING_READINESS: NO-GO for enabled worker or schedule dispatch until F2 owner decisions, temporal fixes, and targeted PostgreSQL evidence pass.
- F0_RECOVERABLE_CHECKPOINT_STATUS: PARTIAL. This handoff and checksum are portable on PR #42. R3.26–R3.31 evidence remains local under /home/publio/phase22-recovery and is not published on GitHub. No standalone R3.32-R report file was found.
- F0_FINAL_VERDICT: PARTIAL_WITH_EXPLICIT_BLOCKERS. Recommendation: conditional GO for isolated synchronous F1; NO-GO for temporal-floor integration, async worker enablement, or scheduled dispatch pending the blockers below. This is a readiness recommendation, not authorization to proceed beyond F0.

## Source identity and documentation reviewed

The current source authority was the remote main commit 1574d83ab7c0ea0eebef22d0f2d00bc3ce2ed176, not the dirty local application checkout. PR #42 was reviewed as a proposed documentation overlay at head 7515e4a640188c676691bc3e50f0f787f4077cc8. It was draft, unmerged, and based directly on main. The required portfolio contract, finalization plan, profile, current state, development plan, agent design, agent execution guide, and productization backlog were read from that PR branch. Application code and tests were inspected at exact main.

The application audit covered backend/app/agents, api, auth, core/config.py, data_sources, jobs, knowledge, llm, models, notifications, rag, research_intelligence, risk, scheduling, services, simulation, options, theses, and frontend research, thesis, report, job, schedule, and notification components. Relevant tests are present in the repository, including test_analysis_workflow.py, test_llm_synthesis.py, test_market_data_adapters.py, test_risk_scoring.py, test_strategy_simulator.py, test_options_analysis.py, test_phase17d_async_analysis.py, test_phase20c_postgres_schedules.py, test_phase20c_scheduled_monitoring.py, test_phase20d_notifications.py, test_phase20d_postgres_notifications.py, and test_phase21d_research_intelligence.py. They were not executed in this F0 review.

Checked-in defaults in backend/app/core/config.py are llm_synthesis_enabled=false, llm_provider=disabled, auth_enabled=false, knowledge_pgvector_primary_enabled=false, schedule_dispatch_enabled=false, jobs_enabled=false, worker_api_enabled=false, async_analysis_enabled=false, and vast_real_rentals_enabled=false. These are source defaults, not a reading of deployed environment settings. The documentation describes main as the live branch; no production endpoint, provider setting, deployment, or worker state was inspected.

## Sealed R3 evidence and SHA-256 manifest

The following archives were present under /home/publio/phase22-recovery. Archive digests were recomputed and matched the sealed identities. The R3.26 source archive contained 702 files; every member matched the 702-entry manifest and the manifest recorded the required tree digest. R3.30 and both R3.31 packages matched their member manifests. R3.31’s addendum embeds the base package manifest hash and preserves the original archive identity.

| Evidence | Archive SHA-256 | Manifest or identity |
| --- | --- | --- |
| R3.26 source | a5eb9f63611682858f89c2b8959ba0fb3b2cb410056ed07881189c017dc7aa73 | 702 files; tree 2a8fad74960cf3f77091f32324b6ce344ce15c0a6f970493e3a1542b4134a21d; manifest 7d98aba471e32490d4ec4d42d4ffcfd9a9bb20c435b31e8b062cb5b3cacf3db5 |
| R3.26 evidence | d667f7432243932023bf01963c898499ed0e767c894904aab3313f92205b8a35 | sidecar and sealed-input verification match |
| R3.27 evidence | 984273ac30ecb4745c5be9f8985bbaff6cd62819fea8e11ea09a42097d8b2fae | package manifest 6a1aa3af985c80d78373e84b33f06ad5990798d397e58b390c99540ae7ab031c |
| R3.28 candidate source | a5eb9f63611682858f89c2b8959ba0fb3b2cb410056ed07881189c017dc7aa73 | same R3.26 source identity |
| R3.28 evidence | c3ac607058493fe61145e04cd50b9acaddce4c89dc37001fb941f893fe0b3c28 | validation manifest ac7f913a3686e6644b4096bd80f66fe49111d56cea79f26c55a93f58fe85713a |
| R3.29 qualification | c49d969a8ac9fe22bb05107d26f8e856172491cb6bc5d01269b31730dbf180bf | package manifest 84b2b03e8d185479d189aeeaec03713b9d7ec1633355decfdd285cb8aabefab5 |
| R3.30 evidence | a8867c1b091088d0a142450b4aa00f8e381c0a3f9a2f78309ae9196745c2f5d1 | 220 manifest-listed files; manifest a871385f7db1b5f1ea1232fb518999364adc5bf00a2af593eef8a04862c6b773 |
| R3.31 original package | 0408385cf7e94d9d6ee3f6f1e8b4b9b9075cbcacc53b78e26ff746515d842c1a | 58 manifest-listed files; manifest 43670a7b92ad0cd4e8837ad0477c63e83df33ab906579cc141072096a83c7a8b |
| R3.31 portfolio addendum | 74e9986e1bc3665bd49acd56d94b97fc5562eb8a838c466a4450c1486a274811 | 32 manifest-listed files; manifest c5d092fa045cb923e8cd47f035dd7d695e240edb8c98695da26c1aa165caf988 |

R3.27 carries forward the R3.26 source identity; R3.28 and R3.29 preserve that lineage. R3.30’s sealed final provenance reports the R3.26–R3.29 chain clean and its application source unmodified. R3.31 binds to those verified inputs, and the addendum binds to the exact R3.31 original package above.

R3.26’s six changed application paths are backend/app/jobs/control_service.py, lifecycle.py, worker_protocol.py and three focused tests for capacity atomicity, PostgreSQL deadline behavior, and worker protocol v2. These are candidate files only. The persisted time-floor prototype and local witness remain experiments; no R3 candidate is integrated in main. The absence of the floor from main is expected and does not invalidate the evidence.

The corrected R3.32-R review report itself was not available as a separately verifiable file. The inherited session record provides its reported digest and conclusions; R3.26–R3.31 source and evidence packages were checked directly. /mnt/e/projetos/phase22-recovery exists but contains older R3.10/R3.11 artifacts, not a duplicate R3.26–R3.31 chain. Do not tell a future reviewer that the full R3 archives or the R3.32-R report can be downloaded from GitHub.

## Portfolio performance assessment

The portfolio profile sets relative limits of at most 30% throughput degradation and at most 50% p99 increase. c1 and c8 used three repeats; c4 used ten repeats per PostgreSQL version and mode. c4 runs used 32 jobs per trial, durable PostgreSQL settings, and one local simulated witness. The c4 comparison pools acknowledgement operation samples across ten runs and also reports the median of per-trial p99 values; with only 32 jobs in one trial, a trial-level p99 is effectively its maximum.

| PostgreSQL / concurrency | Repeats | Throughput degradation | Acknowledgement p99 change | Absolute persisted-floor acknowledgement p99 |
| --- | ---: | ---: | ---: | ---: |
| PG16 c1 | 3 | 0.84% | -6.75% | 126 ms |
| PG16 c4 | 10 | 6.00% | +6.12% pooled; +39.50% median-trial | 2.807 s pooled |
| PG16 c8 | 3 | 4.07% | +16.55% | 3.755 s |
| PG17 c1 | 3 | 2.67% | -3.76% | 122 ms |
| PG17 c4 | 10 | 5.18% | +33.53% pooled; +33.36% median-trial | 3.281 s pooled |
| PG17 c8 | 3 | 0.34% | +24.21% | 3.890 s |

Measured c1/c4/c8 results meet the revised relative portfolio targets. c4 baseline versus floor pooled p99 was 2.645 s versus 2.807 s on PG16 and 2.457 s versus 3.281 s on PG17. Median-trial p99 changes differ from pooled changes, so both are retained. c4 median-trial throughput loss was about 9.00% PG16 and 5.91% PG17, versus aggregate losses of 6.00% and 5.18%.

The initial three-repeat c4 estimate exceeded the new p99 limit: +90.87% PG16 and +81.84% PG17. It is preserved. Seven added repeats reduced the small-sample maximum sensitivity; the ten-run pooled and median-trial comparisons pass. The early estimate is not erased or described as a resolved defect.

R3.30’s PG16 c8 +38.94% p99 regression remains an unresolved historical observation. The matched R3.31 three-repeat rerun measured +16.55% PG16 and +24.21% PG17 but did not identify the original cause. The old value is below the revised 50% portfolio limit, while its cause remains open.

Absolute tail latency is seconds at c4/c8 and no absolute acceptance ceiling was supplied. c2/c3 were not measured. c32 is diagnostic only; persisted-floor acknowledgement p99 was about 27.564 s on PG16 and 23.183 s on PG17 and is not a portfolio compliance gate. c4 data showed substantial local witness operation_in_flight polling and no sampled PostgreSQL blocking PID or resource saturation; this supports local witness queueing as a tail contributor, not a production latency claim. No repeat benchmark is required for this F0 conclusion.

## Capability inventory at main

“Tests present” means matching test files exist; F0 did not run them. “Deployed” is not independently verified.

| Capability | Implementation and status |
| --- | --- |
| Protocol research and source retrieval | IMPLEMENTED and present in the synchronous analysis workflow: strategy parsing, curated retrieval, market-data fetch, deterministic scoring, and report writing. Curated JSON retrieval is the normal fallback. Public durable retrieval filters for approved_for_rag. ENABLED for the synchronous code path; TESTED by workflow/retrieval tests present; DEPLOYED unverified. No iterative follow-up agent. |
| RAG, citations, freshness, source trust | IMPLEMENTED: source citations/lineage, human trust-state gating for durable public retrieval, authenticated knowledge APIs, and report staleness are present. Curated local retrieval is active; private/durable pgvector and shadow paths are feature-gated off by default. TESTED by knowledge/citation tests present; production cutover DEPLOYED unverified. |
| Public and approved market data | IMPLEMENTED adapters include manual, Aave, Morpho, Pendle, DefiLlama, and CoinGecko, with cache and missing-field reporting. ENABLED in code; TESTED by adapter tests present; live upstream success and DEPLOYED status unverified. |
| Deterministic risk scoring | IMPLEMENTED, ENABLED in the analysis and simulation code, with missing-data-aware scores and tests present. No R3 worker-time dependency in the direct synchronous path. DEPLOYED unverified. |
| Strategy and stress simulation | IMPLEMENTED deterministic simulation APIs and UI, with tests present. ENABLED in code; DEPLOYED unverified. |
| Options analysis | IMPLEMENTED deterministic API and UI with tests present. ENABLED in code; DEPLOYED unverified. |
| LLM synthesis and model governance | IMPLEMENTED one-pass explanatory synthesis, route promotion/evidence checks, provenance, output quality validation, and deterministic fallback. DISABLED by checked-in default (llm_synthesis_enabled=false; provider=disabled). A real promoted private-scope route and live approved provider were not inspected or enabled. TESTED by synthesis/governance tests present; DEPLOYED unverified. |
| Bounded multi-step AI research | MISSING. app/agents/orchestrator.py is a fixed one-pass sequence; Phase 21 research intelligence is deterministic metadata and comparison, not an LLM tool loop. No operation should call this live agentic research. |
| Saved thesis, history, revisions, comparisons | IMPLEMENTED authenticated thesis CRUD, revision history, assumptions/catalysts, report comparison, and source-staleness APIs/UI. Authentication is off by default in Settings. Current analyze links pass strategy text rather than a stable thesis-to-run/report relationship; F1/F4 need that linkage. TESTED by research-intelligence tests present; DEPLOYED unverified. |
| Reports and exports | IMPLEMENTED persistence, reopen, Markdown export, source lineage, and deterministic report comparison. Tests present. ENABLED in code; personal authenticated end-to-end behavior and DEPLOYED status unverified. |
| Authentication and user workflows | IMPLEMENTED Supabase/BFF/authenticated API paths and private user screens. Source default auth_enabled=false; production configuration was not read. Do not call an authenticated personal workflow ENABLED or DEPLOYED on this review alone. |
| Async research, progress, cancellation, retry | IMPLEMENTED Phase 17 job submission, idempotency, job events/progress, cancellation request, worker leases, and deterministic worker fallback. async_analysis_enabled, jobs_enabled, and worker_api_enabled default false. The worker path is BLOCKED for activation pending temporal, lease, lock-order, rollback, and recovery proof. |
| User-owned schedules | IMPLEMENTED create/list/pause/resume/delete/history for authenticated owners; hourly, six-hourly, daily, and weekly cadences; timezone/DST rules; five-active-schedule cap; 24-hour overdue skip/coalescing; 30-day history. There is no schedule edit or manual-run route. Target is watchlist.evaluate, not a saved thesis. |
| Automatic scheduled dispatch | IMPLEMENTED dispatcher and durable occurrence/job transaction, but schedule_dispatch_enabled defaults false. No production worker/dispatcher was activated or inspected. ENABLED/DEPLOYED status is unverified; temporal qualification BLOCKS activation. |
| In-app notifications | IMPLEMENTED authenticated notification center, preferences, read state, and idempotent schedule/job/watchlist notification intents. No external provider is needed or enabled. Tests present; real scheduled occurrence delivery DEPLOYED unverified. |

## Temporal, lease, transaction, and recovery review

The PostgreSQL persisted floor is the preferred measured time-ordering architecture for a portfolio implementation because it gives a simple database-local nondecreasing decision-time sample after required locks and meets the observed c1/c4/c8 relative targets. It is not a standalone production recovery authority: PostgreSQL PITR or asynchronous failover can restore an older floor, and the floor does not detect forward clock jumps. Use it only with explicit restore/replay generation fencing and a fail-closed restore gate. Do not substitute a pre-lock external witness ticket as the eligibility time.

The isolated implementation gate must require all of the following:

1. Eligibility is checked using an authoritative sample taken only after the relevant job and capacity locks are held. Require decision_time < deadline and decision_time < lease_until; equality is expired. A ticket obtained before lock wait cannot confer eligibility.
2. Document whether eligibility is a decision-time guarantee or must remain valid through commit/response. Fence stale generations and tokens at commit so a delayed worker cannot mutate state after cancellation, reassignment, or recovery. Do not promise that a decision-time sample guarantees a response before expiry.
3. Define one lock order and apply it across claim, capacity reservation/release, ACK, cancellation, recovery, and schedule dispatch. Preserve one-winner and cross-scope capacity invariants.
4. Commit job state, lease generation, capacity accounting, schedule occurrence, idempotency identity, and any notification/outbox record transactionally or through a proven reconciliation protocol. Lost ACK, duplicate replay, rollback, retry, and cancellation must not produce double release, a second report, or orphaned capacity.
5. On database rollback, restore, or unknown generation, stop eligibility decisions until the generation/floor is checked and reconciliation completes. Never silently accept a restored lower floor or stale worker.
6. Keep the restore witness’s actual topology explicit. Existing evidence uses same-host PostgreSQL and a loopback SQLite witness; it demonstrates simulated restore/replay fencing and fail-closed behavior, not independent host, storage, admin, network, PITR, or failover protection.

Forward-jump recommendation: pair the approved wall/database time observation with a monotonic elapsed-time observation and an owner-approved anomaly bound. The owner must choose the bound, observation window/source, treatment of legitimate clock correction, active-lease behavior, and reopen procedure; no numeric threshold is selected here. When a forward step is classified as anomalous, latch the temporal gate closed before eligibility decisions. Do not expire a lease, deadline, schedule, or capacity allowance solely because the wall clock jumped forward. Pause new claims and schedule dispatch; preserve generations and capacity state; record the anomaly; reopen only after explicit reconciliation confirms the selected time basis and all active work is safe. Until the owner selects semantics, time-sensitive worker paths fail closed and remain disabled.

R3.30 local restore/replay/failover injections and R3.31 witness-unavailable checks are sufficient portfolio evidence for a clearly labeled recovery simulation. They are not evidence of independent recovery protection. Enterprise HA, independent witness hosting, and multi-region recovery can stay deferred if those claims and features stay disabled.

## Enabled-path blockers versus deferred requirements

| Item | Affected scope | Classification |
| --- | --- | --- |
| Strict deadline/lease inequality, post-lock sample, lock ordering, cancellation/ACK-loss fencing, transactional capacity reconciliation, forward-jump semantics, restore-generation gate | Async analysis and scheduled monitoring | Critical blockers to enable these worker paths. |
| Same issues | Direct synchronous deterministic analysis and bounded synchronous F1 | Not a demonstrated blocker if the path avoids the worker/time-floor prototype and maintains existing authorization, source trust, deterministic scoring, provider and report rules. |
| Independent witness, commercial HA/failover, multi-region operation, commercial billing, external notification providers, VAST rentals | Disabled/deferred commercial/enterprise scope | Not F1 portfolio blockers while demonstrably disabled and not represented as live. |
| Absolute p99 ceiling | Personal responsiveness decision | Not set. Owner should decide whether observed seconds-long c4/c8 tails meet the intended use; do not infer an absolute target. |
| c2/c3 benchmarks | Performance evidence | Unmeasured; record as such. They do not overturn the specified c1/c4/c8 outcome. |

No R3 result proves that an already enabled deterministic route is unsafe. The critical integrity defects are blockers to enabling the affected lease/worker/scheduler paths. This conclusion is scoped to isolated application integration and does not assert production readiness.

## Historical failures and pending owner decisions

All historical failures remain open:

| ID | Historical finding | Portfolio scope note |
| --- | --- | --- |
| H1 | Original global-capacity failure (R3.13) | Keep open; worker/capacity invariants matter before async or schedule enablement. |
| H2 | VAST cancellation-cleanup failure (R3.14 PG16) | Keep open; VAST provider execution remains disabled/deferred. |
| H3 | Organization-capacity failure (R3.14 PG16) | Keep open; do not use organization-owned F1/F3 paths until specifically qualified. |
| H4 | VAST lost-completion failure (R3.14 PG17) | Keep open; VAST provider execution remains disabled/deferred. |
| H5 | VAST cancellation time-eligibility failure (R3.14 PG17) | Keep open; do not treat provider leases as qualified. |
| H6 | Intermittent full-suite SKIP LOCKED failure (R3.19 PG16) | Keep open; targeted worker/scheduler SKIP LOCKED evidence is required before enabling those paths. |
| H7 | Capacity failure during PostgreSQL clock rollback (R3.19 PG17) | Keep open; directly relevant to time-sensitive worker/scheduler capacity behavior. |

All ten R3.15 decisions remain PENDING_EXPLICIT_OWNER_DECISION. The historical recommendation column is not an approval:

| # | Path | Historical recommendation | Required gate |
| ---: | --- | --- | --- |
| 1 | .github/workflows/ci.yml | DEFER_PENDING_EVIDENCE | Hosted CI/workflow changes or final release evidence only. |
| 2 | .github/workflows/phase19-exercises.yml | DEFER_PENDING_EVIDENCE | Worker/recovery exercise workflow changes only. |
| 3 | Dockerfile.backend | ACCEPT_RECONSTRUCTED_SOURCE | No F1 dependency if unchanged; owner decision required before changing image/startup. |
| 4 | backend/app/jobs/control_service.py | DEFER_PENDING_EVIDENCE | Before using the worker control path for F2/F3 or async F1. |
| 5 | backend/app/tests/test_phase21e_postgres_migration.py | ACCEPT_RECONSTRUCTED_SOURCE | Before migration-test changes; schema changes require their own approval/evidence. |
| 6 | backend/app/tests/test_phase22_capacity_transition_atomicity.py | DEFER_PENDING_EVIDENCE | Before worker/schedule capacity transitions rely on that proof. |
| 7 | docker-compose.yml | ACCEPT_RECONSTRUCTED_SOURCE | Before changing local Compose behavior. |
| 8 | docker-compose.production.yml | DEFER_PENDING_EVIDENCE | Before production-like Compose or deployment changes. |
| 9 | docs/deployment.md | ACCEPT_RECONSTRUCTED_SOURCE | Before changing deployment instructions or using them for release signoff. |
| 10 | backend/app/tests/test_phase21c_postgres_migration.py | ACCEPT_RECONSTRUCTED_SOURCE | Before migration-test changes; hosted extension/privilege behavior remains open. |

Before a bounded F1 real-model run, the owner must separately approve the selected evaluated provider/route, private-data boundary, cost/run limits, and failure policy. Before F2/F3, the owner must decide clock-jump semantics, post-sample lease/commit behavior, lock ordering, rollback/recovery reconciliation, and exact isolated activation boundary. Before F5, decide whether absolute latency is acceptable and approve the final source/feature matrix. No decision was accepted here.

## F1–F5 bounded implementation roadmap

| Phase | Reuse and minimal work | Essential evidence and acceptance | Dependencies, complexity, risk |
| --- | --- | --- | --- |
| F1 — Bounded AI Research Copilot | Reuse run_analysis_workflow, ProtocolResearchAgent, existing market adapters, deterministic risk/scenario/options services, report writer, llm/routing.py and synthesis/provenance/quality gates, thesis/revision and report persistence. Add a narrow typed tool plan with owner-approved step/time/token/cost limits, at most the contract’s bounded follow-up when sources leave a material gap, and thesis-to-run/report linkage. Start synchronously; do not use async worker leases. | Test allowlisted tool I/O, malicious-source instruction handling, citation/claim validation, unchanged deterministic risk fields, stale/unavailable source labels, approved model success, provider timeout/error deterministic fallback, private tenant isolation, save/reopen/compare/export. Acceptance: a nontrivial research run across two attributable source types, one genuine approved model call, two bounded iterations or evidence-based stop, visible uncertainty/freshness, persisted report, and truthful fallback. | Requires next-phase authorization, selected evaluated real route, owner privacy/cost/budget decisions, existing source approval. Complexity: medium. Main risk: model claims or private data escaping source/tenant boundaries. |
| F2 — Safe worker and temporal prerequisites | Reuse Phase 17 jobs, leases, cancellation, PostgreSQL schedules and capacity accounting; use sealed R3 tests/reports as evidence, not as an automatic patch. Implement only owner-approved deadline/sample/lock/fencing/rollback/restore/forward-jump semantics. Keep worker and dispatch defaults off until the gate passes. | Targeted PG16/PG17 tests for strict equality, lock-wait eligibility, stale ticket rejection, lease/cancel/ACK races, consistent lock order, retry/replay, restored generation, fail-closed forward/backward step, transaction/capacity invariants, and recovery reconciliation. Acceptance: no stale or duplicate mutation, capacity reconciles, all anomaly paths fail closed, and one isolated worker succeeds under approved semantics. | Depends on owner decisions #4/#6 and time/lease/recovery policies. Complexity: high. Main risk: lease expiry races or restore/capacity inconsistency. |
| F3 — Scheduled watch and in-app alerts | Extend existing schedule service/UI; add schedule edit and manual run; bind an owner-approved saved thesis/watch and source freshness to deterministic comparisons; emit idempotent private alerts only for meaningful deltas. AI follow-up stays opt-in and budgeted; no LLM on no-change ticks. Keep current hourly minimum, five-active limit, timezone/DST, coalescing, >24-hour overdue skip, and 30-day history. | Targeted one-winner dispatch, DST, quota, overdue skip, no-change silence, changed-source alert, stale-data/upstream failure, tenant revoke/delete, duplicate notification, retry/restart/cancellation, restore and clock-anomaly closed gate. Acceptance: one actual isolated configured occurrence after F2 and owner activation. | Depends on F2, saved thesis linkage, notification privacy policy, exact private environment approval. Complexity: medium-high. Main risk: duplicate or cross-user events and unsafe work after pause/delete. |
| F4 — End-to-end application validation | Reuse existing auth/BFF, thesis, research, report, jobs, schedule and notification UI. Validate the exact selected flags and database in an isolated environment. | One full personal research walkthrough with real approved model and deterministic fallback; if monitoring is enabled, one real occurrence, alert, pause/delete, and no later dispatch. Check tenant boundaries, exports, source lineage, retry and rollback. Do not substitute sample/mock flows for live-path acceptance. | Depends on F1 and, for monitoring, F2/F3. Complexity: medium-high. No validation was run in F0. |
| F5 — Portfolio release and closure | Pin exact source and container digest; publish enabled/disabled matrix, evidence links, recovery-simulation limits, and deferred backlog. Obtain owner signoff and a reviewer identity record if independent review is claimed. | Reproducible public/demo and restricted personal acceptance for only the selected enabled paths; explicit decision that observed absolute latency is acceptable; no claim of commercial HA or independent restore protection. | Depends on F4, owner decisions, and release authorization. Complexity: low-medium. Main risk: reporting gated code as live or overstating recovery evidence. |

## Forward recovery instructions and provenance limits

A future reviewer should fetch repository publiomcko-cloud/defi-thesis-risk-copilot at main commit 1574d83ab7c0ea0eebef22d0f2d00bc3ce2ed176 and review PR #42 at the branch head recorded in its GitHub timeline. Read the eight portfolio documents from the PR branch and application implementation from exact main. Do not substitute a local application HEAD or treat the R3 candidates as merged source.

On the original host, the sealed archives are under /home/publio/phase22-recovery/r3.26 through r3.31. Verify each archive with SHA-256 before reading it; verify package manifests and R3.26’s 702-file source manifest. The manifest values above are the anchors. /mnt/e/projetos/phase22-recovery is not a current duplicate. The full archives, runtime databases, witness state, and credentials are not in GitHub; credentials and runtime state are not required for this portfolio handoff. If another reviewer lacks the local archive directory, the owner must provide the sealed artifacts separately before claiming a direct R3.32-R evidence re-review.

Reviewer provenance: OpenAI Codex agent in this session; authenticated human identity and independent second-party status are unavailable. R3.26–R3.31 evidence identifies itself as implementer-generated. This report makes no authenticated independent-review claim.

No source, migration, workflow, deployment, worker, model-provider, production, or owner-decision state was changed in F0. Phase 22 remains ACTIVE — HOLD.
