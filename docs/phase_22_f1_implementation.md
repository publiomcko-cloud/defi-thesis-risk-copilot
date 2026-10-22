# Phase 22 F1 — Bounded Synchronous Research Copilot

**State:** implementation candidate; Phase 22 remains **ACTIVE — HOLD**.
**Profile:** technical portfolio and restricted personal research.
**Authorization:** owner-provided F1 authorization attachment SHA-256
`b50eeb6f5d764edd4f88c482e67977d9026e9e22ce13cb52af0c4ad4739e8ede`.

## Source authority

The isolated implementation branch starts from verified remote `main` at
`1574d83ab7c0ea0eebef22d0f2d00bc3ce2ed176`. Draft PR #42 is a separate,
unmerged documentation proposal at
[`1edccc2173492d24ec3e227d918c0b9da9e34fd1`](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/tree/1edccc2173492d24ec3e227d918c0b9da9e34fd1).
The F0 handoff and portfolio contract were read from that exact proposed
source. PR #42 was not merged or modified. The original dirty checkout was
preserved; implementation and tests run in `/home/publio/phase22-f1-implementation`.

The F0 handoff records the verified sealed R3.26–R3.31 artifacts, seven
historical failures H1–H7 as open, and the ten R3.15 owner decisions as pending.
F1 touches no R3.15 reserved path, resolves none of the failures, and accepts
none of those decisions. The R3 time-floor experiment remains outside the
application architecture.

## Implemented workflow

An authenticated owner can open a private saved thesis, submit a bounded
question, inspect persisted run history, and open the linked report. The
synchronous service:

1. Authorizes and locks the private thesis before reading its strategy, protocol tags, legacy saved assumptions, and current explicit assumption heads.
2. Reserves one owner-scoped idempotency key, checksums the bounded assumption snapshot with the thesis/question input, and applies the existing analysis quota.
3. Runs the existing strategy parser, curated retrieval, market adapters, deterministic risk scoring, scenarios, and report writer.
4. Performs one bounded follow-up retrieval pass if protocol coverage or document count leaves an evidence gap.
5. Validates citation metadata, removes invalid source chunks, and keeps deterministic fields authoritative.
6. Uses the existing promoted and scope-approved `report_synthesis` route only if explicitly enabled; otherwise it records deterministic fallback.
7. Saves the report, provenance, run metadata, tool hashes, source freshness, gaps, and completion status through the existing report model.
8. Supports saved-run reopen, same-scope report comparison, and Markdown export.

Saved assumptions are copied into an immutable report section after synthesis,
marked owner-provided and unverified, and never included in the model prompt.
The run checksum includes the exact bounded snapshot so a reused idempotency
key cannot silently bind to different displayed assumptions.

Source version identifiers and checksums are included when retrieval metadata
supplies them. Legacy curated sources without a version identity are labeled as
unavailable rather than assigned an invented version.

Server-selected tools have typed inputs and outputs. The allowlist contains
protocol retrieval, market observation, deterministic risk, and report
synthesis. At most two passes, eight tool invocations, four documents by
default, two model calls, 6,000 total tokens, and 25 seconds are configured.
The backend validates the run deadline between 5 and 25 seconds so an
environment override cannot exceed the 30-second BFF abort; the model request
timeout is clipped to the remaining run budget.
`RESEARCH_RUN_COST_CEILING_MICROUSD=0`, `LLM_SYNTHESIS_ENABLED=false`, and
`LLM_PROVIDER=disabled` remain safe defaults. An unpriced route or failed
budget preflight uses deterministic fallback. Model text cannot replace risk,
market observations, source lists, missing-data fields, or the disclaimer.
Input-budget preflight uses UTF-8 byte length plus a fixed provider-wrapper
reserve in the absence of a provider tokenizer, then derives the maximum output
tokens and cost from registered route rates.

The BFF forwards the idempotency key and enforces a 30-second upstream abort;
the Next.js route declares `maxDuration = 35`. The backend run deadline is 25
seconds. The route-level maximum is within Vercel's currently documented Hobby
Node.js function maximum; the actual linked plan, Fluid Compute setting, and
hosted runtime were not inspected.

## Safety and limitations

- The application path is synchronous and does not use Phase 17 worker leases,
  scheduled dispatch, or the experimental PostgreSQL persisted time floor.
- Only private theses owned by the authenticated actor are supported by this
  route. Organization-shared and anonymous thesis research is rejected.
- Untrusted retrieved content remains evidence, not instructions. Traces store
  digests; raw private questions and source text are not written to product
  analytics.
- A process crash after reservation can leave a persisted `running` row. Its
  idempotency key prevents duplicate model work; F1 provides no worker or
  automatic stale-run recovery. Do not replay such a run under a new key while
  the previous outcome is unknown.
- A local synthetic/fake-provider test is not real-model acceptance. No actual
  private thesis text was sent to a provider and no provider charge was made.
- Source publication time can be absent; observed retrieval/adapter time and
  the missing source timestamp are shown instead of being inferred.

## Deferred owner activation decisions

Before a supervised real-model demonstration, the owner must explicitly approve
the provider and model, private thesis/source/report data transmission and
retention boundary, exact model privacy classification, the server-owned route
promotion, secret source, token budget, and per-run cost ceiling. The price
ceiling must be selected by the owner using current registered rates. No
threshold or provider is approved by this implementation record. Keep provider
flags off until those decisions and the synthetic-to-private acceptance plan
are recorded.

This candidate may be independently reviewed for F1 implementation quality. It
does not meet the portfolio contract's `PERSONAL_RESEARCH_READY` or Phase 22
release/deployment acceptance gate. See the [checksummed report](phase_22_f1_implementation_report.md).
