# Phase 10-12 Expansion Plan — Discovery, Access Control, and Vast.ai

## Purpose

This plan defines the final product-development work before the portfolio/demo phases.

The goal is to turn the app from a static DeFi risk-analysis MVP into a controlled research system that can discover new DeFi candidates, evaluate them, route them through human review, ingest approved knowledge into RAG, and optionally use ephemeral GPU infrastructure for heavier model tasks.

These phases must preserve the existing product boundaries:

- no wallet connection
- no private keys or seed phrases
- no transaction signing
- no trade execution
- no custody
- no personalized financial advice
- no automatic trust of discovered sources
- no model output overriding deterministic risk scoring

## Revised Phase Order

```text
Post-MVP Phase 10: Auto-discovery and human-approved RAG ingestion
Post-MVP Phase 11: Access control and secure provider configuration
Post-MVP Phase 12: Vast.ai ephemeral model provider
Final Phase 13: Demo data and example reports
Final Phase 14: Public portfolio deployment
Final Phase 15: Portfolio polish
```

Phase 11 must be completed before Phase 12, because Vast.ai API configuration, billing controls, lifecycle controls, and instance cleanup must be admin-only.

---

# Phase 10 — Auto-Discovery and Human-Approved RAG Ingestion

## Objective

Add a controlled discovery-to-knowledge-base workflow.

The app should be able to discover DeFi protocols, pools, options venues, derivatives venues, and source candidates from public sources such as DefiLlama and manual lists. It should normalize and evaluate those candidates, then require a human decision before anything is ingested into the knowledge base.

## Discovery Sources

Initial sources:

```text
DefiLlama protocols
DefiLlama yield pools
DefiLlama options overview
DefiLlama open-interest overview
DefiLlama fees/revenue overview
Manual URL or pasted list
```

Start with DefiLlama free endpoints and existing app collectors. Do not require a paid DefiLlama Pro key for this phase.

## Discovery Filters

Recommended filters:

```text
min_tvl_usd
min_pool_tvl_usd
chain_allowlist
category_allowlist
protocol_allowlist
protocol_blocklist
new_since_days
include_yield_pools
include_options_protocols
include_open_interest
include_fee_protocols
```

Default filters should reduce noise and avoid creating excessive low-quality candidates.

## Workflow

```text
User or admin runs discovery
    -> collector fetches public source data
    -> normalizer creates discovered items
    -> duplicate detection uses stable discovery keys
    -> evaluation pipeline creates risk summary
    -> review item appears in the human review queue
    -> admin approves, rejects, archives, or marks needs_more_data
    -> only approved_for_rag items can be explicitly ingested
    -> app writes curated markdown under knowledge_base/discovered/
    -> RAG index is refreshed
    -> future reports can retrieve and cite the new knowledge
```

## Ingestion Rules

Ingestion must be explicit. Approval alone is not enough.

Required rule:

```text
status == approved_for_rag
AND admin clicks ingest-to-rag
AND item was not already ingested
```

The generated markdown file should use a controlled path such as:

```text
knowledge_base/discovered/{protocol}/{review_item_id}.md
```

The file must include:

```text
title
protocol
chain, if available
source URL
source type
discovery timestamp
evaluation timestamp
review status
reviewer notes
evaluation summary
risk rating
missing data
assumptions
source quality notes
human approval statement
non-advisory disclaimer
```

The file must clearly state:

```text
This source was automatically discovered and human-approved before ingestion.
```

## Backend Modules

Suggested files:

```text
backend/app/discovery/
  __init__.py
  defillama_client.py
  collectors.py
  filters.py
  normalizer.py
  quality.py

backend/app/knowledge_base/
  __init__.py
  ingestion_service.py
  markdown_writer.py

backend/app/api/routes_discovery.py
backend/app/api/routes_knowledge_base.py
backend/app/tests/test_discovery_to_rag.py
```

Reuse the existing monitoring, discovered item, evaluation, and review queue models where possible. Do not create a parallel review system.

## Endpoints

```text
POST /api/discovery/run
GET  /api/discovery/candidates
POST /api/evaluation/review-items/{review_item_id}/ingest-to-rag
GET  /api/knowledge-base/discovered
```

## Acceptance Criteria

- Discovery can run from DefiLlama sources and/or manual list input.
- Discovery candidates are normalized and deduplicated.
- Candidates enter the existing evaluation and review queue.
- Rejected or unreviewed items cannot be ingested.
- Approved items require an explicit ingest-to-RAG action.
- Duplicate ingestion is prevented.
- Generated markdown includes source metadata and human-approval metadata.
- RAG index refresh is triggered after ingestion.
- Future analysis can retrieve the ingested source.

---

# Phase 11 — Access Control and Secure Provider Configuration

## Objective

Add basic access control and secure server-side configuration management before adding Vast.ai automation.

The app needs role separation because Vast.ai API keys, cost controls, discovery approvals, and RAG ingestion must not be available to normal users.

## User Types

### Common User

A common user may:

```text
run normal strategy analysis
view generated reports they are allowed to access
run simulations
run options analysis
create personal watchlist items
view in-app alerts related to their own watchlists
```

A common user may not:

```text
manage API keys
configure Vast.ai
rent or destroy GPU instances
approve or ingest discovered sources into RAG
change global discovery settings
access system audit logs
change another user's resources
```

### Admin User

An admin may:

```text
manage users and roles
configure discovery sources
run global discovery jobs
review discovered items
approve/reject/archive review items
ingest approved items into the knowledge base
manage model provider settings
store and rotate Vast.ai credentials
start, stop, or destroy Vast.ai instances
view cost/lifecycle logs
run cleanup jobs
view audit logs
```

## Credential Storage Rules

Secrets must be server-side only.

For MVP implementation, support two modes:

```text
Mode A: environment variables only
Mode B: encrypted database storage for admin-managed provider credentials
```

For database storage, do not store raw secrets in plaintext. Store encrypted values and safe metadata only:

```text
provider_name
credential_name
secret_encrypted
secret_last4
created_by
created_at
rotated_at
last_used_at
enabled
```

The frontend must never receive the raw API key.

Logs must redact secrets.

## Suggested Backend Models

```text
users
api_credentials
access_audit_events
vast_sessions
```

Minimum user fields:

```text
id
email
role: admin | common
is_active
created_at
```

Minimum credential fields:

```text
id
provider
name
secret_encrypted
secret_last4
enabled
created_by
created_at
updated_at
last_used_at
```

Minimum audit fields:

```text
id
actor_user_id
action
resource_type
resource_id
metadata_json
created_at
```

## Suggested Auth Approach

For MVP/local demo:

```text
seed admin from environment variable
simple login/session or bearer token flow
FastAPI dependency: require_admin
FastAPI dependency: require_user
frontend role-aware navigation
```

For hosted deployment later:

```text
managed auth provider or hardened JWT/session auth
password reset
MFA for admin
external secret manager
rate limits
```

## Acceptance Criteria

- Two roles exist: admin and common.
- Admin-only endpoints reject common users.
- Vast.ai credentials can only be created/updated/read as metadata by admins.
- Raw API secrets are never returned to the frontend.
- Secret values are redacted in logs and responses.
- RAG ingestion from approved review items is admin-only.
- Vast.ai lifecycle actions are admin-only.
- Audit events are recorded for sensitive actions.

## Implemented Phase 11 Notes

The MVP implementation uses `AUTH_ENABLED=false` by default for local/demo use. When `AUTH_ENABLED=true`, FastAPI bearer-token dependencies enforce `admin` and `common` roles. A bootstrap admin can be seeded from `ADMIN_EMAIL` and `ADMIN_BOOTSTRAP_TOKEN` or `ADMIN_PASSWORD`.

Provider credentials are managed through admin-only endpoints and returned as metadata only. Raw secrets are not returned to the frontend. Database-stored credentials require `CREDENTIAL_ENCRYPTION_KEY`; hosted production should replace the MVP encryption helper with a managed secret store or KMS-backed encryption.

Audit events are recorded for provider credential changes, discovery runs, review status changes, and explicit approved-item RAG ingestion. Vast.ai lifecycle endpoints remain future Phase 12 work.

---

# Phase 12 — Vast.ai Ephemeral Model Provider

## Objective

Add a model provider that can rent a Vast.ai GPU instance, start an OpenAI-compatible model server container, use it for a controlled task, and then destroy the instance.

The provider must be optional and disabled by default.

## Recommended Provider Strategy

Do not integrate Vast.ai directly into every normal report request.

Use provider priority:

```text
1. deterministic fallback
2. local Ollama, if configured
3. OpenAI-compatible API provider, if configured
4. Vast.ai ephemeral provider, only when admin-enabled and task-approved
```

Vast.ai should be used for heavier optional tasks such as:

```text
large report synthesis
batch evaluation summaries
large-context discovery enrichment
future fine-tuning experiments
retrieval evaluation batches
```

It should not be required for normal app operation.

## Lifecycle State Machine

```text
idle
  -> searching_offer
  -> renting_instance
  -> booting
  -> starting_model_server
  -> health_checking
  -> ready
  -> serving_request
  -> cleanup
  -> destroyed
```

Failure states:

```text
offer_not_found
rent_failed
boot_timeout
container_failed
model_health_failed
request_failed
cleanup_failed
```

## Required Cost and Safety Controls

```text
VAST_ENABLED=false
VAST_MAX_HOURLY_COST_USD
VAST_MAX_SESSION_MINUTES
VAST_MAX_ACTIVE_INSTANCES=1
VAST_GPU_ALLOWLIST
VAST_MIN_GPU_RAM_GB
VAST_DISK_GB
VAST_REQUIRE_VERIFIED=true
VAST_AUTO_DESTROY=true
VAST_IDLE_TIMEOUT_SECONDS
```

The default cleanup action should be destroy, not stop, unless an admin explicitly chooses a reusable warm instance mode.

## Backend Modules

```text
backend/app/llm/vast/
  __init__.py
  client.py
  lifecycle.py
  provider.py
  schemas.py
  templates.py

backend/app/api/routes_vast.py
backend/app/tests/test_vast_provider.py
```

## Endpoints

Admin-only:

```text
POST /api/admin/vast/config
GET  /api/admin/vast/config
POST /api/admin/vast/sessions/start
GET  /api/admin/vast/sessions/{session_id}
POST /api/admin/vast/sessions/{session_id}/test-prompt
POST /api/admin/vast/sessions/{session_id}/destroy
POST /api/admin/vast/cleanup
```

Common users should not access these endpoints.

## Implementation Modes

### Mode 1 — Manual Warm-Up

Admin starts a Vast.ai model session manually, checks health, runs a test prompt, and destroys it.

This is the first implementation target.

### Mode 2 — Automatic Ephemeral

Only after Mode 1 works safely, allow the app to rent automatically for selected tasks when:

```text
VAST_ENABLED=true
LLM_PROVIDER=vast_ephemeral
admin allowed the task type
task explicitly allows remote GPU use
cost and runtime limits pass
```

## Acceptance Criteria

- Vast.ai provider is disabled by default.
- Vast.ai credentials are admin-only and never exposed to the frontend.
- Unit tests mock Vast.ai API calls; no real renting happens in tests.
- Provider enforces cost, GPU, runtime, and active-instance limits.
- Failed startup attempts trigger cleanup.
- Destroy endpoint works even after partial failures.
- Existing local/API LLM providers still work.
- Deterministic report fallback still works without any LLM.

---

# Final Portfolio Phases

After Phases 10-12 are implemented and validated:

```text
Final Phase 13: Demo data and example reports
Final Phase 14: Public portfolio deployment
Final Phase 15: Portfolio polish
```

Final demo should show:

```text
strategy analysis
source-grounded report
simulation
watchlist alert
options analysis
discovery candidate
human approval
ingest-to-RAG
future report using ingested knowledge
optional admin-only Vast.ai model session demo, if safe
```
