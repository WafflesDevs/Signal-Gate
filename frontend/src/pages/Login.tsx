import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "../auth/AuthContext";
import { AuthCoinRain } from "../components/auth/AuthCoinRain";

export function Login() {
  const { user, loading, signIn, signUp } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);

  if (!loading && user) {
    return <Navigate to="/chat" replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setInfo("");
    setBusy(true);
    try {
      if (mode === "login") {
        await signIn(email.trim(), password);
        navigate("/chat");
      } else {
        const { needsEmailConfirm } = await signUp(email.trim(), password);
        if (needsEmailConfirm) {
          setInfo(
            "Check your inbox — we sent a Signal Gate verification email. Confirm, then log in."
          );
          setMode("login");
        } else {
          navigate("/chat");
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page auth-page">
      <AuthCoinRain />
      <motion.div
        className="auth-card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
      >
        <img src="/signal-s.png" alt="" className="auth-card__logo" />
        <h1 className="brand-name auth-card__title">Signal Gate</h1>
        <p className="auth-card__sub">
          {mode === "login" ? "Welcome back to the desk." : "Create your account to start chatting."}
        </p>

        <form className="auth-form" onSubmit={onSubmit}>
          <label>
            Email
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@email.com"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </label>

          {error && <p className="auth-form__error">{error}</p>}
          {info && <p className="auth-form__info">{info}</p>}

          <button type="submit" className="btn btn--primary auth-form__submit" disabled={busy}>
            {busy ? "Please wait…" : mode === "login" ? "Log in" : "Sign up"}
          </button>
        </form>

        <p className="auth-card__switch">
          {mode === "login" ? (
            <>
              New here?{" "}
              <button type="button" onClick={() => setMode("signup")}>
                Create account
              </button>
            </>
          ) : (
            <>
              Already verified?{" "}
              <button type="button" onClick={() => setMode("login")}>
                Log in
              </button>
            </>
          )}
        </p>

        <Link to="/" className="auth-card__back">
          ← Back home
        </Link>
      </motion.div>
    </div>
  );
}
