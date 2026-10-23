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
F1-C restores `docs/deployment.md` byte-for-byte to the verified base; reserved
R3.15 decision #9 remains pending. No historical failure or owner decision is
resolved. The R3 time-floor experiment remains outside the application
architecture.

## Implemented workflow

An authenticated owner can open a private saved thesis, submit a bounded
question, inspect persisted run history, and open the linked report. The
synchronous service:

1. Acquires an owner-scoped execution/lifecycle fence, then authorizes the private thesis before reading its strategy, protocol tags, legacy saved assumptions, and current explicit assumption heads.
2. Reserves one owner-scoped idempotency key, checksums the bounded assumption snapshot with the thesis/question input, and applies the existing analysis quota.
3. Runs the existing strategy parser, curated retrieval, market adapters, deterministic risk scoring, scenarios, and report writer.
4. Matches bounded source sentences to the research question, cites each excerpt, reports unmatched question terms and possible lexical conflicts, and returns an explicit insufficient-evidence answer when no relevant sentence is found. Lexical matches remain marked weak; they never establish semantic entailment.
5. Performs at most one question-focused retrieval pass when question terms remain unmatched or required protocol evidence is absent; the semantic-entailment limitation and document count alone do not trigger that pass.
6. Validates citation metadata and URLs, removes invalid source chunks, and keeps deterministic fields authoritative.
7. Uses the existing promoted and scope-approved `report_synthesis` route only if explicitly enabled; otherwise it records deterministic fallback.
8. Saves the report, provenance, run metadata, tool hashes, source freshness, gaps, and completion status through the existing report model.
9. Supports saved-run reopen, same-scope report comparison, and Markdown export.

Saved assumptions are copied into an immutable report section after synthesis,
marked owner-provided and unverified, and never included in the model prompt.
The run checksum includes the exact bounded snapshot so a reused idempotency
key cannot silently bind to different displayed assumptions.

Research questions and strategy descriptions are separate, labeled untrusted
task-input fields. Retrieved text, source metadata, URLs, and market observations
are untrusted data. Provider adapters send code-owned policy in a real system
message/field; user JSON contains only task data. The F1-C prompt contract is
`report_synthesis.prompt.v4` with safety policy `report_synthesis.safety.v3`.
The prior v3 prompt record remains immutable. Existing promoted routes for v3
do not authorize v4; v4 requires normal evaluation and promotion before model
use.

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
tokens and cost from registered route rates. After a response, the enforced
effective total is the maximum of the valid provider total and the valid
input/output component sum. Adapter usage counts accept only strict,
non-boolean integers from 0 through 10,000,000. The OpenAI-compatible Chat
Completions adapter requires the documented `prompt_tokens`,
`completion_tokens`, and `total_tokens` fields; absent or malformed values cause
deterministic fallback. The [OpenAI usage schema](https://platform.openai.com/docs/api-reference/chat/object)
documents those counts. Ollama reports `prompt_eval_count` and `eval_count`
without a separate total, so only that adapter derives the effective total from
both components and leaves the provider-reported total unknown
([Ollama usage fields](https://github.com/ollama/ollama/blob/main/docs/api/usage.mdx)).
Present invalid fields remain classified by field name; raw malformed values
are not retained. Any malformed, incomplete, over-budget, or inconsistent
usage prevents model-generated text from being accepted. Valid observed
components and available registered-rate cost evidence remain in provenance
when a response is rejected. Provider-reported and effective totals remain
separate.

The BFF forwards the idempotency key and enforces a 30-second upstream abort;
the Next.js route declares `maxDuration = 35`. The backend run deadline is 25
seconds. A browser or BFF timeout only ends waiting; it does not assert backend
cancellation. Run history is refreshed after timeout and carries the original
idempotency key so refresh/retry cannot start a second provider call. Hosted
Vercel plan, function settings, candidate deployment, and route behavior remain
**DEPLOYMENT_UNVERIFIED**; the previous reviewer received HTTP 403 during
read-only project inspection.

## Safety and limitations

- The application path is synchronous and does not use Phase 17 worker leases,
  scheduled dispatch, or the experimental PostgreSQL persisted time floor.
- Only private theses owned by the authenticated actor are supported by this
  route. Organization-shared and anonymous thesis research is rejected.
- Untrusted retrieved content remains evidence, not instructions. Traces store
  digests; raw private questions and source text are not written to product
  analytics.
- PostgreSQL holds an owner-scoped transaction advisory lock on a dedicated,
  pinned connection from before reservation through report commit. The request
  checks that same transaction before work, around each bounded tool call, and
  at finalization; detected lock loss stops further calls and records an
  uncertain outcome rather than claiming an already-transmitted provider call
  was cancelled. The advisory connection is a prompt stop signal, not the sole
  final-write authority. Reservation and finalization reload lifecycle state
  under row locks. Finalization locks account, thesis, then run; it revalidates
  active account, live private ownership, exact input checksum, and `running`
  status, then commits the report, completion metadata, provenance, quality
  evidence, and usage in one transaction. Account deletion locks account then
  runs; thesis deletion locks thesis then runs. If lifecycle disposal commits
  first, finalization fails without a report. If finalization commits first,
  later deletion waits for the rows and scrubs the completed report and private
  data. Reconciliation and failure handling reload and lock the run row so a
  terminal or disposed run is not overwritten by stale state. A status read
  that cannot obtain the advisory fence leaves a running reservation alone;
  after process loss, reconciliation finds a committed report or marks the run
  `interrupted` with provider outcome and usage explicitly uncertain. Process
  loss releases the PostgreSQL transaction lock; transaction-pooling operation
  requires the open transaction to pin its backend for the whole request.
  Each active request still needs an application connection and a separate
  owner-lock connection; pool headroom, checkout timeout, and hosted pooler
  affinity remain deployment prerequisites and were not verified here. SQLite
  has only a process-local fence and cannot prove cross-process ownership;
  stale runs are marked `uncertain` and are not cancelled or replayed. In either
  case the same key returns the persisted state. Do not retry an unknown run
  under a new key. No automatic worker recovery exists.
- Thesis and account deletion scrub F1 questions, strategy snapshots, source and
  model provenance, report JSON, and Markdown while retaining only a redacted
  disposition record. Report access rejects tombstoned rows. Owner privacy
  export includes live F1 run metadata and full report JSON/Markdown. F1 rows
  have no automatic TTL; they are retained until the owner deletes the thesis
  or account, when F1 payloads are scrubbed in the existing lifecycle
  transaction.
- Citation destinations use the shared backend/frontend policy: ASCII DNS
  names over HTTPS without credentials, plus recognized `docs/` or
  `knowledge_base/` Markdown references. IP literals, IDNs, local names,
  malformed ports, and ambiguous path encodings are rejected. Unsafe metadata
  is removed from F1 evidence before answer generation and sanitized again in
  report APIs, Markdown export, and frontend links. The policy is display-only;
  it does not authorize server-side fetching.
- Provider provenance distinguishes no attempt, pre-transmission rejection,
  response received but rejected, uncertain transport outcome, and accepted
  output. Observed tokens and cost remain visible on rejected responses; missing
  usage is marked unknown and never reported as zero. Post-call rejection does
  not reverse provider charges.
- A local synthetic/fake-provider test is not real-model acceptance. No actual
  private thesis text was sent to a provider and no provider charge was made.
- Source publication time can be absent; observed retrieval/adapter time and
  the missing source timestamp are shown instead of being inferred.
- Draft CI audits found six pypdf advisories in the pre-existing `6.20.0` pin
  and critical/high Next.js advisories in the pre-existing `15.5.27` pin. F1
  updates them to `pypdf==6.21.1` and `next==15.5.28`; focused PDF-ingestion
  and F1 tests, frontend lint/build/contracts/smoke, and the local production
  dependency audit pass with the updated pins.

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
release/deployment acceptance gate. See the [checksummed implementation report](phase_22_f1_implementation_report.md),
the [checksummed F1-C correction review](phase_22_f1c_correction_report.md),
the [checksummed F1-C2 correction report](phase_22_f1c2_correction_report.md),
and the [checksummed F1-C3 correction report](phase_22_f1c3_correction_report.md).
