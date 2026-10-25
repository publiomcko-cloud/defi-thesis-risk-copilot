# Phase 22 F1-A1J — prepared real-GPU evaluation plan

**State:** prepared only. F1-A1I.1 qualifies PostgreSQL and the adapter
contract; it does not authorize a Vast.ai query, rental, model download, or
live provider call. Obtain a separate, explicit owner authorization before
executing any command below.

## Preconditions

- Revalidate one verified, full RTX 5080 16 GB, on-demand offer with direct
  SSH and inclusive compute plus requested disk at or below US$0.50/hour.
- Keep the existing independent Windows watchdog authenticated and tested
  before creation. A watchdog whose Windows host is powered off, asleep,
  disconnected, or otherwise unavailable cannot guarantee an absolute
  billing ceiling. The US$3 total, 30-minute duration, and one-instance limit
  are operational limits, not provider-enforced caps; do not create a
  replacement instance.
- Use only `qwen2.5:7b-instruct-q4_K_M`, with separately pinned Ollama
  manifest digest
  `sha256:845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`
  and GGUF model-layer weights digest
  `sha256:2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730`.
  The manifest checksum and its unique `application/vnd.ollama.image.model`
  layer are verified from the checked-in official registry evidence. The live
  `/api/tags` manifest, `/api/show` Q4_K_M metadata, and local Modelfile blob
  reference must independently match that pair over the verified SSH loopback
  tunnel. The two digests identify different artifact types and are not
  interchangeable.
- This correction uses the isolated `report_synthesis.research_gpu.v3`
  authority and `report_synthesis.research_gpu_binding.v3`. Its Ollama
  `/api/generate` request sends a JSON Schema (`stream=false`) whose exact
  top-level properties are `executive_summary` and `sections`; allowed
  section keys derive from `SYNTHESIZABLE_SECTION_TITLES`. The sections object
  may contain any subset, including none. The final
  `_validate_synthesis_payload()` and semantic evaluator remain authoritative;
  no repair or automatic schema retry is permitted. This experimental v3
  identity has a new policy checksum. Existing v2 evaluation rows and sealed
  evidence remain historical and are not rewritten. The promotion authority
  `report_synthesis.promotion.v3` and all quality/latency limits are unchanged.
- Disable Ollama cloud, bind the remote Ollama service to loopback, use a
  verified SSH host key and tunnel, and send only the checked-in public and
  synthetic evaluation fixtures. Keep product route activation disabled.
- Apply migration 0037 to the explicitly authorized evaluation database
  before the run. Set `DEPLOYMENT_COMMIT` to the exact qualified source commit
  recorded in the F1-A1I.1 report. Keep `DATABASE_URL` in the approved process
  environment; do not put its value in shell history, this document, or logs.
- Use a persisted, active platform administrator identity supplied through
  `F1A1J_OPERATOR_USER_ID`. The runner below rejects missing, inactive, or
  non-administrator users. No HTTP evaluation route exists; this is a local,
  one-shot call to the internal evaluation service.

## Bounded SSH and evaluator commands

After a separate owner authorization and successful cleanup-watchdog
preflight, activate the already-qualified backend Python environment and run
these commands from `backend/`. Supply the required shell values from the
newly authorized instance and the approved local database/runtime environment.
The SSH key must come from the secured SSH agent or protected
file, never a command-line key value. `StrictHostKeyChecking` must remain on;
`VAST_KNOWN_HOSTS` must contain the independently read-back host key.

```bash
set -euo pipefail
: "${VAST_SSH_TARGET:?set the authorized user@host}"
: "${VAST_SSH_PORT:?set the authorized SSH port}"
: "${VAST_KNOWN_HOSTS:?set the verified known_hosts path}"
: "${F1A1J_OPERATOR_USER_ID:?set the approved persisted admin user id}"
: "${DATABASE_URL:?provide the approved evaluation database through the protected environment}"

ssh -F /dev/null -N -T \
  -p "$VAST_SSH_PORT" \
  -o BatchMode=yes \
  -o ExitOnForwardFailure=yes \
  -o StrictHostKeyChecking=yes \
  -o "UserKnownHostsFile=$VAST_KNOWN_HOSTS" \
  -L 127.0.0.1:11435:127.0.0.1:11434 \
  "$VAST_SSH_TARGET" &
export RESEARCH_GPU_SSH_PID=$!
trap 'kill "$RESEARCH_GPU_SSH_PID" 2>/dev/null || true; wait "$RESEARCH_GPU_SSH_PID" 2>/dev/null || true' EXIT

export APP_ENV=development
export PUBLIC_DEMO_MODE=false
export RESEARCH_GPU_EVALUATION_ENABLED=true
export RESEARCH_GPU_EVALUATION_ISOLATED=true
export DEPLOYMENT_COMMIT="$(git -C .. rev-parse HEAD)"
export F1A1J_OLLAMA_BASE_URL=http://127.0.0.1:11435
export F1A1J_MODEL_MANIFEST_DIGEST=sha256:845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e
export F1A1J_MODEL_WEIGHTS_DIGEST=sha256:2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730

python - <<'PY'
import os

from sqlalchemy import select

from app.auth.service import user_context
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.llm.evaluation import evaluate_report_synthesis_research_gpu_candidate
from app.llm.research_gpu_ollama import VerifiedResearchGpuOllamaProvider
from app.llm.research_gpu_readiness import qualifies_as_approved_five_case_sample
from app.models.model_governance import ModelEvaluationCaseResultModel
from app.models.user import UserModel

settings = get_settings()
if settings.app_env != "development" or settings.public_demo_mode:
    raise SystemExit("evaluation environment is not isolated development")
if not settings.research_gpu_evaluation_enabled or not settings.research_gpu_evaluation_isolated:
    raise SystemExit("research-GPU evaluation gates are not enabled")
if settings.deployment_commit != os.environ["DEPLOYMENT_COMMIT"]:
    raise SystemExit("DEPLOYMENT_COMMIT does not match the running source")

provider = VerifiedResearchGpuOllamaProvider.verify_runtime(
    base_url=os.environ["F1A1J_OLLAMA_BASE_URL"],
    expected_manifest_digest=os.environ["F1A1J_MODEL_MANIFEST_DIGEST"],
    expected_weights_digest=os.environ["F1A1J_MODEL_WEIGHTS_DIGEST"],
    ssh_pid=int(os.environ["RESEARCH_GPU_SSH_PID"]),
)
with SessionLocal() as db:
    operator = db.get(UserModel, os.environ["F1A1J_OPERATOR_USER_ID"])
    if (
        operator is None
        or not operator.is_active
        or operator.account_status != "active"
        or operator.deleted_at is not None
        or (operator.role != "admin" and operator.platform_role != "admin")
    ):
        raise SystemExit("approved active platform administrator was not found")
    run = evaluate_report_synthesis_research_gpu_candidate(
        db,
        provider=provider,
        actor=user_context(operator),
        model_manifest_digest=provider.manifest_digest,
        model_weights_digest=provider.weights_digest,
        plan="representative",
    )
    case_results = db.scalars(
        select(ModelEvaluationCaseResultModel).where(
            ModelEvaluationCaseResultModel.evaluation_run_id == run.id
        )
    ).all()
    sample_approved = qualifies_as_approved_five_case_sample(run, case_results)
    cost_evidence = (
        "unobserved"
        if run.cost_observation_count == 0
        else f"{run.cost_observation_count}/5 cases; {run.cost_microusd_total} microusd observed"
    )
    print(
        f"run_id={run.id} status={run.status} passed={run.passed_case_count}/5 "
        f"provider_failures={run.provider_failure_count} failure_reason={run.failure_reason!r} "
        f"promotion_eligible={run.promotion_eligible} cost={cost_evidence} "
        f"sample_approved={sample_approved}"
    )
    if not sample_approved:
        raise SystemExit("five-case sample did not pass every v3 policy and quality requirement; stop")
PY
```

The run selects these five code-owned cases, in order:
`ordinary_valid`, `risk_mutation`, `source_mutation`,
`instruction_like_context`, and `direct_injection`. Before the first request,
the adapter queries `/api/ps`, unloads the exact model if needed, and verifies
it is absent. It then records Ollama's native `load_duration`,
`total_duration`, `prompt_eval_duration`, and `eval_duration`, together with
the separately typed manifest and weights digests, Q4_K_M metadata, local
blob reference, server version, SSH-process/host-key evidence, and timestamps.
A positive native load duration is required for the first case
to be accepted as cold. All five requests count toward the 30,000 ms mean;
the cold case is not excluded. The exact API/generation path remains real HTTP,
not a canned-response implementation. The post-run qualification helper
requires all five persisted cases to pass, no provider failures, no failure
reason, complete token/latency/native-timing evidence, the exact v3 binding,
and every unchanged quality-policy gate. It checks the 45-second request limit and
30-second mean; each case is a separate, single-call/single-pass synthesis
operation, so the 120-second duration and two-call/two-pass bounds apply per
case rather than to the five-case batch. Cost is informational: an absent
cost observation is printed as `unobserved`, never as zero.

`status="completed"` means only that the run finished. A 0/5 or partial pass
can also be completed while remaining non-promotable. The command reports
`sample_approved=true` only for 5/5 passing cases that satisfy all evidence
and v3 policy gates. `promotion_eligible` must remain false even for that
approved portfolio sample.

## Structured output and redacted diagnostics

For every case, record separate outcomes for transport completion, JSON
syntax, JSON Schema conformance, and semantic quality. Record only bounded
reason codes, the fixed missing required field names, and counts of unexpected
top-level properties or section titles; do not persist arbitrary property
names or raw model output. Distinguish malformed JSON from valid JSON that
violates structure, and distinguish both from semantic quality failure after
structure passes. A response timeout or other non-completed request has no
JSON or semantic result and must be reported as `not_completed`, with transport
outcome and incomplete evidence stated explicitly. Record whether each native
Ollama metric was available; missing metrics remain missing and cannot be
inferred.

## GPU, latency, cost, and execution evidence for a future authorized run

For each run, record the detected GPU model and VRAM, the exact resident
Ollama model, and the observed GPU layer count/offload state. Capture CUDA
utilization during inference when the host exposes it; mark it unavailable
when it cannot be observed. Keep per-call wall-clock latency separate from
Ollama `load_duration`, `total_duration`, `prompt_eval_duration`, and
`eval_duration`. Record valid JSON, schema conformity, and semantic quality
as independent outcomes. Reconcile compute, disk, transfer, startup/download,
and cleanup costs separately, label estimates and unsettled billing, and
report incomplete calls as not completed rather than assigning a latency or
quality result.

## Sample interpretation and stop conditions

F1-A1H measured 30,763.869 ms cold and 881.336 ms for an identical warm
prompt; that warm request benefited from prompt cache and is not equivalent
to the representative cases. Its application case hit the old 8-second
timeout at 8,143 ms, so quality remained unmeasured. Those observations do
not establish F1-A1J quality or timing. The five-case result can estimate a
full-run duration only as `cold measurement + observed warm-case distribution
for remaining cases`, with variability and startup/download/cleanup overhead
reported separately. The prior inclusive 30-minute compute/storage estimate
was about US$0.191 before transfer; observed F1-A1H billing was US$0.058.
Recalculate actual offer, disk, transfer, and billing before any future
authorization.

Only if all five cases satisfy the v3 experiment's unchanged quality and latency contract and a
measured full-corpus duration/cost fits a separately authorized limit may a
31-case run be proposed. Stop after any provider failure, invalid JSON,
quality/citation/integrity failure, budget concern, host-key or digest change,
or cleanup uncertainty. Destroy the exact instance and reconcile its absence
and billing regardless of evaluation outcome; never create a replacement.
Close the local tunnel with the trap and verify its process ended. The
Windows-dependent watchdog is supplementary and cannot guarantee an absolute
charge cap when Windows is unavailable.

## Runtime architecture gate

This procedure evaluates the GPU-hosted synthesis model under the isolated,
non-promotable v1 evaluation profile. It does not activate a 120-second
product operation. Any user-facing 120-second research run first needs the
asynchronous operation/lease/finalizer design and owner decisions described
in `phase_22_f1a1i_research_gpu_policy.md`; do not stretch the existing
synchronous 25-second backend / 30-second BFF flow.
