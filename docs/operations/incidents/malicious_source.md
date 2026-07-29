# Malicious Upload or Source — `knowledge.malicious-source`

Owner roles: knowledge owner (primary), security owner (backup). Communication
authority: assigned incident communications authority. Escalate to `SEV1` when
trusted retrieval may have used the source; otherwise begin at `SEV2`.

## Detection

Triggers include a scanner rejection, parser failure, source-poisoning report,
unexpected retrieval behavior, checksum mismatch, or storage-policy alert.
Record source/version identifiers only in approved private evidence.

## Immediate containment

Reject or tombstone the source/version, stop its ingestion/embedding jobs, and
remove it from active retrieval. Do not download or render suspicious content
outside an approved isolated scanner/parser environment.

## Eradication and scope

Verify source trust state, immutable version lineage, parser/chunker/embedding
generation, retrieval events, and citations through server-side metadata.
Identify whether any report used the version without exposing source content.

## Recovery and rollback

Re-ingest only from a verified clean immutable version after scanner and
integrity checks pass. Keep durable storage disabled or use JSON fallback when
the validated recovery path is unavailable. Rollback restores the last known
safe active generation/version, not the suspect source.

## Communications

The communications authority decides whether users need a correction after
confirmed report/citation impact. Do not publish malicious content or exploit
details.

## Evidence

Record source/version/generation references, scanner/parser outcome category,
trust-state transitions, retrieval/report impact references, and verification
result. Exclude document bytes, object keys, signed URLs, and raw prompts.

## Retrospective

Review allowlists, scanning/quarantine, parser limits, source approval,
retrieval evaluation, and whether supplier/provider disclosure is needed.
