import assert from "node:assert/strict";

import {
  challengeAndVerifyTotp,
  enrollTotpFactor,
  loadMfaState,
  unenrollMfaFactor,
} from "../src/lib/mfa-provider.ts";

const factorId = "2b306a77-21dc-4110-ba71-537cb56b9e98";
const challengeId = "6a4cce2c-43fc-489f-9a73-e30df104776f";

function jwt(aal: "aal1" | "aal2") {
  return `header.${Buffer.from(JSON.stringify({ aal })).toString("base64url")}.signature`;
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

{
  const calls: Array<{ path: string; init?: RequestInit }> = [];
  const result = await loadMfaState(jwt("aal1"), async (path, init) => {
    calls.push({ path, init });
    return jsonResponse({
      factors: [{
        id: factorId,
        status: "verified",
        friendly_name: "Primary app",
        factor_type: "totp",
        secret: "must-not-leak",
      }],
    });
  });
  assert.equal(result.ok, true);
  if (result.ok) {
    assert.equal(result.data.current_level, "aal1");
    assert.equal(result.data.next_level, "aal2");
    assert.deepEqual(Object.keys(result.data.factors[0]).sort(), [
      "created_at", "factor_type", "friendly_name", "id", "last_challenged_at", "status", "updated_at",
    ]);
  }
  assert.equal(calls[0].path, "/user");
  assert.equal(new Headers(calls[0].init?.headers).get("authorization"), `Bearer ${jwt("aal1")}`);
}

{
  const result = await enrollTotpFactor(jwt("aal1"), "Work phone", async (path, init) => {
    assert.equal(path, "/factors");
    assert.deepEqual(JSON.parse(String(init?.body)), {
      factor_type: "totp",
      friendly_name: "Work phone",
    });
    return jsonResponse({
      id: factorId,
      friendly_name: "Work phone",
      totp: { qr_code: "<svg><rect /></svg>", secret: "ABCDEF234567" },
    });
  });
  assert.equal(result.ok, true);
  if (result.ok) {
    assert.match(result.data.qr_code, /^data:image\/svg\+xml/);
    assert.equal(result.data.secret, "ABCDEF234567");
  }
}

{
  const calls: string[] = [];
  const result = await challengeAndVerifyTotp(jwt("aal1"), factorId, "123456", async (path, init) => {
    calls.push(path);
    if (path.endsWith("/challenge")) {
      return jsonResponse({ id: challengeId, type: "totp" });
    }
    assert.deepEqual(JSON.parse(String(init?.body)), { challenge_id: challengeId, code: "123456" });
    return jsonResponse({ access_token: jwt("aal2"), refresh_token: "rotated-refresh", expires_in: 3600 });
  });
  assert.equal(result.ok, true);
  assert.deepEqual(calls, [
    `/factors/${factorId}/challenge`,
    `/factors/${factorId}/verify`,
  ]);
}

{
  let callCount = 0;
  const result = await challengeAndVerifyTotp(jwt("aal1"), factorId, "123456", async () => {
    callCount += 1;
    return jsonResponse({ message: "provider unavailable" }, 503);
  });
  assert.deepEqual(result, { ok: false, status: 503 });
  assert.equal(callCount, 1, "verification must not run after a failed challenge");
}

{
  const result = await loadMfaState(jwt("aal1"), async () => {
    throw new Error("network unavailable");
  });
  assert.deepEqual(result, { ok: false, status: 502 });
}

{
  const invalid = await challengeAndVerifyTotp(jwt("aal1"), "../factor", "not-a-code", async () => {
    throw new Error("invalid input must not reach the provider");
  });
  assert.deepEqual(invalid, { ok: false, status: 400 });

  const removed = await unenrollMfaFactor(jwt("aal2"), factorId, async (path, init) => {
    assert.equal(path, `/factors/${factorId}`);
    assert.equal(init?.method, "DELETE");
    return jsonResponse({ id: factorId });
  });
  assert.equal(removed.ok, true);
}

console.log("MFA provider contract checks passed.");
