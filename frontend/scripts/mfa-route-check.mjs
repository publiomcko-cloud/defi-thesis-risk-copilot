import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createServer } from "node:http";

const factorId = "2b306a77-21dc-4110-ba71-537cb56b9e98";
const challengeId = "6a4cce2c-43fc-489f-9a73-e30df104776f";
const mockRequests = [];
const mockServer = createServer(async (request, response) => {
  const body = await readBody(request);
  mockRequests.push({ method: request.method, url: request.url, headers: request.headers, body });
  response.setHeader("Content-Type", "application/json");

  if (request.method === "GET" && request.url === "/auth/v1/user") {
    return send(response, 200, {
      factors: [{ id: factorId, status: "verified", friendly_name: "Primary app", factor_type: "totp" }],
    });
  }
  if (request.method === "POST" && request.url === "/auth/v1/token?grant_type=password") {
    return send(response, 200, {
      access_token: jwt("aal1"),
      refresh_token: "login-refresh-token",
      expires_in: 3600,
      user: {
        factors: [{ id: factorId, status: "verified", friendly_name: "Primary app", factor_type: "totp" }],
      },
    });
  }
  if (request.method === "POST" && request.url === "/auth/v1/factors") {
    const payload = JSON.parse(body || "{}");
    if (payload.friendly_name === "Provider failure") {
      return send(response, 503, { message: "sensitive provider detail" });
    }
    return send(response, 200, {
      id: factorId,
      friendly_name: payload.friendly_name,
      totp: { qr_code: "<svg><rect /></svg>", secret: "ABCDEF234567" },
    });
  }
  if (request.method === "POST" && request.url === `/auth/v1/factors/${factorId}/challenge`) {
    return send(response, 200, { id: challengeId, type: "totp" });
  }
  if (request.method === "POST" && request.url === `/auth/v1/factors/${factorId}/verify`) {
    return send(response, 200, {
      access_token: jwt("aal2"),
      refresh_token: "rotated-refresh-token",
      expires_in: 3600,
    });
  }
  if (request.method === "DELETE" && request.url === `/auth/v1/factors/${factorId}`) {
    return send(response, 200, { id: factorId });
  }
  return send(response, 404, { message: "not found" });
});

await listen(mockServer, 0);
const mockAddress = mockServer.address();
assert(mockAddress && typeof mockAddress === "object");
const appPort = await availablePort();
const appOrigin = `http://127.0.0.1:${appPort}`;
const app = spawn("./node_modules/.bin/next", ["start", "--hostname", "127.0.0.1", "--port", String(appPort)], {
  cwd: new URL("..", import.meta.url),
  env: {
    ...process.env,
    SUPABASE_URL: `http://127.0.0.1:${mockAddress.port}`,
    SUPABASE_ANON_KEY: "phase16-test-anon-key",
    SESSION_COOKIE_NAME: "phase16_test_session",
    COOKIE_SECURE: "false",
    ADMIN_MFA_REQUIRED: "true",
  },
  stdio: ["ignore", "pipe", "pipe"],
});
let appOutput = "";
app.stdout.on("data", (chunk) => { appOutput += chunk; });
app.stderr.on("data", (chunk) => { appOutput += chunk; });

try {
  await waitForApp(`${appOrigin}/account/security`, app);
  const accessToken = jwt("aal1");
  const cookie = [
    `phase16_test_session=${accessToken}`,
    `phase16_test_session_refresh=refresh-token`,
    `phase16_test_session_expires_at=${Date.now() + 3_600_000}`,
  ].join("; ");
  const authHeaders = { Cookie: cookie };
  const mutationHeaders = { ...authHeaders, Origin: appOrigin, "Content-Type": "application/json" };

  const loginResponse = await fetch(`${appOrigin}/api/auth/login`, {
    method: "POST",
    headers: { Origin: appOrigin, "Content-Type": "application/json" },
    body: JSON.stringify({ email: "admin@example.test", password: "test-password" }),
  });
  assert.equal(loginResponse.status, 200);
  assert.equal((await loginResponse.json()).next, "/account/security");
  assert(loginResponse.headers.getSetCookie().some((value) => value.startsWith("phase16_test_session=")));

  const stateResponse = await fetch(`${appOrigin}/api/auth/mfa`, { headers: authHeaders });
  assert.equal(stateResponse.status, 200);
  const state = await stateResponse.json();
  assert.equal(state.current_level, "aal1");
  assert.equal(state.next_level, "aal2");
  assert.equal(state.factors[0].friendly_name, "Primary app");

  const enrollResponse = await fetch(`${appOrigin}/api/auth/mfa/enroll`, {
    method: "POST",
    headers: mutationHeaders,
    body: JSON.stringify({ friendly_name: "Work phone" }),
  });
  assert.equal(enrollResponse.status, 200);
  const enrollment = await enrollResponse.json();
  assert.equal(enrollment.factor_id, factorId);
  assert.match(enrollment.qr_code, /^data:image\/svg\+xml/);

  const challengeResponse = await fetch(`${appOrigin}/api/auth/mfa/challenge`, {
    method: "POST",
    headers: mutationHeaders,
    body: JSON.stringify({ factor_id: factorId, code: "123456" }),
  });
  assert.equal(challengeResponse.status, 200);
  assert.deepEqual(await challengeResponse.json(), { status: "verified", assurance_level: "aal2" });
  const setCookies = challengeResponse.headers.getSetCookie();
  assert(setCookies.some((value) => value.startsWith("phase16_test_session=")));
  assert(setCookies.some((value) => value.startsWith("phase16_test_session_refresh=")));
  assert(setCookies.filter((value) => value.startsWith("phase16_test_session=")).every((value) => value.includes("HttpOnly")));
  assert(setCookies.filter((value) => value.startsWith("phase16_test_session_refresh=")).every((value) => value.includes("HttpOnly")));

  const deleteResponse = await fetch(`${appOrigin}/api/auth/mfa/${factorId}`, {
    method: "DELETE",
    headers: mutationHeaders,
  });
  assert.equal(deleteResponse.status, 200);

  const failureResponse = await fetch(`${appOrigin}/api/auth/mfa/enroll`, {
    method: "POST",
    headers: mutationHeaders,
    body: JSON.stringify({ friendly_name: "Provider failure" }),
  });
  assert.equal(failureResponse.status, 503);
  assert(!JSON.stringify(await failureResponse.json()).includes("sensitive provider detail"));

  const crossOrigin = await fetch(`${appOrigin}/api/auth/mfa/enroll`, {
    method: "POST",
    headers: { ...authHeaders, Origin: "https://attacker.example", "Content-Type": "application/json" },
    body: JSON.stringify({ friendly_name: "Blocked" }),
  });
  assert.equal(crossOrigin.status, 403);

  for (const request of mockRequests) {
    assert.equal(request.headers.cookie, undefined, "browser cookies must not reach Supabase Auth");
    assert.equal(request.headers.apikey, "phase16-test-anon-key");
    if (request.url === "/auth/v1/token?grant_type=password") {
      assert.equal(request.headers.authorization, undefined);
    } else {
      assert.match(request.headers.authorization ?? "", /^Bearer /);
    }
  }
  console.log("MFA route-handler checks passed.");
} catch (error) {
  if (appOutput) {
    console.error(appOutput);
  }
  throw error;
} finally {
  app.kill("SIGTERM");
  mockServer.close();
  await Promise.allSettled([waitForExit(app), closeServer(mockServer)]);
}

function jwt(aal) {
  return `header.${Buffer.from(JSON.stringify({ aal })).toString("base64url")}.signature`;
}

function send(response, status, body) {
  response.statusCode = status;
  response.end(JSON.stringify(body));
}

async function readBody(request) {
  let body = "";
  for await (const chunk of request) {
    body += chunk;
  }
  return body;
}

async function availablePort() {
  const server = createServer();
  await listen(server, 0);
  const address = server.address();
  assert(address && typeof address === "object");
  const port = address.port;
  await closeServer(server);
  return port;
}

function listen(server, port) {
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", resolve);
  });
}

function closeServer(server) {
  return new Promise((resolve) => {
    if (!server.listening) {
      resolve();
      return;
    }
    server.close(resolve);
  });
}

function waitForExit(child) {
  return new Promise((resolve) => {
    if (child.exitCode !== null || child.signalCode !== null) {
      resolve();
      return;
    }
    child.once("exit", resolve);
    setTimeout(() => child.kill("SIGKILL"), 5_000).unref();
  });
}

async function waitForApp(url, child) {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(`Next.js exited before startup with code ${child.exitCode}`);
    }
    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
    } catch {
      // Startup connection failures are expected until Next.js is listening.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("Timed out waiting for the Next.js MFA route test server.");
}
