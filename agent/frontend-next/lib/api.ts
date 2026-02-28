import type { ChatRequest, ChatResponse, FeedbackRequest } from "./types";

export const AGENT_API_URL =
  process.env.NEXT_PUBLIC_AGENT_API_URL ?? "http://localhost:8400";

// ── Error type ────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

async function throwIfNotOk(res: Response): Promise<void> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // ignore JSON parse errors; keep statusText
    }
    throw new ApiError(res.status, detail);
  }
}

// ── Public API ────────────────────────────────────────────────────────────────

export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${AGENT_API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  await throwIfNotOk(res);
  return res.json() as Promise<ChatResponse>;
}

export async function sendFeedback(request: FeedbackRequest): Promise<void> {
  fetch(`${AGENT_API_URL}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  })
    .then((res) => {
      if (!res.ok) {
        console.error(`[feedback] non-2xx response: ${res.status}`);
      }
    })
    .catch((err) => {
      console.error("[feedback] network error:", err);
    });
}

export async function checkHealth(): Promise<{
  status: string;
  openemr_connected: boolean;
}> {
  try {
    const res = await fetch(`${AGENT_API_URL}/health`);
    if (!res.ok) {
      return { status: "unreachable", openemr_connected: false };
    }
    return res.json();
  } catch {
    return { status: "unreachable", openemr_connected: false };
  }
}
