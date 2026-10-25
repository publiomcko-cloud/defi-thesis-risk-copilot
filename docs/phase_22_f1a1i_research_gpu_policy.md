# Phase 22 F1-A1I — research-GPU evaluation policy

## Authority and state

`report_synthesis.promotion.v3` remains unchanged (SHA-256
`309f35a2842827002dae007a8d3f4e2ac5c082326b9e6697969d858b8c37f25c`). The
independent `report_synthesis.research_gpu.v1` policy is code-owned and has
SHA-256 `a0694927eec462f565a2146633c4b9d499e3deceff968819001f4b583aa57fe3`.
Its non-latency thresholds and evaluator protocol are copied exactly from v3.
It retains the 100% structured-output, deterministic-preservation,
source-integrity, citation-consistency, uncertainty-preservation,
deterministic-integrity, and missing-data-honesty requirements; zero
unsupported claims, source-poisoning authority violations, unsafe-language
violations, privacy violations, and provider failures; and informational
provider cost accounting.

The research-GPU latency contract is a 45-second provider timeout, maximum
30,000 ms mean model-request latency, a 120,000 ms maximum for one complete
research operation, at most two model calls and two passes per research, and
zero provider failures. The mean includes every measured call, including cold
starts. Cold and warm measurements are stored separately. A missing latency,
input/output token count, latency phase, or over-timeout response makes the
evaluation fail closed; missing provider cost is recorded as unobserved, not
zero.

## Isolation and evidence binding

The profile has two server settings, both false by default:
`RESEARCH_GPU_EVALUATION_ENABLED` and
`RESEARCH_GPU_EVALUATION_ISOLATED`. Both must be true, `APP_ENV` must be
`development` or `exercise`, and public-demo mode must be off. The internal
evaluation service accepts only the code-owned Ollama Qwen2.5 7B Q4_K_M
identity, explicitly `public_only`, over an HTTP loopback endpoint (the
authorized SSH tunnel), and requires the model artifact SHA-256. It also
requires `DEPLOYMENT_COMMIT` to be the exact 40–64 character source commit;
`source-tree` is insufficient for a bound v1 run. It has no HTTP route and no
client-selectable policy, threshold, case list, provider, or environment.
Evaluation cases are chosen by a fixed five-case representative plan or the
complete 31-case plan.

Each completed run stores the v1 policy version/checksum and a separate
checksum plus redacted structured binding snapshot over the model registry identity and artifact digest, exact
task/version, prompt ID/checksum, evaluator protocol, both dataset IDs,
versions, checksums and counts, selected case checksums, evaluation plan,
environment, and source revision. Case evidence stores `cold` or `warm`,
latency, tokens, and any observed provider cost. The evaluator commits the
running marker before model I/O and commits each redacted case result in a
short transaction; no database transaction is held across inference. An
interrupted run remains non-promotable.

The new profile is always non-promotable. It does not mark the model registry
as evaluated or change routes. Promotion, live route resolution, execution
snapshots, and rollback/restoration require the exact v3 policy version and
checksum. Snapshots now carry that authority explicitly, and legacy active
snapshots missing the policy fields fail closed to deterministic fallback.
Historical results are not rewritten or reinterpreted.

Provider API fees, Vast GPU compute, disk, and transfer are separate cost
categories. A local Ollama response with no API-token charge does not mean the
GPU experiment is free. Unsettled provider billing is labeled an estimate.

## Synchronous deadline and asynchronous dependency

The existing product route remains at a 25-second backend wall deadline, a
30-second BFF abort, and the existing 35-second route maximum. F1-A1I does not
raise any of them. The 120-second policy is not connected to the live
synchronous research route.

Supporting a 120-second user operation safely requires a separate architecture
decision and qualified execution infrastructure. Proposed flow:

1. In a short transaction, authorize the thesis owner, reserve an
   idempotency-keyed operation, persist a secret-free immutable task/policy/
   provider/route snapshot, and enqueue it durably; return the operation ID.
2. Run under a qualified lease/fence with two calls, two passes, fixed
   token/source/tool/cost budgets, a monotonic 120-second deadline, and a
   cancellation signal. Once a provider request is transmitted, cancellation
   cannot imply that provider work or charges stopped.
3. Finalize only after rechecking tenant ownership, thesis/input generation,
   exact route/policy snapshot, deadline, and current fencing token. Commit the
   final output and terminal status atomically; stale workers cannot finalize.
4. Expose owner-scoped status/progress and safe cancellation, retain
   deterministic fallback, and reconcile interrupted/uncertain provider calls
   without replaying them automatically.

The unqualified Phase 17 worker/lease/schedule infrastructure is not activated
or reused. Any design requiring protected R3.15 paths or a new owner decision
must wait for the corresponding explicit decision and a separately authorized
implementation. Phase 22 remains ACTIVE — HOLD; H1–H7 remain OPEN; all ten
R3.15 decisions remain PENDING.
