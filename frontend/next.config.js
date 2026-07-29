/** @type {import('next').NextConfig} */
const cspMode = process.env.SECURITY_CSP_MODE ?? "report_only";
const cspReportUri = process.env.SECURITY_CSP_REPORT_URI ?? "";
const contentSecurityPolicy = [
  "default-src 'self'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "object-src 'none'",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  "style-src 'self' 'unsafe-inline'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
  "connect-src 'self' https:",
  "upgrade-insecure-requests",
  cspReportUri ? `report-uri ${cspReportUri}` : ""
].filter(Boolean).join("; ");

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=(), payment=(), usb=()" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" }
];
if (cspMode === "enforce") {
  securityHeaders.push({ key: "Content-Security-Policy", value: contentSecurityPolicy });
} else if (cspMode === "report_only") {
  securityHeaders.push({ key: "Content-Security-Policy-Report-Only", value: contentSecurityPolicy });
}
if (process.env.SECURITY_HSTS_ENABLED === "true") {
  securityHeaders.push({ key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" });
}

const nextConfig = {
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  }
};

module.exports = nextConfig;
