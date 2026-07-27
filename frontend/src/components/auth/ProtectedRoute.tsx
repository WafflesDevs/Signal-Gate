import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";

/** Relative in-app paths only — blocks open redirects. */
export function safeReturnPath(path: string | null | undefined, fallback = "/chat") {
  if (!path || !path.startsWith("/") || path.startsWith("//")) return fallback;
  return path;
}

/**
 * Router-level auth gate. Redirects to /login?next=… so Login can send
 * the user back to Chart, Chat, Settings, etc. after sign-in.
 */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="page page--center" style={{ padding: "4rem 1.5rem", textAlign: "center" }}>
        <p className="chat-boot">Checking session…</p>
      </div>
    );
  }

  if (!user) {
    const next = encodeURIComponent(`${location.pathname}${location.search}`);
    return <Navigate to={`/login?next=${next}`} replace />;
  }

  return <>{children}</>;
}
