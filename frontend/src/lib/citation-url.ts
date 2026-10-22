export function safeCitationHref(value: string | null | undefined): string | null {
  if (!value || value.length > 2048 || value.trim() !== value || value.includes("\\") || /[\u0000-\u001f\u007f]/.test(value)) {
    return null;
  }
  if (/^(docs|knowledge_base)\/[A-Za-z0-9._/-]+\.md$/.test(value)) {
    const parts = value.split("/");
    return parts.some((part) => !part || part === "." || part === "..") ? null : value;
  }
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.username || url.password) return null;
    const host = url.hostname.toLowerCase().replace(/\.$/, "").replace(/^\[|\]$/g, "");
    if (!host || host === "localhost" || host.endsWith(".localhost") || host.endsWith(".local")) return null;
    if (host === "::1" || host === "::" || host.startsWith("fc") || host.startsWith("fd") || host.startsWith("fe80:")) return null;
    const ipv4 = host.split(".").map(Number);
    if (ipv4.length === 4 && ipv4.every((part) => Number.isInteger(part) && part >= 0 && part <= 255)) {
      const [a, b] = ipv4;
      if (a === 0 || a === 10 || a === 127 || (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || a >= 224) return null;
    }
    return url.href;
  } catch {
    return null;
  }
}
