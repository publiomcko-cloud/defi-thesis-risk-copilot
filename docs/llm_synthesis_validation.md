# LLM Synthesis Validation

This document records the local validation of Post-MVP Phase 1: optional backend LLM synthesis.

## Scope

The LLM synthesis path improves report explanation wording only. It must not override deterministic analysis outputs.

Protected fields and behavior:

- risk score
- risk rating
- protocols
- missing data
- sources
- disclaimer
- market data values
- safety boundaries

The app must keep working when LLM synthesis is disabled, unavailable, slow, or invalid.

## Local Test Environment

Hardware:

- GPU: NVIDIA GeForce GTX 1050 Ti
- VRAM: 4 GB

Ollama:

- Installed locally
- Reachable from host at `http://127.0.0.1:11434`
- Reachable from Docker backend at `http://host.docker.internal:11434`

Tested local models:

- `llama3.1:8b`
- `llama3.2:3b`

Result: `llama3.2:3b` is the better local fit for this GPU. The 8B model can respond, but it is too heavy for comfortable report synthesis on 4 GB VRAM.

## Runtime Configuration Used

Local `.env`:

```env
LLM_SYNTHESIS_ENABLED=true
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:3b
LLM_TIMEOUT_SECONDS=180
```

Backend container environment confirmed:

```text
LLM_PROVIDER=ollama
LLM_SYNTHESIS_ENABLED=true
LLM_TIMEOUT_SECONDS=180
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:3b
```

## Validation Performed

Direct provider test:

- Docker backend reached Ollama successfully.
- `llama3.2:3b` returned valid JSON for a small provider prompt.

Backend report workflow:

- `/api/analyze` completed successfully with LLM synthesis enabled.
- Persisted report included the LLM synthesis assumption.
- Deterministic risk rating remained protected.

Verified browser-generated report:

```text
report_id: report_3773ef0de584
risk_rating: Very Risky
LLM marker: Optional LLM synthesis was used only to improve explanatory wording; deterministic risk scoring, missing data, sources, market values, and safety rules remain authoritative. Provider: ollama; model: llama3.2:3b.
```

Backend tests with Ollama enabled:

```bash
cd backend
source .venv/bin/activate
LLM_SYNTHESIS_ENABLED=true \
LLM_PROVIDER=ollama \
OLLAMA_BASE_URL=http://127.0.0.1:11434 \
OLLAMA_MODEL=llama3.2:3b \
LLM_TIMEOUT_SECONDS=120 \
python -m pytest -q
```

Result:

```text
30 passed
```

## Issues Observed

Local LLM latency:

- Full report synthesis is slow on the GTX 1050 Ti.
- 60 seconds was not always enough for the full report prompt.
- 120 seconds worked in local backend tests.
- 180 seconds is more reliable for Docker/browser testing.

Smoke script timeout:

- `backend/scripts/run_smoke_checks.py` currently uses a shorter client timeout.
- With LLM synthesis enabled, the smoke script can time out even though the backend eventually completes the report.
- For fast smoke testing, keep `LLM_SYNTHESIS_ENABLED=false`.
- For LLM validation, use a longer direct request or increase the smoke timeout temporarily.

Docker networking:

- Inside the backend container, `localhost:11434` points to the container, not the host.
- Local Docker testing should use `OLLAMA_BASE_URL=http://host.docker.internal:11434`.
- `docker-compose.yml` includes `host.docker.internal:host-gateway` for Linux host access.

## Current Conclusion

Post-MVP Phase 1 is complete.

The app can use local Ollama synthesis with `llama3.2:3b`, and deterministic fallback behavior remains intact. The main remaining improvement is performance: future work should shorten prompts, synthesize sections separately, or use a faster hosted/OpenAI-compatible model for better interactive latency.
