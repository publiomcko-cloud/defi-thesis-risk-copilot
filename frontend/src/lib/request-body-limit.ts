export type BodyLimitResult =
  | { ok: true; body: ArrayBuffer | undefined }
  | { ok: false; status: 400 | 413; detail: string };

const DEFAULT_API_LIMIT = 1 * 1024 * 1024;
const DEFAULT_KNOWLEDGE_LIMIT = 10 * 1024 * 1024 + 128 * 1024;

export function bffBodyLimit(path: string): number {
  const configured = path.startsWith("/api/knowledge/")
    ? process.env.BFF_KNOWLEDGE_UPLOAD_MAX_BYTES
    : process.env.BFF_MAX_REQUEST_BYTES;
  const fallback = path.startsWith("/api/knowledge/") ? DEFAULT_KNOWLEDGE_LIMIT : DEFAULT_API_LIMIT;
  const parsed = Number(configured ?? fallback);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : fallback;
}

export async function readBodyWithinLimit(request: Request, limit: number): Promise<BodyLimitResult> {
  const declared = request.headers.get("content-length");
  if (declared !== null && (!/^\d+$/.test(declared) || Number(declared) > limit)) {
    return {
      ok: false,
      status: declared !== null && /^\d+$/.test(declared) ? 413 : 400,
      detail: declared !== null && /^\d+$/.test(declared) ? "Request body exceeds the allowed size." : "Invalid Content-Length header."
    };
  }
  if (!request.body) return { ok: true, body: undefined };

  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > limit) {
        await reader.cancel();
        return { ok: false, status: 413, detail: "Request body exceeds the allowed size." };
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const body = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    body.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return { ok: true, body: body.buffer as ArrayBuffer };
}
