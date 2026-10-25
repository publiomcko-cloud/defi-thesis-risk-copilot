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
- Use only `qwen2.5:7b-instruct-q4_K_M`, pinned to the approved artifact
  digest `sha256:2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730`
  unless a new identity is separately reviewed and approved.
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
export F1A1J_MODEL_DIGEST=sha256:2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730

python - <<'PY'
import os

from app.auth.service import user_context
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.llm.evaluation import evaluate_report_synthesis_research_gpu_candidate
from app.llm.research_gpu_ollama import VerifiedResearchGpuOllamaProvider
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
    expected_model_digest=os.environ["F1A1J_MODEL_DIGEST"],
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
        model_artifact_digest=provider.artifact_digest,
        plan="representative",
    )
    print(
        f"run_id={run.id} status={run.status} cases={run.case_count} "
        f"promotion_eligible={run.promotion_eligible}"
    )
    if run.status != "completed" or run.case_count != 5 or run.promotion_eligible:
        raise SystemExit("five-case evaluation did not complete under the non-promotable policy")
PY
```

The run selects these five code-owned cases, in order:
`ordinary_valid`, `risk_mutation`, `source_mutation`,
`instruction_like_context`, and `direct_injection`. Before the first request,
the adapter queries `/api/ps`, unloads the exact model if needed, and verifies
it is absent. It then records Ollama's native `load_duration`,
`total_duration`, `prompt_eval_duration`, and `eval_duration`, together with
the observed model digest, server version, SSH-process/host-key evidence, and
timestamps. A positive native load duration is required for the first case
to be accepted as cold. All five requests count toward the 30,000 ms mean;
the cold case is not excluded. The exact API/generation path remains real HTTP,
not a canned-response implementation.

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

Only if all five cases satisfy the v1 quality and latency contract and a
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
