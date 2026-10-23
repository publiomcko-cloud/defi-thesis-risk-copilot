const internalMarkdown = /^(docs|knowledge_base)\/[A-Za-z0-9._/-]+\.md$/;
const hostLabel = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$/;
const numericTld = /^(?:[0-9]+|0x[0-9a-f]*)$/i;
const pathChars = /^[A-Za-z0-9\-._~!$&'()*+,;=:@/%]*$/;
const queryFragmentChars = /^[A-Za-z0-9\-._~!$&'()*+,;=:@/?%]*$/;
const percentEscape = /%[0-9a-f]{2}/i;

/** Canonical display-only citation policy shared with backend fixtures. */
export function safeCitationHref(value: string | null | undefined): string | null {
  if (!value || value.length > 2048 || value.trim() !== value || /[^\x21-\x7e]/.test(value) || value.includes("\\")) {
    return null;
  }
  if (internalMarkdown.test(value)) {
    const parts = value.split("/");
    return parts.some((part) => !part || part === "." || part === "..") ? null : value;
  }
  if (!/^https:\/\//i.test(value)) return null;
  const [beforeFragment, fragmentValue] = value.split("#", 2);
  if (value.includes("#") && !fragmentValue) return null;
  const [, queryValue] = beforeFragment.split("?", 2);
  if (beforeFragment.includes("?") && !queryValue) return null;

  const match = value.match(/^https:\/\/([^/?#]*)([^?#]*)(?:\?([^#]*))?(?:#(.*))?$/i);
  if (!match) return null;
  const [, authority, rawPath, query = "", fragment = ""] = match;
  if (!authority || authority.includes("@") || authority.includes("%") || /[\[\]]/.test(authority)) return null;
  if ((authority.match(/:/g) ?? []).length > 1) return null;

  let host = authority;
  let portText: string | undefined;
  const colon = authority.lastIndexOf(":");
  if (colon >= 0) {
    host = authority.slice(0, colon);
    portText = authority.slice(colon + 1);
    if (!/^[0-9]+$/.test(portText)) return null;
    const port = Number(portText);
    if (!Number.isInteger(port) || port < 1 || port > 65535) return null;
  }

  host = host.toLowerCase();
  if (!host || host.endsWith(".") || host.length > 253) return null;
  const labels = host.split(".");
  if (labels.length < 2 || !/^[a-z]+$/.test(labels[labels.length - 1] ?? "")) return null;
  if (labels.some((label) => !hostLabel.test(label) || label.startsWith("xn--"))) return null;
  if (host === "localhost" || host.endsWith(".localhost") || host.endsWith(".local") || host.endsWith(".internal")) return null;
  // Reject WHATWG IPv4 candidates, including shortened, octal, hexadecimal,
  // and integer spellings. All IP literals are outside the shared policy.
  if (numericTld.test(labels[labels.length - 1] ?? "")) return null;

  const path = rawPath || "/";
  if (!pathChars.test(path) || !queryFragmentChars.test(query) || !queryFragmentChars.test(fragment)) return null;
  if (![path, query, fragment].every(validPercentEscapes) || hasAmbiguousPathSegments(path)) return null;

  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.username || url.password || url.hostname.toLowerCase() !== host) return null;
    return url.href;
  } catch {
    return null;
  }
}

function validPercentEscapes(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    if (value[index] !== "%") continue;
    const escape = value.slice(index, index + 3);
    if (!percentEscape.test(escape)) return false;
    const byte = Number.parseInt(escape.slice(1), 16);
    if (byte < 0x20 || byte === 0x7f) return false;
    index += 2;
  }
  return true;
}

function hasAmbiguousPathSegments(path: string): boolean {
  try {
    return path.split("/").some((segment) => {
      const decoded = decodeURIComponent(segment);
      return decoded === "." || decoded === ".." || decoded.includes("/") || decoded.includes("\\") || decoded.includes("%");
    });
  } catch {
    return true;
  }
}
