const baseUrl = process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000";

const paths = [
  "/login",
  "/signup",
  "/verify-email",
  "/forgot-password",
  "/reset-password",
  "/account",
  "/account/security",
  "/terms",
  "/privacy",
  "/theses",
  "/organizations",
];

for (const path of paths) {
  const response = await fetch(`${baseUrl}${path}`);
  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}`);
  }
  const html = await response.text();
  if (!html.includes("DeFi Thesis")) {
    throw new Error(`${path} did not render the application shell`);
  }
}

console.log(`E2E smoke passed for ${paths.length} Phase 16 pages.`);
