/**
 * API base URL for browser fetches.
 *
 * - Local / single-service Render: leave empty (same-origin; Vite proxies in dev).
 * - Split Static Site + API: set VITE_API_BASE or VITE_API_URL to the API origin.
 */
export const API_BASE = (
  (import.meta.env.VITE_API_BASE as string | undefined) ||
  (import.meta.env.VITE_API_URL as string | undefined) ||
  ""
).replace(/\/$/, "");

/** Join API_BASE with a path like `/chat/...`. */
export function apiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${p}`;
}
