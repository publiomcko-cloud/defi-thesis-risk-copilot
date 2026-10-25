# Phase 22 F1-A1J — prepared real-GPU evaluation plan

**State:** prepared only; no Vast.ai query, rental, model download, credential
change, or provider call is authorized by F1-A1I.

## Preconditions

- Obtain a separate owner authorization after F1-A1I policy review.
- Revalidate exactly one verified, full RTX 5080 16 GB, on-demand offer with
  direct SSH, inclusive compute plus disk at or below US$0.50/hour.
- Use the already corrected SSH method only after account-key read-back,
  independent Windows watchdog authentication, and synthetic cleanup test.
- One instance, no replacement, maximum 30 minutes, US$3 operational target;
  the target is not provider-enforced and the Windows watchdog cannot cap
  charges while Windows is unavailable.
- Use only `qwen2.5:7b-instruct-q4_K_M`, pinned to the recorded model artifact
  digest `sha256:2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730`
  unless separately reviewed evidence justifies a new identity.
- Disable Ollama cloud, bind only to loopback, use an SSH tunnel, synthetic or
  public fixtures only, and keep runtime route activation disabled.

## Representative sample

Run the fixed five cases in order: `ordinary_valid`, `risk_mutation`,
`source_mutation`, `instruction_like_context`, and `direct_injection`. Verify
the model is unloaded before the first request and record that request as
cold; subsequent requests in the same server session are warm. Do not discard
the cold latency from the aggregate mean. Use the exact v1 45-second request
timeout and 30,000 ms all-request mean, zero-provider-failure and inherited
quality checks. Preserve per-case latency, phase, input/output tokens, JSON
validity, failure category, quality/citation results, and provider cost
observations. Record GPU compute, disk, network, and unsettled billing
separately.

F1-A1H measured 30,763.869 ms cold and 881.336 ms for an identical warm prompt;
the warm request benefited from prompt cache and is not an equivalent
representative request. The real application case then hit the old 8-second
timeout at 8,143 ms, so its quality was unmeasured. These values motivate the
new policy but do not establish F1-A1J quality or timing. Five representative
case results must be used to estimate full-run duration as
`cold measurement + measured warm-case distribution for remaining cases`,
with variability and startup/download/cleanup overhead stated separately.
The prior inclusive 30-minute compute/storage estimate was about US$0.191,
before transfer; observed F1-A1H billing was US$0.058. Recalculate live before
any future rental.

Only if all five cases satisfy v1 quality and latency requirements and the
measured full-corpus duration/cost fits the separately authorized limits may
the 31-case run be recommended. Do not assume 31 cases fit a 30-minute rental
from one warm prompt or the prior failed 8-second attempt. Stop on any provider
failure, invalid JSON, quality/citation/integrity failure, budget concern, or
cleanup uncertainty. Destroy and reconcile the exact instance regardless of
evaluation outcome; do not create a replacement.

## Runtime architecture gate

This test plan evaluates the GPU-hosted synthesis model using the v1 evaluation
profile. It does not activate a 120-second product operation. Any user-facing
120-second research run first needs the asynchronous operation/lease/finalizer
design and owner decisions described in
`phase_22_f1a1i_research_gpu_policy.md`; do not stretch the existing
synchronous 25-second backend / 30-second BFF flow.
