import { useAuth } from "../auth/AuthContext";
import { useMemo } from "react";

export async function apiFetch(path: string, token: string | null, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(path, { ...init, headers });
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }
  if (res.status === 204) return null;
  return res.json();
}

/** One SSE event from POST /chat/.../messages/stream */
export type ChatStreamEvent =
  | { type: "token"; text: string }
  | {
      type: "final";
      reply: string;
      pending_trades: Array<{ name: string; arguments: Record<string, unknown> }>;
      message?: {
        id: string;
        role: string;
        content: string;
        metadata?: Record<string, unknown>;
      } | null;
    }
  | { type: "error"; detail: string };

/**
 * POST a chat message and read Server-Sent Events (token / final / error).
 * Calls onEvent for each parsed `data:` line.
 */
export async function streamChatMessage(
  path: string,
  token: string | null,
  body: { message: string },
  onEvent: (event: ChatStreamEvent) => void
): Promise<void> {
  const headers = new Headers({ "Content-Type": "application/json" });
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(path, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      const errBody = await res.json();
      detail = errBody.detail || JSON.stringify(errBody);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }

  if (!res.body) {
    throw new Error("No response body from stream");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";

    for (const chunk of chunks) {
      const line = chunk
        .split("\n")
        .map((l) => l.trim())
        .find((l) => l.startsWith("data:"));
      if (!line) continue;
      const raw = line.replace(/^data:\s*/, "");
      if (!raw || raw === "[DONE]") continue;
      try {
        onEvent(JSON.parse(raw) as ChatStreamEvent);
      } catch {
        /* skip malformed lines */
      }
    }
  }
}

export function useApi() {
  const { accessToken } = useAuth();
  return useMemo(
    () => ({
      get: (path: string) => apiFetch(path, accessToken),
      post: (path: string, body?: unknown) =>
        apiFetch(path, accessToken, {
          method: "POST",
          body: body !== undefined ? JSON.stringify(body) : undefined,
        }),
      del: (path: string) => apiFetch(path, accessToken, { method: "DELETE" }),
      /** Stream a chat turn (SSE). Needs the raw token for Authorization. */
      streamChat: (
        path: string,
        body: { message: string },
        onEvent: (event: ChatStreamEvent) => void
      ) => streamChatMessage(path, accessToken, body, onEvent),
    }),
    [accessToken]
  );
}
