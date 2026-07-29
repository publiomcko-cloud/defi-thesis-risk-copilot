# Phase 19I Controlled Durable-RAG Rollout

Status: **local rollout controls implemented; deployed evidence pending.**

This runbook collects narrow evidence for Phase 18 durable knowledge without a
broad customer activation. It never authorizes real Vast.ai rentals:
`VAST_DRY_RUN=true` and `VAST_REAL_RENTALS_ENABLED=false` are mandatory in
every stage. Do not use customer private data, print credentials, or store
evidence in this repository.

## Preconditions

Obtain written approval identifying the isolated target, synthetic owner,
synthetic organization member, scoped worker, evidence location, time window,
rollback owner, and stop condition. Confirm merged migrations `0017` through
`0021`, a verified private Supabase bucket/RLS policy, pgvector extension,
backup readiness, and alert/runbook access.

The production shadow target must set only the approved minimum:

```text
CONTROLLED_RAG_VALIDATION_ENABLED=true
KNOWLEDGE_STORAGE_ENABLED=true
KNOWLEDGE_UPLOAD_SCANNING_REQUIRED=true
KNOWLEDGE_UPLOAD_SCANNER_URL=https://approved-scanner.example.internal/scan
DOCUMENT_INGEST_ENABLED=true
JOBS_ENABLED=true
WORKER_API_ENABLED=true
KNOWLEDGE_EMBEDDINGS_ENABLED=true
KNOWLEDGE_SHADOW_RETRIEVAL_ENABLED=true
KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=false
VAST_DRY_RUN=true
VAST_REAL_RENTALS_ENABLED=false
```

Run the read-only check from the trusted backend environment:

```bash
cd backend
python -m scripts.check_knowledge_readiness --probe-storage
python -m scripts.check_controlled_rag_rollout --mode shadow
```

Both commands must pass. The first creates and deletes one synthetic private
object; it prints neither the bucket name nor the object key. The second
contains only boolean check names and statuses. A blocked result is a stop
condition, not a reason to bypass a control.

## Synthetic Evidence Sequence

1. With a synthetic owner and synthetic non-member, verify private source and
   document metadata is visible only to the owner. Verify an active synthetic
   organization member sees only active-organization content and the non-member
   receives `404`.
2. Upload a bounded synthetic Markdown document, approve it explicitly, and
   submit `document.ingest` through the scoped trusted worker. Record only job
   IDs in the approved private evidence system; do not put source text, storage
   keys, or tokens in an issue or commit.
3. Submit embeddings and query shadow retrieval. Record aggregate timing,
   citation IDs, expected tenant visibility, and absence of storage keys. Run a
   normal report with the same synthetic strategy and confirm JSON RAG remains
   the report authority during the shadow window.
4. In a separately isolated **non-production** target only, set
   `CONTROLLED_RAG_VALIDATION_ISOLATED=true` and
   `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=true`, then run:

   ```bash
   python -m scripts.check_controlled_rag_rollout --mode primary-synthetic
   ```

   Run one authenticated synthetic report and one anonymous synthetic report.
   Confirm exact citation lineage, public-only anonymous retrieval, owner and
   active-organization isolation, and a durable-versus-JSON comparison. The
   application rejects the primary flag when `APP_ENV=production`.

5. Roll back by first setting `KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED=false`,
   redeploying, and rerunning the shadow check. Keep durable rows and objects
   intact for investigation. Disable ingestion/embedding/shadow flags only
   after confirming JSON reports and queue recovery. Do not delete data as a
   rollback action.

## Evidence and Completion Boundary

Record the deployment commit, target classification, approval reference,
timestamps, check statuses, synthetic identities by private reference, worker
state, citations by ID, JSON/durable comparison result, rollback result, and
alert observations in the approved private operations system. Never record
tokens, object keys, signed URLs, content, email addresses, or report bodies.

This prepares Phase 19I. It is not a claim that bucket policy, RLS, worker
availability, alert delivery, a primary report path, or rollback has been
validated in a deployed environment. Broad activation and launch approval stay
with Phase 22.
