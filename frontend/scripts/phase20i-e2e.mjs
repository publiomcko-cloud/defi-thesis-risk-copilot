import assert from "node:assert/strict";
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { chromium } from "playwright";

const now = "2026-08-28T18:00:00.000Z";
const users = {
  owner: { id: "request-owner", email: "request-owner@example.test", role: "common" },
  other: { id: "request-other", email: "request-other@example.test", role: "common" },
  organizationAdmin: { id: "request-org-admin", email: "request-org-admin@example.test", role: "common" },
  platformAdmin: { id: "request-platform-admin", email: "request-platform-admin@example.test", role: "admin" },
};
const state = {
  customerRequests: [],
  customerCalls: [],
  backendCalls: [],
  healthHealthy: true,
  healthAuthHeaders: [],
  sequence: 0,
};

const upstream = createServer(async (request, response) => {
  const body = await readBody(request);
  const url = new URL(request.url ?? "/", "http://localhost");
  const payload = parseJson(body);
  const method = request.method ?? "GET";
  if (url.pathname.startsWith("/auth/v1/")) return handleSupabase(method, url, payload, response);
  return handleBackend(method, url, payload, request.headers, response);
});

await listen(upstream, 0);
const upstreamAddress = upstream.address();
assert(upstreamAddress && typeof upstreamAddress === "object");
const appPort = await availablePort();
const appOrigin = `http://127.0.0.1:${appPort}`;
const upstreamOrigin = `http://127.0.0.1:${upstreamAddress.port}`;
const app = spawn("./node_modules/.bin/next", ["start", "--hostname", "127.0.0.1", "--port", String(appPort)], {
  cwd: new URL("..", import.meta.url),
  env: {
    ...process.env,
    BACKEND_API_BASE_URL: upstreamOrigin,
    SUPABASE_URL: upstreamOrigin,
    SUPABASE_ANON_KEY: "phase20i-browser-key",
    SESSION_COOKIE_NAME: "phase20i_browser_session",
    COOKIE_SECURE: "false",
    BFF_MAX_REQUEST_BYTES: "512",
  },
  stdio: ["ignore", "pipe", "pipe"],
});
let appOutput = "";
app.stdout.on("data", (chunk) => { appOutput += chunk; });
app.stderr.on("data", (chunk) => { appOutput += chunk; });

let browser;
let activePage;
try {
  await waitForApp(`${appOrigin}/status`, app);
  browser = await chromium.launch({ headless: true });
  await exercisePublicStatus(browser);
  await exerciseUnauthenticatedSupport(browser);
  await exerciseSupportWorkspace(browser);
  await exerciseBffContracts(browser);
  console.log("Phase 20I browser E2E passed: support workspace, private-content boundary, BFF contract, and public-safe status.");
} catch (error) {
  if (appOutput) console.error(appOutput);
  throw error;
} finally {
  await browser?.close();
  app.kill("SIGTERM");
  await Promise.allSettled([waitForExit(app), closeServer(upstream)]);
}

async function exercisePublicStatus(browserInstance) {
  const context = await browserInstance.newContext();
  const page = await context.newPage();
  activePage = page;
  const before = state.customerCalls.length;
  await page.goto(`${appOrigin}/status`);
  await page.getByRole("heading", { name: "Current Service Status" }).waitFor();
  await page.getByText("Backend API", { exact: true }).waitFor();
  await page.getByText("Operational", { exact: true }).waitFor();
  assert.equal(await page.getByText(/database host|migration|tenant storage|credential|internal alert id/i).count(), 0, "status must not expose internal operational details");
  assert.equal(state.customerCalls.length, before, "status must not request customer data");
  assert.equal(state.healthAuthHeaders.at(-1), "", "public status health check must not require an authentication token");

  state.healthHealthy = false;
  await page.reload();
  await page.getByText("Unavailable", { exact: true }).waitFor();
  assert.equal(await page.getByRole("heading", { name: "Current Service Status" }).count(), 1, "status page remains usable when the backend is unavailable");
  state.healthHealthy = true;
  await context.close();
}

async function exerciseUnauthenticatedSupport(browserInstance) {
  const context = await browserInstance.newContext();
  const page = await context.newPage();
  activePage = page;
  await page.goto(`${appOrigin}/support`);
  await page.getByRole("heading", { name: "Sign in required" }).waitFor();
  assert.equal(await page.getByRole("link", { name: "Log in" }).getAttribute("href"), "/login");
  await context.close();
}

async function exerciseSupportWorkspace(browserInstance) {
  const ownerContext = await browserInstance.newContext();
  const page = await ownerContext.newPage();
  activePage = page;
  const consoleMessages = [];
  page.on("console", (message) => consoleMessages.push(message.text()));
  await login(page, users.owner.email);
  await page.goto(`${appOrigin}/support`);
  await page.getByRole("heading", { name: "Support and Requests" }).waitFor();
  await page.getByRole("heading", { name: "New request" }).waitFor();
  assert.equal(await page.locator('input[type="file"]').count(), 0, "attachments must not be offered");
  assert.equal(/billing|zendesk|intercom|freshdesk|provider/i.test(await page.locator("main").innerText()), false, "support workspace must not expose billing or helpdesk-provider UI");

  await page.getByLabel("Organization context (optional)").selectOption("org-browser-20i");
  await page.getByLabel("Request type").selectOption("privacy_access_export");
  assert.equal(await page.getByLabel("Organization context (optional)").count(), 0, "privacy types must hide organization context");
  await page.getByRole("link", { name: "Open account export" }).waitFor();
  assert.equal(await page.getByRole("link", { name: "Open account export" }).getAttribute("href"), "/account");
  await page.getByLabel("Request type").selectOption("privacy_deletion");
  await page.getByRole("link", { name: "Open account deletion" }).waitFor();
  assert.equal(await page.getByRole("link", { name: "Open account deletion" }).getAttribute("href"), "/account");

  const rejectedSubject = "PRIVATE_REJECTED_SUBJECT_20I_" + "s".repeat(128);
  await page.getByLabel("Request type").selectOption("support");
  await forceInputValue(page.getByLabel("Subject"), rejectedSubject);
  await page.getByLabel("Description").fill("A bounded validation test.");
  await page.getByRole("button", { name: "Create request" }).click();
  const rejectedAlert = page.locator(".error-text[role='alert']");
  await rejectedAlert.waitFor();
  assert.equal(await rejectedAlert.innerText(), "Review the request details and try again.");
  assert.equal((await rejectedAlert.innerText()).includes(rejectedSubject), false, "rejected subject must not be echoed in error UI");

  const rejectedDescription = "PRIVATE_REJECTED_DESCRIPTION_20I_" + "d".repeat(4008);
  await page.getByLabel("Subject").fill("Bounded error request");
  await forceInputValue(page.getByLabel("Description"), rejectedDescription);
  await page.getByRole("button", { name: "Create request" }).click();
  await rejectedAlert.waitFor();
  assert.equal((await rejectedAlert.innerText()).includes(rejectedDescription), false, "rejected description must not be echoed in error UI");

  const privateSubject = "PRIVATE_BROWSER_SUBJECT_20I";
  const privateDescription = "PRIVATE_BROWSER_DESCRIPTION_20I";
  await page.getByLabel("Subject").fill(privateSubject);
  await page.getByLabel("Description").fill(privateDescription);
  await page.getByLabel("Organization context (optional)").selectOption("org-browser-20i");
  await page.getByRole("button", { name: "Create request" }).click();
  await page.getByText("Request created.").waitFor();
  await page.getByRole("cell", { name: privateSubject }).waitFor();
  assert.equal(await page.getByLabel("Subject").inputValue(), "", "successful creation clears unsaved subject text");
  assert.equal(await page.getByLabel("Description").inputValue(), "", "successful creation clears unsaved description text");

  const ordinaryCall = state.customerCalls.find((call) => call.body?.subject === privateSubject);
  assert(ordinaryCall, "support creation must reach the customer-request API");
  assert.deepEqual(Object.keys(ordinaryCall.body).sort(), ["description", "organization_id", "request_type", "subject"], "browser may send only approved ordinary-request fields");
  assert.equal(ordinaryCall.url.includes(privateSubject) || ordinaryCall.url.includes(privateDescription), false, "private request text must not enter an outbound URL");
  assert.equal(ordinaryCall.headers.cookie.includes("phase20i_browser_session"), false, "BFF must keep the browser session cookie server-managed");

  await page.getByLabel("Request type").selectOption("privacy_access_export");
  await page.getByLabel("Subject").fill("Privacy export tracking");
  await page.getByLabel("Description").fill("Track the existing account export workflow.");
  await page.getByRole("button", { name: "Create request" }).click();
  await page.getByText("Request created.").waitFor();
  const privacyCall = state.customerCalls.find((call) => call.body?.subject === "Privacy export tracking");
  assert(privacyCall, "privacy creation must reach the customer-request API");
  assert.deepEqual(Object.keys(privacyCall.body).sort(), ["description", "request_type", "subject"], "privacy requests must clear organization context before submission");

  await page.getByRole("button", { name: "View" }).first().click();
  await page.getByRole("heading", { name: "Request detail" }).waitFor();
  await page.getByRole("button", { name: "Close request" }).click();
  await page.getByRole("dialog", { name: "Close request" }).getByRole("button", { name: "Close request" }).click();
  await page.getByText("Request closed.").waitFor();
  await page.getByText("closed", { exact: true }).waitFor();

  const unsavedSubject = "PRIVATE_UNSAVED_SUBJECT_20I";
  await page.getByLabel("Request type").selectOption("feedback");
  await page.getByLabel("Subject").fill(unsavedSubject);
  await page.getByLabel("Description").fill("This draft intentionally remains only in component state.");
  await page.reload();
  await page.getByRole("heading", { name: "New request" }).waitFor();
  assert.equal(await page.getByLabel("Subject").inputValue(), "", "refresh must not preserve unsaved private subject text");
  assert.equal(await page.getByLabel("Description").inputValue(), "", "refresh must not preserve unsaved private description text");
  assert.equal(new URL(page.url()).search, "", "private text must not enter query parameters");
  assert.equal(new URL(page.url()).hash, "", "private text must not enter URL fragments");
  const storage = await page.evaluate(() => ({
    local: Object.entries(localStorage),
    session: Object.entries(sessionStorage),
    title: document.title,
    metadata: document.head.innerHTML,
  }));
  const browserVisibleState = JSON.stringify(storage);
  assert.equal(browserVisibleState.includes(privateSubject) || browserVisibleState.includes(privateDescription) || browserVisibleState.includes(unsavedSubject), false, "private request text must not enter storage, title, or metadata");
  const cookies = await ownerContext.cookies(appOrigin);
  assert.equal(JSON.stringify(cookies).includes(privateSubject) || JSON.stringify(cookies).includes(privateDescription), false, "private request text must not enter cookies");
  assert.equal(consoleMessages.some((message) => message.includes(privateSubject) || message.includes(privateDescription) || message.includes(unsavedSubject)), false, "private request text must not enter browser console output");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByLabel("Subject").focus();
  assert.equal(await page.getByLabel("Subject").evaluate((element) => document.activeElement === element), true, "support controls remain keyboard-operable on mobile");

  const firstRequestId = ordinaryCall.response.id;
  await ownerContext.close();
  await exerciseCrossUserIsolation(browserInstance, firstRequestId, privateSubject);
}

async function exerciseCrossUserIsolation(browserInstance, requestId, privateSubject) {
  for (const user of [users.other, users.organizationAdmin, users.platformAdmin]) {
    const context = await browserInstance.newContext();
    const page = await context.newPage();
    activePage = page;
    await login(page, user.email);
    await page.goto(`${appOrigin}/support`);
    await page.getByRole("heading", { name: "Your requests" }).waitFor();
    assert.equal(await page.getByText(privateSubject, { exact: true }).count(), 0, "other browser users must not receive another owner's request text");
    const response = await page.evaluate(async (id) => {
      const result = await fetch(`/api/backend/api/customer-requests/${id}`);
      return result.status;
    }, requestId);
    assert.equal(response, 404, "customer-request detail remains owner-scoped through the BFF");
    await context.close();
  }
}

async function exerciseBffContracts(browserInstance) {
  const context = await browserInstance.newContext();
  const page = await context.newPage();
  activePage = page;
  const arbitrary = await page.request.get(`${appOrigin}/api/backend/api/not-allowlisted`);
  assert.equal(arbitrary.status(), 404, "arbitrary backend API paths must remain denied");
  const unsupportedMethod = await page.request.patch(`${appOrigin}/api/backend/api/customer-requests`, { data: {} });
  assert.equal(unsupportedMethod.status(), 404, "customer-request method restrictions must be enforced by the BFF");
  const inventedCustomerPath = await page.request.get(`${appOrigin}/api/backend/api/customer-requests/request-id/not-allowed`);
  assert.equal(inventedCustomerPath.status(), 404, "invented customer-request paths must be denied by the BFF");
  const oversized = await page.request.post(`${appOrigin}/api/backend/api/customer-requests`, {
    data: { request_type: "support", subject: "limit", description: "x".repeat(1024) },
  });
  assert.equal(oversized.status(), 413, "customer-request body limit must be enforced before forwarding");
  const crossOrigin = await page.request.post(`${appOrigin}/api/backend/api/customer-requests`, {
    headers: { Origin: "https://untrusted.example.test" },
    data: { request_type: "support", subject: "cross", description: "origin" },
  });
  assert.equal(crossOrigin.status(), 403, "customer-request BFF mutations require a trusted origin");
  const redirect = await page.request.get(`${appOrigin}/api/backend/api/protocols`);
  assert.equal(redirect.status(), 502, "unsafe backend redirects must remain denied");
  await context.close();
}

function handleSupabase(method, url, payload, response) {
  if (method === "POST" && url.pathname === "/auth/v1/token" && url.searchParams.get("grant_type") === "password") {
    const user = Object.values(users).find((candidate) => candidate.email === payload?.email);
    return user ? send(response, 200, session(user)) : send(response, 400, { detail: "Login failed" });
  }
  return send(response, 404, { detail: "Unhandled Supabase route" });
}

function handleBackend(method, url, payload, headers, response) {
  if (url.pathname === "/health") {
    state.healthAuthHeaders.push(headers.authorization ?? "");
    return state.healthHealthy
      ? send(response, 200, { status: "healthy", service: "test", environment: "test", timestamp: now })
      : send(response, 503, { detail: "Unavailable" });
  }
  if (url.pathname === "/api/protocols") {
    response.writeHead(302, { location: "https://untrusted.example.test" });
    response.end();
    return;
  }
  const actor = actorForToken(headers.authorization ?? "");
  if (url.pathname === "/api/auth/me") return actor ? send(response, 200, userPayload(actor)) : send(response, 401, { detail: "Authentication required" });
  if (!actor) return send(response, 401, { detail: "Authentication required" });

  const call = { method, path: url.pathname, url: url.href, body: payload, headers: { authorization: headers.authorization ?? "", cookie: headers.cookie ?? "" }, response: null };
  state.backendCalls.push(call);
  const finish = (status, body) => {
    call.response = body;
    if (url.pathname.startsWith("/api/customer-requests")) state.customerCalls.push(call);
    return send(response, status, body);
  };
  if (url.pathname === "/api/organizations" && method === "GET") {
    const visible = actor.id === users.owner.id || actor.id === users.organizationAdmin.id
      ? [{ id: "org-browser-20i", name: "Browser Organization", status: "active" }]
      : [];
    return finish(200, { items: visible });
  }
  if (url.pathname === "/api/customer-requests" && method === "GET") {
    return finish(200, { items: state.customerRequests.filter((item) => item.owner_user_id === actor.id).map(publicRequest) });
  }
  if (url.pathname === "/api/customer-requests" && method === "POST") {
    const validation = validateCustomerRequest(payload);
    if (validation) return finish(422, validation);
    const record = {
      id: `creq-browser-${++state.sequence}`,
      owner_user_id: actor.id,
      request_type: payload.request_type,
      subject: payload.subject,
      description: payload.description,
      organization_id: payload.organization_id ?? null,
      workflow_state: "open",
      verification_state: payload.request_type.startsWith("privacy_") ? "authenticated" : "not_required",
      created_at: now,
      updated_at: now,
      closed_at: null,
    };
    state.customerRequests.unshift(record);
    return finish(201, publicRequest(record));
  }
  const detail = /^\/api\/customer-requests\/([^/]+)(?:\/close)?$/.exec(url.pathname);
  if (detail) {
    const record = state.customerRequests.find((item) => item.id === detail[1] && item.owner_user_id === actor.id);
    if (!record) return finish(404, { detail: "Customer request not found" });
    if (method === "GET" && !url.pathname.endsWith("/close")) return finish(200, publicRequest(record));
    if (method === "POST" && url.pathname.endsWith("/close")) {
      if (record.workflow_state !== "closed") {
        record.workflow_state = "closed";
        record.closed_at = now;
        record.updated_at = now;
      }
      return finish(200, publicRequest(record));
    }
  }
  return finish(404, { detail: "Unhandled backend route" });
}

function validateCustomerRequest(payload) {
  const allowed = new Set(["request_type", "subject", "description", "organization_id"]);
  if (!payload || typeof payload !== "object" || Object.keys(payload).some((key) => !allowed.has(key))) return safeValidationError();
  if (!["support", "feedback", "abuse_report", "privacy_access_export", "privacy_deletion"].includes(payload.request_type)) return safeValidationError();
  if (typeof payload.subject !== "string" || payload.subject.length < 1 || payload.subject.length > 120) return safeValidationError();
  if (typeof payload.description !== "string" || payload.description.length < 1 || payload.description.length > 4000) return safeValidationError();
  if (payload.request_type.startsWith("privacy_") && "organization_id" in payload) return safeValidationError();
  return null;
}

function safeValidationError() {
  return { detail: [{ loc: ["body"], msg: "Invalid request field.", type: "invalid_request" }] };
}

function publicRequest(record) {
  const { owner_user_id, ...response } = record;
  return response;
}

function actorForToken(value) {
  const token = value.replace(/^Bearer\s+/i, "");
  return Object.values(users).find((user) => token === `access-${user.id}`) ?? null;
}

function userPayload(user) {
  return { id: user.id, email: user.email, role: user.role, platform_role: user.role === "admin" ? "admin" : "user", is_active: true, auth_enabled: true };
}

function session(user) {
  return { access_token: `access-${user.id}`, refresh_token: `refresh-${user.id}`, expires_in: 3600, user: { id: user.id, email: user.email, factors: [] } };
}

async function login(page, email) {
  await page.goto(`${appOrigin}/login`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("browser-test-password");
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL(/\/account$/);
}

async function forceInputValue(locator, value) {
  await locator.evaluate((element) => element.removeAttribute("maxlength"));
  await locator.fill(value);
}

function readBody(request) {
  return new Promise((resolve) => {
    let body = "";
    request.on("data", (chunk) => { body += chunk; });
    request.on("end", () => resolve(body));
  });
}

function parseJson(body) {
  try {
    return body ? JSON.parse(body) : null;
  } catch {
    return null;
  }
}

function send(response, status, body) {
  response.writeHead(status, { "content-type": "application/json" });
  response.end(JSON.stringify(body));
}

function listen(server, port) {
  return new Promise((resolve) => server.listen(port, "127.0.0.1", resolve));
}

function closeServer(server) {
  return new Promise((resolve) => server.close(resolve));
}

function waitForExit(process) {
  return new Promise((resolve) => process.once("exit", resolve));
}

async function availablePort() {
  const server = createServer();
  await listen(server, 0);
  const address = server.address();
  assert(address && typeof address === "object");
  const { port } = address;
  await closeServer(server);
  return port;
}

async function waitForApp(url, process) {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (process.exitCode !== null) throw new Error("Next.js exited before Phase 20I E2E could start");
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("Timed out waiting for Next.js Phase 20I E2E server");
}
