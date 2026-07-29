import assert from "node:assert/strict";

import { readBodyWithinLimit } from "../src/lib/request-body-limit.ts";

function streamedRequest(chunks: string[], headers: HeadersInit = {}): Request {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    }
  });
  return new Request("http://bff.example.test/api/backend/api/analyze", {
    method: "POST",
    headers,
    body: stream,
    // Required by Node's Fetch implementation for a streamed request body.
    duplex: "half"
  } as RequestInit);
}

const chunked = await readBodyWithinLimit(streamedRequest(["123", "456"]), 5);
assert.equal(chunked.ok, false);
if (!chunked.ok) assert.equal(chunked.status, 413);

const misleading = await readBodyWithinLimit(streamedRequest(["123456"], { "content-length": "1" }), 5);
assert.equal(misleading.ok, false);
if (!misleading.ok) assert.equal(misleading.status, 413);

const invalid = await readBodyWithinLimit(streamedRequest(["1"], { "content-length": "not-a-number" }), 5);
assert.equal(invalid.ok, false);
if (!invalid.ok) assert.equal(invalid.status, 400);
const accepted = await readBodyWithinLimit(streamedRequest(["12", "34"]), 5);
assert.equal(accepted.ok, true);
if (accepted.ok) assert.equal(new TextDecoder().decode(accepted.body), "1234");

console.log("BFF bounded-body checks passed.");
