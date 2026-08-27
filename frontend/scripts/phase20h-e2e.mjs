import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { chromium } from "playwright";

const expiresAt = "2026-09-30T12:00:00.000Z";
const users = {
  owner: { id: "user-owner", email: "owner@example.test" },
  admin: { id: "user-admin", email: "admin@example.test" },
  member: { id: "user-member", email: "member@example.test" },
  viewer: { id: "user-viewer", email: "viewer@example.test" },
  invitee: { id: "user-invitee", email: "invitee@example.test" }
};
const state = {
  organization: { id: "org-ui-1", name: "Portfolio Research", slug: "portfolio-research", status: "active" },
  memberships: [
    { id: "membership-owner", organization_id: "org-ui-1", user_id: users.owner.id, email: users.owner.email, role: "owner", status: "active" },
    { id: "membership-admin", organization_id: "org-ui-1", user_id: users.admin.id, email: users.admin.email, role: "admin", status: "active" },
    { id: "membership-member", organization_id: "org-ui-1", user_id: users.member.id, email: users.member.email, role: "member", status: "active" },
    { id: "membership-viewer", organization_id: "org-ui-1", user_id: users.viewer.id, email: users.viewer.email, role: "viewer", status: "active" }
  ],
  invitations: [],
  calls: [],
  transferAttempts: 0,
  invitationSequence: 0
};

const upstream = createServer(async (request, response) => {
  const body = await readBody(request);
  const url = new URL(request.url ?? "/", "http://localhost");
  const method = request.method ?? "GET";
  const payload = parseJson(body);
  const token = (request.headers.authorization ?? "").replace(/^Bearer\s+/i, "");
  if (url.pathname.startsWith("/auth/v1/")) return handleSupabase(method, url, payload, response);
  return handleBackend(method, url, payload, token, response);
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
    ADMIN_MFA_REQUIRED: "false",
    BACKEND_API_BASE_URL: upstreamOrigin,
    COOKIE_SECURE: "false",
    SESSION_COOKIE_NAME: "phase20h_browser_session",
    SUPABASE_ANON_KEY: "phase20h-browser-key",
    SUPABASE_URL: upstreamOrigin
  },
  stdio: ["ignore", "pipe", "pipe"]
});
let appOutput = "";
app.stdout.on("data", (chunk) => { appOutput += chunk; });
app.stderr.on("data", (chunk) => { appOutput += chunk; });

let browser;
let activePage;
try {
  await waitForApp(`${appOrigin}/login`, app);
  browser = await chromium.launch({ headless: true });
  await exerciseViewerWorkflow(browser);
  await exerciseOwnerWorkflow(browser);
  await exerciseInvitationAcceptance(browser);
  await exerciseAdminWorkflow(browser);

  assert(state.calls.every((call) => !call.url.includes("token=")), "invitation tokens must never reach the backend in a URL");
  assert(state.calls.filter((call) => call.path.endsWith("/invitations") && call.method === "GET").every((call) => !JSON.stringify(call.response).includes("token")), "listed invitations must never include a token");
  assert(state.calls.filter((call) => call.path === "/api/organization-invitations/accept").every((call) => Object.keys(call.body).length === 1 && typeof call.body.token === "string"), "acceptance must send a token only in its request body");
  assert(state.calls.filter((call) => call.path.endsWith("/transfer-ownership")).every((call) => Object.keys(call.body).length === 1 && typeof call.body.target_membership_id === "string"), "ownership transfer must use only the dedicated target-membership request body");
  assert(state.calls.every((call) => !/(token_hash|jwt|auth_time|billing|payment|subscription|price)/i.test(JSON.stringify(call.response))), "browser API responses must not expose sensitive or billing fields");
  console.log("Phase 20H browser E2E passed: seat projection, invitations, one-time token handling, acceptance, lifecycle controls, transfer, and export.");
} catch (error) {
  if (activePage) await activePage.screenshot({ path: "test-results/phase20h-e2e-failure.png", fullPage: true }).catch(() => {});
  if (appOutput) console.error(appOutput);
  throw error;
} finally {
  await browser?.close();
  app.kill("SIGTERM");
  await Promise.allSettled([waitForExit(app), closeServer(upstream)]);
}

async function exerciseViewerWorkflow(browserInstance) {
  const context = await browserInstance.newContext();
  const page = await context.newPage();
  activePage = page;
  await login(page, users.viewer.email);
  await page.goto(`${appOrigin}/organizations/${state.organization.id}`);
  await page.getByText("Current role: viewer").waitFor();
  assert.equal(await page.getByRole("heading", { name: "Invite member" }).count(), 0, "a viewer must not receive invitation controls");
  assert.equal(await page.getByRole("heading", { name: "Ownership transfer" }).count(), 0, "a viewer must not receive ownership-transfer authority");
  assert.equal(await page.getByRole("heading", { name: "Organization lifecycle" }).count(), 0, "a viewer must not receive lifecycle authority");
  await context.close();
}

async function exerciseOwnerWorkflow(browserInstance) {
  const context = await browserInstance.newContext({ acceptDownloads: true });
  const page = await context.newPage();
  activePage = page;
  await login(page, users.owner.email);
  await page.goto(`${appOrigin}/organizations`);
  await page.getByRole("heading", { name: "Portfolio Research" }).waitFor();
  await page.getByText("4 / 5 seats", { exact: true }).waitFor();
  await page.getByText("Active", { exact: true }).waitFor();
  await page.getByText("Reserved", { exact: true }).waitFor();
  assert.deepEqual(await page.getByLabel("Invitation role").locator("option").allTextContents(), ["admin", "member", "viewer"], "owner must not be an invitation role option");
  assert.deepEqual(await page.getByLabel(`Role for ${users.member.email}`).locator("option").allTextContents(), ["admin", "member", "viewer"], "ordinary role editing must not offer owner");

  await page.getByLabel("Destination email").fill(users.invitee.email);
  await page.getByLabel("Invitation role").selectOption("member");
  await page.getByRole("button", { name: "Create invitation" }).click();
  await page.getByRole("heading", { name: "One-time invitation link" }).waitFor();
  const firstLink = await page.getByLabel(`Invitation link for ${users.invitee.email}`).inputValue();
  const firstInvitationUrl = new URL(firstLink);
  assert.equal(firstInvitationUrl.search, "", "invitation links must not put tokens in query parameters");
  assert(firstInvitationUrl.hash.startsWith("#token="), "the one-time link must contain the token in a client-only fragment");
  await page.getByRole("button", { name: "Copy invitation link" }).click();
  await page.getByText(/Invitation link copied\.|Copy is unavailable in this browser/).waitFor();
  await page.getByText("5 / 5 seats", { exact: true }).waitFor();
  assert.equal(await page.evaluate(() => Object.keys(localStorage).length + Object.keys(sessionStorage).length), 0, "invitation tokens must not be stored in browser storage");
  assert.equal(/pricing|billing|checkout|subscription/i.test(await page.locator("body").innerText()), false, "organization UI must remain non-billable and operational");

  await page.getByLabel("Destination email").fill("overflow@example.test");
  await page.getByRole("button", { name: "Create invitation" }).click();
  await page.getByRole("alert").filter({ hasText: "All organization seats are currently consumed" }).waitFor();

  const inviteeRow = page.locator("tr").filter({ hasText: users.invitee.email });
  await inviteeRow.getByRole("button", { name: "Resend" }).click();
  await page.waitForFunction(
    (previousValue) => document.getElementById("one-time-invitation-link")?.value !== previousValue,
    firstLink
  );
  const replacementLink = await page.getByLabel(`Invitation link for ${users.invitee.email}`).inputValue();
  assert.notEqual(replacementLink, firstLink, "resend must replace the one-time link");
  await inviteeRow.getByRole("button", { name: "Revoke" }).click();
  await page.getByText("4 / 5 seats", { exact: true }).waitFor();
  await page.reload();
  assert.equal(await page.getByRole("heading", { name: "One-time invitation link" }).count(), 0, "a one-time link must disappear after refresh");

  await page.getByLabel("Destination email").fill(users.invitee.email);
  await page.getByRole("button", { name: "Create invitation" }).click();
  const invitationLink = await page.getByLabel(`Invitation link for ${users.invitee.email}`).inputValue();
  state.inviteeLink = invitationLink;
  assert.equal((await page.getByLabel("Active member").locator("option").allTextContents()).some((option) => option.includes(users.invitee.email)), false, "pending invitations must never be ownership-transfer targets");

  await page.getByRole("button", { name: "Disable organization" }).click();
  await page.getByRole("button", { name: "Reactivate organization" }).waitFor();
  assert.equal(await page.getByRole("heading", { name: "Invite member" }).count(), 0, "disabled organizations must hide ordinary invitation management");
  assert.equal(await page.getByRole("heading", { name: "Ownership transfer" }).count(), 0, "disabled organizations must hide ownership transfer");
  await page.getByRole("button", { name: "Reactivate organization" }).click();
  await page.getByRole("button", { name: "Disable organization" }).waitFor();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export organization data" }).click();
  const download = await downloadPromise;
  const exportFile = await download.path();
  assert(exportFile, "organization export must create a download");
  const exported = JSON.parse(await readFile(exportFile, "utf8"));
  const serialized = JSON.stringify(exported);
  assert.equal(/token|token_hash|authorization|secret|billing|price|subscription/i.test(serialized), false, "organization export must contain only the allowlisted organization data");

  await page.getByLabel("Active member").selectOption("membership-member");
  await page.getByRole("button", { name: "Transfer ownership" }).click();
  await page.getByRole("dialog", { name: "Transfer ownership" }).getByRole("button", { name: "Confirm transfer" }).click();
  await page.getByRole("alert").filter({ hasText: "Reauthenticate to transfer ownership" }).waitFor();
  await page.getByRole("link", { name: "Log in again" }).waitFor();

  await page.getByRole("button", { name: "Transfer ownership" }).click();
  await page.getByRole("dialog", { name: "Transfer ownership" }).getByRole("button", { name: "Confirm transfer" }).click();
  await page.getByText(`${users.member.email} is now the organization owner.`).waitFor();
  assert.equal(await page.getByRole("heading", { name: "Organization lifecycle" }).count(), 0, "a former owner must lose lifecycle controls after transfer");
  await page.getByRole("heading", { name: "Organization export" }).waitFor();
  await context.close();
}

async function exerciseInvitationAcceptance(browserInstance) {
  const invitationLink = state.inviteeLink;
  assert(invitationLink, "owner workflow must create an invitation for acceptance");
  const anonymousContext = await browserInstance.newContext();
  const anonymousPage = await anonymousContext.newPage();
  activePage = anonymousPage;
  await openInvitationLink(anonymousPage, invitationLink);
  await anonymousPage.waitForFunction(() => document.getElementById("organization-invitation-token")?.value.length > 0);
  await anonymousPage.getByRole("button", { name: "Accept invitation" }).click();
  await anonymousPage.getByRole("heading", { name: "Authentication required" }).waitFor();
  await anonymousContext.close();

  const context = await browserInstance.newContext();
  const page = await context.newPage();
  activePage = page;
  await login(page, users.viewer.email);
  await openInvitationLink(page, invitationLink);
  await page.waitForFunction(() => document.getElementById("organization-invitation-token")?.value.length > 0);
  await page.getByRole("button", { name: "Accept invitation" }).click();
  await page.getByRole("alert").filter({ hasText: "different authenticated email" }).waitFor();
  assert.equal(await page.evaluate(() => `${location.search}|${Object.keys(localStorage).join(" ")}|${Object.keys(sessionStorage).join(" ")}`.includes("ui-")), false, "the acceptance route must remove tokens from the address and browser storage");
  await context.close();

  const invitedContext = await browserInstance.newContext();
  const invitedPage = await invitedContext.newPage();
  activePage = invitedPage;
  await login(invitedPage, users.invitee.email);
  await openInvitationLink(invitedPage, invitationLink);
  await invitedPage.waitForFunction(() => document.getElementById("organization-invitation-token")?.value.length > 0);
  await invitedPage.getByRole("button", { name: "Accept invitation" }).click();
  await invitedPage.getByRole("heading", { name: "Invitation accepted" }).waitFor();
  await invitedPage.getByRole("link", { name: "Open organization" }).click();
  await invitedPage.waitForURL(new RegExp(`/organizations/${state.organization.id}$`));
  await invitedPage.getByText(users.invitee.email).waitFor();
  assert.equal(await invitedPage.getByRole("heading", { name: "Ownership transfer" }).count(), 0, "a member must not receive ownership-transfer authority");
  await invitedContext.close();

  const ownerContext = await browserInstance.newContext();
  const ownerPage = await ownerContext.newPage();
  activePage = ownerPage;
  await login(ownerPage, users.member.email);
  await ownerPage.goto(`${appOrigin}/organizations/${state.organization.id}`);
  const viewerRow = ownerPage.locator("tr").filter({ hasText: users.viewer.email });
  await viewerRow.getByRole("button", { name: "Remove" }).click();
  await ownerPage.getByText("4 / 5 seats", { exact: true }).waitFor();
  await ownerContext.close();
}

async function exerciseAdminWorkflow(browserInstance) {
  const context = await browserInstance.newContext({ acceptDownloads: true });
  const page = await context.newPage();
  activePage = page;
  await login(page, users.admin.email);
  await page.goto(`${appOrigin}/organizations/${state.organization.id}`);
  await page.getByRole("heading", { name: "Invite member" }).waitFor();
  assert.equal(await page.getByRole("heading", { name: "Organization lifecycle" }).count(), 0, "an administrator must not receive lifecycle authority");
  assert.equal(await page.getByRole("heading", { name: "Ownership transfer" }).count(), 0, "an administrator must not receive ownership-transfer authority");

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export organization data" }).click();
  await downloadPromise;
  await page.getByLabel("Destination email").fill("admin-invite@example.test");
  await page.getByRole("button", { name: "Create invitation" }).click();
  await page.getByRole("heading", { name: "One-time invitation link" }).waitFor();
  await context.close();
}

async function login(page, email) {
  await page.goto(`${appOrigin}/login`);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("browser-test-password");
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL(/\/account$/);
}

async function openInvitationLink(page, invitationLink) {
  let navigationUrl = "";
  const captureNavigation = (request) => {
    if (request.isNavigationRequest() && new URL(request.url()).pathname === "/organization-invitations/accept") {
      navigationUrl = request.url();
    }
  };
  page.on("request", captureNavigation);
  await page.goto(invitationLink);
  await page.waitForURL(`${appOrigin}/organization-invitations/accept`);
  page.off("request", captureNavigation);
  assert.equal(navigationUrl, `${appOrigin}/organization-invitations/accept`, "the acceptance navigation must not transmit a token to the server");
  assert.deepEqual(await page.evaluate(() => ({ hash: location.hash, search: location.search })), { hash: "", search: "" }, "the acceptance page must immediately clear its fragment and query state");
}

function handleSupabase(method, url, payload, response) {
  if (method === "POST" && url.pathname === "/auth/v1/token" && url.searchParams.get("grant_type") === "password") {
    const actor = Object.values(users).find((candidate) => candidate.email === payload.email);
    return actor ? send(response, 200, session(actor)) : send(response, 400, { detail: "Login failed" });
  }
  return send(response, 404, { detail: `Unhandled Supabase route ${method} ${url.pathname}` });
}

function handleBackend(method, url, payload, token, response) {
  const actor = actorForToken(token);
  if (method === "GET" && url.pathname === "/api/auth/me") return actor ? send(response, 200, userPayload(actor)) : send(response, 401, { detail: "Authentication required" });
  if (!actor) return send(response, 401, { detail: "Authentication required" });
  const call = { method, path: url.pathname, url: url.href, body: payload, response: null };
  state.calls.push(call);
  const finish = (status, body) => {
    call.response = body;
    return send(response, status, body);
  };
  if (url.pathname === "/api/organizations") {
    if (method === "GET") return finish(200, { items: hasActiveMembership(actor.id) ? [state.organization] : [] });
  }
  if (url.pathname === "/api/organization-invitations/accept" && method === "POST") {
    const invitation = state.invitations.find((item) => item.status === "pending" && item.token === payload.token);
    if (!invitation) return finish(409, { detail: "Invitation is invalid" });
    if (invitation.destination_email !== actor.email) return finish(403, { detail: "Invitation destination email does not match authenticated user" });
    invitation.status = "accepted";
    state.memberships.push({ id: `membership-${actor.id}`, organization_id: state.organization.id, user_id: actor.id, email: actor.email, role: invitation.role, status: "active" });
    return finish(200, state.memberships.at(-1));
  }
  if (!hasActiveMembership(actor.id)) return finish(404, { detail: "Organization not found" });
  if (url.pathname === `/api/organizations/${state.organization.id}`) {
    if (method === "GET") return finish(200, state.organization);
    if (method === "PATCH") {
      if (payload.status && !isOwner(actor.id)) return finish(403, { detail: "Organization owner role required" });
      if (payload.status) state.organization.status = payload.status;
      if (payload.name && isManager(actor.id) && state.organization.status === "active") state.organization.name = payload.name;
      return finish(200, state.organization);
    }
  }
  if (url.pathname === `/api/organizations/${state.organization.id}/members` && method === "GET") return finish(200, { items: state.memberships });
  const membershipAction = url.pathname.match(new RegExp(`^/api/organizations/${state.organization.id}/members/([^/]+)$`));
  if (membershipAction && method === "DELETE") {
    if (!isManager(actor.id) || state.organization.status !== "active") return finish(403, { detail: "Organization owner/admin role required" });
    const membership = state.memberships.find((item) => item.id === membershipAction[1]);
    if (!membership || membership.role === "owner") return finish(409, { detail: "Membership cannot be removed" });
    membership.status = "removed";
    return finish(200, membership);
  }
  if (url.pathname === `/api/organizations/${state.organization.id}/seat-status` && method === "GET") {
    if (state.organization.status !== "active" && !isOwner(actor.id)) return finish(404, { detail: "Organization not found" });
    return finish(200, seatProjection());
  }
  if (url.pathname === `/api/organizations/${state.organization.id}/knowledge-sources` && method === "GET") return finish(200, { items: [] });
  if (url.pathname === `/api/organizations/${state.organization.id}/invitations`) {
    if (!isManager(actor.id) || state.organization.status !== "active") return finish(403, { detail: "Organization admin role required" });
    if (method === "GET") return finish(200, { items: publicInvitations() });
    if (method === "POST") {
      if (seatProjection().remaining <= 0) return finish(409, { detail: "Organization seat limit reached" });
      const invitation = createInvitation(payload.email, payload.role);
      return finish(200, publicInvitation(invitation, true));
    }
  }
  const invitationAction = url.pathname.match(new RegExp(`^/api/organizations/${state.organization.id}/invitations/([^/]+)/(resend|revoke)$`));
  if (invitationAction && method === "POST") {
    if (!isManager(actor.id) || state.organization.status !== "active") return finish(403, { detail: "Organization admin role required" });
    const invitation = state.invitations.find((item) => item.id === invitationAction[1]);
    if (!invitation || invitation.status !== "pending") return finish(404, { detail: "Invitation not found" });
    if (invitationAction[2] === "resend") {
      invitation.token = `ui-invitation-${++state.invitationSequence}`;
      return finish(200, publicInvitation(invitation, true));
    }
    invitation.status = "revoked";
    return finish(200, publicInvitation(invitation));
  }
  if (url.pathname === `/api/organizations/${state.organization.id}/transfer-ownership` && method === "POST") {
    if (!isOwner(actor.id) || state.organization.status !== "active") return finish(403, { detail: "Organization owner role required" });
    state.transferAttempts += 1;
    if (state.transferAttempts === 1) return finish(403, { detail: "Recent authentication required" });
    const target = state.memberships.find((item) => item.id === payload.target_membership_id && item.status === "active");
    if (!target) return finish(404, { detail: "Membership not found" });
    state.memberships.find((item) => item.user_id === actor.id).role = "admin";
    target.role = "owner";
    return finish(200, target);
  }
  if (url.pathname === `/api/organizations/${state.organization.id}/export` && method === "GET") {
    if (!(isManager(actor.id) && state.organization.status === "active") && !(isOwner(actor.id) && state.organization.status === "disabled")) return finish(403, { detail: "Organization admin role required" });
    return finish(200, { format_version: "phase20h.organization_export.v1", organization: state.organization, memberships: state.memberships.map(publicMembership), invitations: publicInvitations(), seat_status: seatProjection() });
  }
  return finish(404, { detail: `Unhandled backend route ${method} ${url.pathname}` });
}

function createInvitation(email, role) {
  state.invitationSequence += 1;
  const invitation = { id: `invitation-ui-${state.invitationSequence}`, organization_id: state.organization.id, destination_email: email, role, status: "pending", expires_at: expiresAt, token: `ui-invitation-${state.invitationSequence}` };
  state.invitations.push(invitation);
  return invitation;
}

function seatProjection() {
  const active = state.memberships.filter((membership) => membership.status === "active").length;
  const reserved = state.invitations.filter((invitation) => invitation.status === "pending").length;
  const consumed = active + reserved;
  return { limit: 5, active, reserved, consumed, remaining: Math.max(0, 5 - consumed) };
}

function publicInvitations() { return state.invitations.map((invitation) => publicInvitation(invitation)); }
function publicInvitation(invitation, withToken = false) {
  const { token: _token, ...publicData } = invitation;
  return withToken ? { ...publicData, token: invitation.token } : publicData;
}
function publicMembership(membership) { return { id: membership.id, organization_id: membership.organization_id, user_id: membership.user_id, email: membership.email, role: membership.role, status: membership.status }; }
function hasActiveMembership(userId) { return state.memberships.some((membership) => membership.user_id === userId && membership.status === "active"); }
function isOwner(userId) { return state.memberships.some((membership) => membership.user_id === userId && membership.status === "active" && membership.role === "owner"); }
function isManager(userId) { return state.memberships.some((membership) => membership.user_id === userId && membership.status === "active" && ["owner", "admin"].includes(membership.role)); }
function actorForToken(token) { return Object.values(users).find((user) => token === `access-${user.id}`) ?? null; }
function userPayload(actor) { return { ...actor, role: "common", platform_role: "user", plan: "free", is_active: true, auth_enabled: true, email_verified: true }; }
function session(actor) { return { access_token: `access-${actor.id}`, refresh_token: `refresh-${actor.id}`, expires_in: 3600, user: { factors: [] } }; }
function send(response, status, payload) { response.writeHead(status, { "Content-Type": "application/json" }); response.end(JSON.stringify(payload)); }
function parseJson(value) { try { return value ? JSON.parse(value) : {}; } catch { return {}; } }
async function readBody(request) { let body = ""; for await (const chunk of request) body += chunk; return body; }
async function availablePort() { const server = createServer(); await listen(server, 0); const address = server.address(); assert(address && typeof address === "object"); await closeServer(server); return address.port; }
function listen(server, port) { return new Promise((resolve, reject) => { server.once("error", reject); server.listen(port, "127.0.0.1", resolve); }); }
function closeServer(server) { return new Promise((resolve) => { if (!server.listening) return resolve(); server.close(resolve); }); }
function waitForExit(child) { return new Promise((resolve) => { if (child.exitCode !== null || child.signalCode !== null) return resolve(); child.once("exit", resolve); setTimeout(() => child.kill("SIGKILL"), 5000).unref(); }); }
async function waitForApp(url, child) { const deadline = Date.now() + 30000; while (Date.now() < deadline) { if (child.exitCode !== null) throw new Error(`Next.js exited before startup with code ${child.exitCode}`); try { if ((await fetch(url)).ok) return; } catch {} await new Promise((resolve) => setTimeout(resolve, 250)); } throw new Error("Timed out waiting for the Next.js browser test server."); }
