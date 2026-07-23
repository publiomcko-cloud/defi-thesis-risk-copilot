import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { chromium } from "playwright";

const factorId = "11111111-1111-4111-8111-111111111111";
const now = "2026-07-21T12:00:00.000Z";
const artifactsDirectory = new URL("../test-results/phase16-e2e/", import.meta.url);
const state = {
  anonymousReports: new Map(),
  expiredAnonymousSessions: new Set(),
  theses: [],
  reports: new Map(),
  organization: null,
  memberships: [],
  consents: [],
  mfaFactors: [],
  refreshCount: 0,
  recoveryExchanges: 0,
  auditActions: [],
  backendTokens: [],
  supabaseCookies: []
};

const upstream = createServer(async (request, response) => {
  const body = await readBody(request);
  const url = new URL(request.url ?? "/", "http://localhost");
  const method = request.method ?? "GET";
  const payload = parseJson(body);
  const authorization = request.headers.authorization ?? "";
  const token = authorization.replace(/^Bearer\s+/i, "");

  if (url.pathname.startsWith("/auth/v1/")) {
    state.supabaseCookies.push(request.headers.cookie ?? "");
    return handleSupabase(method, url, payload, token, response);
  }
  return handleBackend(method, url, payload, token, request.headers.cookie ?? "", response);
});

await listen(upstream, 0);
const upstreamAddress = upstream.address();
assert(upstreamAddress && typeof upstreamAddress === "object");
const appPort = await availablePort();
const appOrigin = `http://localhost:${appPort}`;
const upstreamOrigin = `http://127.0.0.1:${upstreamAddress.port}`;
const app = spawn("./node_modules/.bin/next", ["start", "--hostname", "127.0.0.1", "--port", String(appPort)], {
  cwd: new URL("..", import.meta.url),
  env: {
    ...process.env,
    BACKEND_API_BASE_URL: upstreamOrigin,
    SUPABASE_URL: upstreamOrigin,
    SUPABASE_ANON_KEY: "phase16-browser-test-key",
    SESSION_COOKIE_NAME: "phase16_browser_session",
    COOKIE_SECURE: "false",
    ADMIN_MFA_REQUIRED: "true",
    BFF_AUDIT_SECRET: "phase16-browser-audit"
  },
  stdio: ["ignore", "pipe", "pipe"]
});
let appOutput = "";
app.stdout.on("data", (chunk) => { appOutput += chunk; });
app.stderr.on("data", (chunk) => { appOutput += chunk; });

let browser;
let activePage;
let activeContext;

try {
  await waitForApp(`${appOrigin}/login`, app);
  browser = await chromium.launch({ headless: true });

  await runAnonymousFlow(browser);
  await runRecoveryFlow(browser);
  await runAuthenticatedFlow(browser);
  await runMobileKeyboardSmoke(browser);

  assert(state.refreshCount >= 1, "an expired access token must refresh through the BFF");
  assert.equal(state.recoveryExchanges, 1, "recovery callback must exchange its code once");
  assert.deepEqual(
    state.auditActions.sort(),
    ["mfa.challenge_verified", "mfa.enrollment_started", "mfa.factor_unenrolled"],
  );
  assert(state.backendTokens.includes("access-owner-refreshed"), "BFF must forward the refreshed access token");
  assert(state.supabaseCookies.every((cookie) => cookie === ""), "browser cookies must not reach Supabase Auth");
  console.log("Phase 16 browser E2E passed: anonymous, BFF session, account, thesis, organization, recovery, MFA, and mobile flows.");
} catch (error) {
  await mkdir(artifactsDirectory, { recursive: true });
  if (activePage) {
    await activePage.screenshot({ path: new URL("failure.png", artifactsDirectory).pathname, fullPage: true }).catch(() => {});
  }
  if (activeContext) {
    await activeContext.tracing.stop({ path: new URL("failure-trace.zip", artifactsDirectory).pathname }).catch(() => {});
  }
  if (appOutput) {
    console.error(appOutput);
  }
  throw error;
} finally {
  await activeContext?.tracing.stop().catch(() => {});
  await browser?.close();
  app.kill("SIGTERM");
  await Promise.allSettled([waitForExit(app), closeServer(upstream)]);
}

async function runAnonymousFlow(browserInstance) {
  const context = await browserInstance.newContext();
  activeContext = context;
  await context.tracing.start({ screenshots: true, snapshots: true });
  const page = await context.newPage();
  activePage = page;
  await page.route("**/api/auth/session", async (route) => {
    await sleep(250);
    await route.continue();
  });
  await page.goto(`${appOrigin}/account`);
  await page.getByText("Loading account...").waitFor();
  assert.equal(await page.getByText("owner@example.test").count(), 0, "private account content must not flash before session resolution");
  await page.getByText("Sign in required").waitFor();

  await page.goto(`${appOrigin}/analyze`);
  await page.getByLabel("Strategy description").fill("Evaluate a hypothetical collateralized fixed-yield strategy with liquidity and liquidation assumptions.");
  await page.getByRole("button", { name: "Analyze Strategy" }).click();
  await page.waitForURL(/\/reports\/anon-report-a$/);
  await page.getByRole("heading", { name: "Strategy Risk Report" }).waitFor();

  const otherContext = await browserInstance.newContext();
  const otherPage = await otherContext.newPage();
  await otherPage.goto(`${appOrigin}/reports/anon-report-a`);
  await otherPage.getByRole("heading", { name: "Report temporarily unavailable" }).waitFor();
  await otherContext.close();

  state.expiredAnonymousSessions.add("anon-browser-a");
  await page.reload();
  await page.getByRole("heading", { name: "Report temporarily unavailable" }).waitFor();
  await context.close();
}

async function runRecoveryFlow(browserInstance) {
  const context = await browserInstance.newContext();
  activeContext = context;
  await context.tracing.start({ screenshots: true, snapshots: true });
  const page = await context.newPage();
  activePage = page;
  await page.goto(`${appOrigin}/api/auth/recovery-callback?code=recovery-code&next=/reset-password`);
  await page.waitForURL(/\/reset-password$/);
  await page.getByLabel("Password").fill("recovered-password");
  await page.getByRole("button", { name: "Update password" }).click();
  await page.getByText("Password updated.").waitFor();
  await context.close();
}

async function runAuthenticatedFlow(browserInstance) {
  const context = await browserInstance.newContext({ acceptDownloads: true });
  activeContext = context;
  await context.tracing.start({ screenshots: true, snapshots: true });
  const page = await context.newPage();
  activePage = page;
  await login(page, "owner@example.test");
  await page.getByText("owner@example.test").waitFor();
  await page.getByRole("link", { name: "Account" }).waitFor();
  assert.equal(await page.getByRole("link", { name: "Login" }).count(), 0, "header must update after authentication");

  await page.getByRole("button", { name: "Accept terms" }).click();
  await page.getByText("Terms consent recorded.").waitFor();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export" }).click();
  await (await download).delete();
  page.once("dialog", async (dialog) => {
    assert.equal(dialog.type(), "prompt");
    await dialog.accept("DELETE");
  });
  await page.getByRole("button", { name: "Delete" }).click();
  await page.getByText("Account deletion requested.").waitFor();

  await context.addCookies([{
    name: "phase16_browser_session_expires_at",
    value: "0",
    url: appOrigin,
    httpOnly: true,
    sameSite: "Lax"
  }]);
  await page.goto(`${appOrigin}/theses`);
  await page.getByRole("heading", { name: "Save Thesis" }).waitFor();
  await page.getByLabel("Title").fill("Fixed yield thesis");
  await page.getByLabel("Strategy text").fill("Assess the hypothetical fixed-yield position before using it in a research workflow.");
  await page.getByLabel("Protocols").fill("pendle, morpho");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await page.getByText("Thesis saved.").waitFor();
  await page.getByRole("button", { name: "Edit", exact: true }).click();
  await page.getByRole("heading", { name: "Edit Thesis" }).waitFor();
  await page.getByLabel("Title").fill("Updated fixed yield thesis");
  await page.getByRole("button", { name: "Update", exact: true }).click();
  await page.getByText("Thesis updated.").waitFor();
  const thesisCard = page.locator("article").filter({ hasText: "Updated fixed yield thesis" });
  await thesisCard.getByRole("link", { name: "Analyze" }).click();
  await page.getByRole("button", { name: "Analyze Strategy" }).click();
  await page.waitForURL(/\/reports\/owner-report$/);
  await page.getByRole("heading", { name: "Strategy Risk Report" }).waitFor();
  await page.goto(`${appOrigin}/theses`);
  await page.locator("article").filter({ hasText: "Updated fixed yield thesis" }).getByRole("button", { name: "Delete" }).click();
  await page.getByText("Thesis deleted.").waitFor();
  const refreshedCookies = await context.cookies(appOrigin);
  assert(
    refreshedCookies.some((cookie) => cookie.name === "phase16_browser_session" && cookie.value === "access-owner-refreshed"),
    `BFF refresh must rotate the browser access cookie: ${JSON.stringify(refreshedCookies)}`,
  );
  assert(
    Number(refreshedCookies.find((cookie) => cookie.name === "phase16_browser_session_expires_at")?.value ?? 0) > Date.now(),
    `BFF refresh must rotate the browser expiry cookie: ${JSON.stringify(refreshedCookies)}`,
  );

  await page.goto(`${appOrigin}/account`);
  await page.getByRole("button", { name: "Logout" }).click();
  await page.getByText("Signed out.").waitFor();
  await page.getByText("Sign in required").waitFor();
  await page.getByRole("link", { name: "Login" }).waitFor();
  await login(page, "owner@example.test");

  await page.goto(`${appOrigin}/organizations`);
  await page.getByRole("heading", { name: "Create Organization" }).waitFor();
  await page.getByLabel("Name").fill("Research Guild");
  await page.getByRole("button", { name: "Create", exact: true }).click();
  await page.getByText("Organization created.").waitFor();
  await page.getByText("owner@example.test · owner · active").waitFor();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Remove", exact: true }).first().click();
  await page.getByText("Cannot remove the final active organization owner").waitFor();
  await page.getByLabel("Invite email").fill("member@example.test");
  await page.getByRole("button", { name: "Invite", exact: true }).click();
  await page.getByText("Member invitation saved.").waitFor();
  await page.getByText("member@example.test · member · active").waitFor();
  await page.getByLabel("Role for member@example.test").selectOption("owner");
  await page.getByText("Member role updated.").waitFor();
  page.once("dialog", (dialog) => dialog.accept());
  const memberRow = page.locator("li").filter({ hasText: "member@example.test" });
  await memberRow.getByRole("button", { name: "Remove" }).click();
  await page.getByText("Member removed.").waitFor();
  await verifyRemovedMember(browserInstance);

  await page.goto(`${appOrigin}/account/security`);
  await page.getByText("No authenticator factor is enrolled.").waitFor();
  await page.getByRole("button", { name: "Add authenticator" }).click();
  await page.getByRole("heading", { name: "Scan authenticator code" }).waitFor();
  await page.getByLabel("Verification code").fill("123456");
  await page.getByRole("button", { name: "Verify code" }).click();
  await page.getByText("MFA verified. This session now has AAL2 assurance.").waitFor();
  await page.getByText("AAL2", { exact: true }).waitFor();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Remove", exact: true }).click();
  await page.getByText("Authenticator removed.").waitFor();

  assert.equal(await page.evaluate(() => Object.keys(localStorage).join(" ").includes("access-owner")), false, "access tokens must not be stored in localStorage");
  await context.close();
}

async function verifyRemovedMember(browserInstance) {
  const context = await browserInstance.newContext();
  const page = await context.newPage();
  await login(page, "member@example.test");
  await page.goto(`${appOrigin}/organizations/org-browser-1`);
  await page.getByText("No organizations available for this account.").waitFor();
  await context.close();
}

async function runMobileKeyboardSmoke(browserInstance) {
  const context = await browserInstance.newContext({ viewport: { width: 390, height: 844 } });
  activeContext = context;
  await context.tracing.start({ screenshots: true, snapshots: true });
  const page = await context.newPage();
  activePage = page;
  await page.goto(`${appOrigin}/login`);
  await page.getByLabel("Email").focus();
  await page.keyboard.press("Tab");
  assert.equal(await page.getByLabel("Password").evaluate((element) => document.activeElement === element), true, "keyboard focus must move from email to password");
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, "mobile layout must not horizontally overflow");
  await context.close();
}

async function login(page, email) {
  await page.goto(`${appOrigin}/login`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("test-password");
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL(/\/account\/security$/);
  await page.goto(`${appOrigin}/account`);
}

function handleSupabase(method, url, payload, token, response) {
  if (method === "POST" && url.pathname === "/auth/v1/token" && url.searchParams.get("grant_type") === "password") {
    const member = payload.email === "member@example.test";
    return send(response, 200, session(member ? "access-member" : "access-owner"));
  }
  if (method === "POST" && url.pathname === "/auth/v1/token" && url.searchParams.get("grant_type") === "refresh_token") {
    state.refreshCount += 1;
    return send(response, 200, session("access-owner-refreshed"));
  }
  if (method === "POST" && url.pathname === "/auth/v1/token" && url.searchParams.get("grant_type") === "pkce") {
    state.recoveryExchanges += 1;
    return send(response, 200, session("access-recovery"));
  }
  if (method === "GET" && url.pathname === "/auth/v1/user") {
    return send(response, 200, { id: "supabase-owner", email: "owner@example.test", factors: state.mfaFactors });
  }
  if (method === "PUT" && url.pathname === "/auth/v1/user") {
    return send(response, 200, { id: "supabase-owner" });
  }
  if (method === "POST" && url.pathname === "/auth/v1/factors") {
    state.mfaFactors = [factor("unverified")];
    return send(response, 200, {
      id: factorId,
      friendly_name: payload.friendly_name,
      totp: { qr_code: "<svg xmlns='http://www.w3.org/2000/svg'></svg>", secret: "ABCDEFGHIJKLMNOP" }
    });
  }
  if (method === "POST" && url.pathname === `/auth/v1/factors/${factorId}/challenge`) {
    return send(response, 200, { id: "22222222-2222-4222-8222-222222222222" });
  }
  if (method === "POST" && url.pathname === `/auth/v1/factors/${factorId}/verify`) {
    state.mfaFactors = [factor("verified")];
    return send(response, 200, session(jwt("aal2")));
  }
  if (method === "DELETE" && url.pathname === `/auth/v1/factors/${factorId}`) {
    state.mfaFactors = [];
    return send(response, 200, { id: factorId });
  }
  return send(response, 404, { detail: `Unhandled Supabase route ${method} ${url.pathname} ${token}` });
}

function handleBackend(method, url, payload, token, cookie, response) {
  if (token) {
    state.backendTokens.push(token);
  }
  const user = userForToken(token);
  if (method === "GET" && url.pathname === "/api/auth/me") {
    return user ? send(response, 200, user) : send(response, 401, { detail: "Authentication required" });
  }
  if (method === "POST" && url.pathname === "/api/auth/mfa/audit") {
    state.auditActions.push(payload.action);
    return send(response, 200, { status: "recorded" });
  }
  if (method === "POST" && url.pathname === "/api/analyze") {
    const anonymousId = readCookie(cookie, "defi_copilot_anon") || "anon-browser-a";
    const reportId = user ? "owner-report" : "anon-report-a";
    const report = reportPayload(reportId, payload.protocols ?? ["pendle"]);
    state.reports.set(reportId, { report, owner: user?.id ?? null, anonymousId });
    if (!user) {
      state.anonymousReports.set(reportId, anonymousId);
    }
    return send(response, 200, { report_id: reportId }, user ? {} : { "Set-Cookie": "defi_copilot_anon=anon-browser-a; Path=/; HttpOnly; SameSite=Lax" });
  }
  if (method === "GET" && /^\/api\/reports\//.test(url.pathname)) {
    const reportId = url.pathname.split("/").pop();
    const entry = state.reports.get(reportId);
    const anonymousId = readCookie(cookie, "defi_copilot_anon");
    if (!entry || (entry.owner && entry.owner !== user?.id) || (!entry.owner && (entry.anonymousId !== anonymousId || state.expiredAnonymousSessions.has(anonymousId)))) {
      return send(response, 404, { detail: "Report not found" });
    }
    return send(response, 200, entry.report);
  }
  if (!user) {
    return send(response, 401, { detail: "Authentication required" });
  }
  if (method === "GET" && url.pathname === "/api/usage") {
    return send(response, 200, { items: [{ action: "analysis", used: 1, limit: 25, remaining: 24 }] });
  }
  if (method === "GET" && url.pathname === "/api/consents") {
    return send(response, 200, { items: state.consents.filter((item) => item.userId === user.id) });
  }
  if (method === "POST" && url.pathname === "/api/consents") {
    const consent = { document_type: payload.document_type, document_version: "2026-07-20", accepted_at: now, userId: user.id };
    state.consents = [...state.consents.filter((item) => item.userId !== user.id || item.document_type !== consent.document_type), consent];
    return send(response, 200, { consent });
  }
  if (method === "GET" && url.pathname === "/api/account/export") {
    return send(response, 200, { format_version: "phase16.account_export.v1", profile: user, saved_theses: state.theses.filter((item) => item.owner_user_id === user.id), consents: [] });
  }
  if (method === "DELETE" && url.pathname === "/api/account") {
    return send(response, 200, { status: "pending_provider_deletion" });
  }
  if (url.pathname === "/api/theses") {
    if (method === "GET") return send(response, 200, { items: state.theses.filter((item) => item.owner_user_id === user.id) });
    if (method === "POST") {
      const thesis = { id: "thesis-browser-1", owner_user_id: user.id, title: payload.title, strategy_text: payload.strategy_text, protocols: payload.protocols, visibility: "private" };
      state.theses.push(thesis);
      return send(response, 200, thesis);
    }
  }
  if (/^\/api\/theses\//.test(url.pathname)) {
    const thesisId = url.pathname.split("/").pop();
    const thesis = state.theses.find((item) => item.id === thesisId && item.owner_user_id === user.id);
    if (!thesis) return send(response, 404, { detail: "Thesis not found" });
    if (method === "PATCH") {
      Object.assign(thesis, payload);
      return send(response, 200, thesis);
    }
    if (method === "DELETE") {
      state.theses = state.theses.filter((item) => item.id !== thesisId);
      return send(response, 200, thesis);
    }
  }
  if (url.pathname === "/api/organizations") {
    if (method === "GET") {
      return send(response, 200, { items: visibleOrganizations(user) });
    }
    if (method === "POST") {
      state.organization = { id: "org-browser-1", name: payload.name, slug: "research-guild", status: "active" };
      state.memberships = [{ id: "member-owner", email: "owner@example.test", user_id: "owner", role: "owner", status: "active" }];
      return send(response, 200, state.organization);
    }
  }
  if (/^\/api\/organizations\/org-browser-1$/.test(url.pathname)) {
    if (!visibleOrganizations(user).length) return send(response, 404, { detail: "Organization not found" });
    if (method === "PATCH") {
      state.organization.name = payload.name;
      return send(response, 200, state.organization);
    }
  }
  if (/^\/api\/organizations\/org-browser-1\/members$/.test(url.pathname)) {
    if (!visibleOrganizations(user).length) return send(response, 404, { detail: "Organization not found" });
    if (method === "GET") return send(response, 200, { items: state.memberships });
    if (method === "POST") {
      const member = { id: "member-invitee", email: payload.email, user_id: "member", role: payload.role, status: "active" };
      state.memberships = [...state.memberships.filter((item) => item.id !== member.id), member];
      return send(response, 200, member);
    }
  }
  if (/^\/api\/organizations\/org-browser-1\/members\//.test(url.pathname)) {
    const membershipId = url.pathname.split("/").pop();
    const member = state.memberships.find((item) => item.id === membershipId);
    if (!member) return send(response, 404, { detail: "Membership not found" });
    if (method === "PATCH") {
      member.role = payload.role ?? member.role;
      return send(response, 200, member);
    }
    if (method === "DELETE") {
      const ownerCount = state.memberships.filter((item) => item.role === "owner" && item.status === "active").length;
      if (member.role === "owner" && ownerCount <= 1) return send(response, 409, { detail: "Cannot remove the final active organization owner" });
      member.status = "removed";
      return send(response, 200, member);
    }
  }
  if (/^\/api\/organizations\/org-browser-1\/knowledge-sources$/.test(url.pathname)) {
    return send(response, 200, { items: [] });
  }
  return send(response, 404, { detail: `Unhandled backend route ${method} ${url.pathname}` });
}

function visibleOrganizations(user) {
  if (!state.organization) return [];
  return state.memberships.some((member) => member.user_id === user.id && member.status === "active") ? [state.organization] : [];
}

function userForToken(token) {
  if (token.startsWith("access-member")) return { id: "member", email: "member@example.test", role: "common", platform_role: "user", plan: "free", is_active: true, auth_enabled: true, email_verified: true };
  if (token) return { id: "owner", email: "owner@example.test", role: "common", platform_role: "user", plan: "free", is_active: true, auth_enabled: true, email_verified: true };
  return null;
}

function reportPayload(reportId, protocols) {
  return {
    report_id: reportId,
    status: "completed",
    executive_summary: "Deterministic research summary for a hypothetical strategy.",
    strategy_description: "Hypothetical browser E2E strategy.",
    protocols,
    risk_rating: "Moderate",
    assumptions: ["Mocked browser test data is deterministic."],
    missing_data: [],
    sections: [{ title: "Risk Notes", content: "Educational research only; no execution or personalized advice." }],
    sources: [],
    disclaimer: "Educational research only. This is not investment advice."
  };
}

function session(accessToken) {
  return { access_token: accessToken, refresh_token: "refresh-owner", expires_in: 3600, user: { factors: state.mfaFactors } };
}

function jwt(aal) {
  return `header.${Buffer.from(JSON.stringify({ aal })).toString("base64url")}.signature`;
}

function factor(status) {
  return { id: factorId, status, friendly_name: "Authenticator app", factor_type: "totp", created_at: now, updated_at: now, last_challenged_at: null };
}

function send(response, status, payload, headers = {}) {
  response.writeHead(status, { "Content-Type": "application/json", ...headers });
  response.end(JSON.stringify(payload));
}

function readCookie(header, name) {
  return header.split(";").map((value) => value.trim()).find((value) => value.startsWith(`${name}=`))?.slice(name.length + 1) ?? "";
}

function parseJson(value) {
  try { return value ? JSON.parse(value) : {}; } catch { return {}; }
}

async function readBody(request) {
  let body = "";
  for await (const chunk of request) body += chunk;
  return body;
}

async function availablePort() {
  const server = createServer();
  await listen(server, 0);
  const address = server.address();
  assert(address && typeof address === "object");
  await closeServer(server);
  return address.port;
}

function listen(server, port) {
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", resolve);
  });
}

function closeServer(server) {
  return new Promise((resolve) => {
    if (!server.listening) return resolve();
    server.close(resolve);
  });
}

function waitForExit(child) {
  return new Promise((resolve) => {
    if (child.exitCode !== null || child.signalCode !== null) return resolve();
    child.once("exit", resolve);
    setTimeout(() => child.kill("SIGKILL"), 5_000).unref();
  });
}

async function waitForApp(url, child) {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`Next.js exited before startup with code ${child.exitCode}`);
    try {
      if ((await fetch(url)).ok) return;
    } catch {
      // The production server needs a short startup window.
    }
    await sleep(250);
  }
  throw new Error("Timed out waiting for the Next.js browser E2E server.");
}

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}
