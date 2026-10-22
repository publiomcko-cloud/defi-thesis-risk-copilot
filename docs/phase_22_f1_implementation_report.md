# Phase 22 F1 — Implementation Evidence Report

**Review date:** 2026-10-22
**Phase:** ACTIVE — HOLD
**Scope:** owner-authorized isolated synchronous Research Copilot candidate
**Original main:** `1574d83ab7c0ea0eebef22d0f2d00bc3ce2ed176`
**Implementation branch:** `codex/f1-bounded-research-copilot-20261022`
**Preserved dirty local checkout HEAD:** `a93ac4931f1c550b789fd894b8acddfed08ffaef`
**Report checksum:** see `phase_22_f1_implementation_report.md.sha256`.

## Required statuses

- `F1_SOURCE_PROVENANCE_STATUS`: **VERIFIED** — F1 authorization attachment SHA-256 `b50eeb6f5d764edd4f88c482e67977d9026e9e22ce13cb52af0c4ad4739e8ede`; `origin/main` was rechecked at `1574d83ab7c0ea0eebef22d0f2d00bc3ce2ed176`. PR #42 remains a separate open draft at head `1edccc2173492d24ec3e227d918c0b9da9e34fd1`; its proposed portfolio contract and F0 handoff were read directly and not merged. The original dirty checkout at `a93ac4931f1c550b789fd894b8acddfed08ffaef` was preserved.
- `F1_RESEARCH_ORCHESTRATION_STATUS`: **IMPLEMENTED_AND_FOCUSED_TESTS_PASS** — authenticated private-thesis API; synchronous workflow; max two passes, eight typed tool invocations, four documents by default, two model calls, configured token/cost budgets, 25-second backend wall deadline, and no worker lease.
- `F1_LLM_GOVERNANCE_STATUS`: **GUARDED_DISABLED_BY_DEFAULT** — existing evaluated/promoted `report_synthesis` route, scope/privacy checks, provenance, quality validation, and deterministic fallback are reused. Synthesis and provider remain disabled by default; zero cost is the default; unpriced and over-budget routes fail closed. Preflight uses a conservative UTF-8 byte upper bound plus provider-wrapper reserve, registered price rates, and a remaining-deadline provider timeout. Controlled fake-provider and governance regressions passed.
- `F1_TOOL_AND_SOURCE_SAFETY_STATUS`: **IMPLEMENTED_AND_TESTED** — fixed typed allowlist; hash-only tool trace; citation validation removes chunks missing required metadata; source version ID/checksum is retained when available and left unavailable when absent; fixed market adapters; no model-generated code, shell, or unrestricted HTTP. Existing adversarial model-quality tests and the F1 prompt-injection fixture passed with no unsafe text in the saved report.
- `F1_DETERMINISTIC_INTEGRITY_STATUS`: **PRESERVED_AND_TESTED** — risk, market data, missing-data fields, sources, and disclaimer remain deterministic. Existing fake-provider mutation tests passed; F1 saved-report assertions passed.
- `F1_THESIS_REPORT_INTEGRATION_STATUS`: **IMPLEMENTED_AND_TESTED** — migration `20261022_0035`; stable owner/thesis/run association; checksummed inputs include a bounded snapshot of legacy saved assumptions and current explicit assumption heads; assumptions appear in an immutable owner-provided/unverified report section added after synthesis; unique owner-scoped idempotency; same-key replay returns the saved result; mismatched input returns `409`; report persistence, comparison, reopen, and Markdown export passed.
- `F1_FRONTEND_WORKFLOW_STATUS`: **IMPLEMENTED_BUILD_AND_SMOKE_CHECKED** — question submission from the saved-thesis workspace, synchronous status, retry key reuse while the form remains mounted, saved-run links, evidence/freshness display, report view, comparison, and export. Frontend typecheck, build, BFF contracts, and F1 UI contract passed. A local built-page smoke is recorded below.
- `F1_AUTH_TENANT_ISOLATION_STATUS`: **PRIVATE_OWNER_SCOPE_TESTED** — authentication is required; only the authenticated owner of an active private thesis can submit or read its runs; another user receives `404`. Reports retain existing owner authorization. Tests use isolated SQLite and synthetic user identities.
- `F1_REGRESSION_STATUS`: **SELECTED_BACKEND_AND_FRONTEND_REGRESSIONS_PASS** — see validation record below. This was a focused changed-path run, not a claim that the full application suite passed.
- `F1_REAL_MODEL_ACCEPTANCE_STATUS`: **NOT_PERFORMED** — no real provider route was enabled, no actual private thesis data was transmitted, and no provider charge or deployment occurred. Fake-provider tests are not real-model acceptance.
- `F1_OWNER_ACTIVATION_REQUIREMENTS`: **OWNER_DECISIONS_REQUIRED** — before supervised model acceptance, explicitly approve provider/model, private-data transmission and retention boundary, `private_approved` model classification and server-owned route promotion, credential source, token budget, and a per-run cost ceiling based on current registered rates. Keep synthesis disabled until those choices and the acceptance plan are recorded. No provider, price cap, or privacy threshold was inferred. The ten R3.15 decisions remain pending.
- `F1_REVIEWER_PROVENANCE_STATUS`: **AGENT_REVIEW_ONLY** — implementation and report prepared by the OpenAI Codex agent in this session. No authenticated human identity or independent second-party separation is evidenced.
- `F1_FINAL_VERDICT`: **READY_FOR_INDEPENDENT_F1_REVIEW** — the implementation candidate and local evidence are ready for review. This is not `PERSONAL_RESEARCH_READY`, production acceptance, merge approval, or Phase 22 completion.

## Validation record

Backend selected regression command:

```bash
cd backend
.venv/bin/python -m pytest \
  app/tests/test_phase22_research_copilot.py \
  app/tests/test_llm_synthesis.py \
  app/tests/test_phase21b_model_routing.py \
  app/tests/test_phase21d_research_intelligence.py \
  app/tests/test_market_data_adapters.py -q
```

**Result:** passed on the selected candidate before the final conservative
byte-based prompt-estimate adjustment. This includes the new F1 API/tool tests, controlled fake
provider success and failure, malformed/tampered synthesis, model-route
privacy/promotion, source-instruction adversarial cases, market adapters,
tenant isolation, idempotency, and report comparison/export. New F1 tests used
synthetic retrieval and market fixtures only.

After the final budget/deadline adjustment, the F1, synthesis, and model-route
subset was run again and passed:

```bash
cd backend
.venv/bin/python -m pytest \
  app/tests/test_phase22_research_copilot.py \
  app/tests/test_llm_synthesis.py \
  app/tests/test_phase21b_model_routing.py -q
```

After the final source-version/status mapping and owner run-detail assertions,
`test_phase22_research_copilot.py` plus `test_market_data_adapters.py` passed
again, and backend `compileall` completed successfully. This final follow-up
kept the rerun bounded to changed paths.

After adding saved-assumption reporting, input-checksum coverage, and the
Markdown/prompt-injection boundary assertion, the exact final F1 module was
rerun:

```bash
cd backend
.venv/bin/python -m pytest app/tests/test_phase22_research_copilot.py -q
```

**Result:** 7 passed. This verifies current explicit and legacy assumption
capture, stale idempotency rejection after an assumption revision, that
owner-authored assumption text stays out of synthesis input, and that the
saved report/export presents it as inert owner-provided text. One initial test
attempt lacked the required thesis revision precondition; the corrected test
supplies it, and the final run passed.

The selected changed-path regression across F1, synthesis, model routing,
Phase 21D research intelligence, and market adapters also passed after the
saved-assumption integration. The final narrow F1 rerun above includes the
subsequent Markdown inertness change.

An isolated temporary SQLite database passed Alembic
`upgrade head -> downgrade 20260911_0034 -> upgrade head`, including migration
`20261022_0035`. The app test fixture also applied the current migration chain
on isolated SQLite. PostgreSQL migration/concurrency execution was not run for
this synchronous candidate.

Frontend results:

- `npm run lint` — passed.
- `npm run build` — passed after setting the 35-second route maximum.
- `npm run test:bff` — passed.
- `npm run test:phase21d` — passed.
- `npm run test:phase21e` — passed.
- `npm run test:phase22-f1` — passed.
- Built Next.js app — local smoke returned HTTP 200 for `/` and `/theses`; no hosted backend was contacted by the smoke.

The Next.js BFF aborts the upstream research request at 30 seconds; the route
declares `maxDuration = 35`, and the backend's configured run deadline defaults
to 25 seconds. Vercel's official [duration configuration](https://vercel.com/docs/functions/configuring-functions/duration)
and [function limits](https://vercel.com/docs/functions/limitations) were
checked on the review date; the configured ceiling is below the published
Hobby Node.js maximum. The actual linked project's plan, Fluid Compute setting,
and hosted runtime were not inspected.

## Preserved status and limitations

- Seven historical R3 failures H1–H7 remain open and preserved. This F1 change
  does not modify or qualify the worker/schedule temporal architecture.
- All ten R3.15 owner decisions remain pending; none was accepted by the agent.
- F1 does not use the R3 persisted time floor, Phase 17 workers, or schedule
  dispatch. The temporal/recovery blockers remain applicable to those paths.
- A process crash after a run reservation can leave `running` persisted. The
  idempotency key prevents accidental repeated provider work; F1 includes no
  automatic worker recovery or replay path.
- Source publication timestamps may be absent; retrieval time is shown and the
  missing source timestamp remains explicit.
- No production system, production database, production credentials, hosted
  deployment, worker, schedule, model-provider secret, merge, or owner decision
  was accessed or changed.

## Portable verification

From this directory, verify the report with:

```bash
sha256sum -c phase_22_f1_implementation_report.md.sha256
```

The original application checkout at `/home/publio/projetos/DeFiThesis_RiskCopilot`
remained dirty but untouched. The full F1 source is isolated on the branch named
above and is submitted as a draft pull request; Phase 22 remains ACTIVE — HOLD.
