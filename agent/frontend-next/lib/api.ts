import type { ChatRequest, ChatResponse, FeedbackRequest } from "./types";

export const AGENT_API_URL =
  process.env.NEXT_PUBLIC_AGENT_API_URL ?? "http://localhost:8400";

// ── Error types ───────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class TimeoutError extends Error {
  constructor(message = "Request timed out") {
    super(message);
    this.name = "TimeoutError";
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
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 60_000);

  try {
    const res = await fetch(`${AGENT_API_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal: controller.signal,
    });
    await throwIfNotOk(res);
    return (await res.json()) as ChatResponse;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new TimeoutError();
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

export async function sendFeedback(request: FeedbackRequest): Promise<void> {
  try {
    const res = await fetch(`${AGENT_API_URL}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!res.ok) {
      throw new ApiError(res.status, `non-2xx response: ${res.status}`);
    }
  } catch {
    throw new Error("Failed to submit feedback");
  }
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
