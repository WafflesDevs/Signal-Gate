/**
 * Settings — link Alpaca Paper or Live credentials.
 * Secrets are encrypted server-side; UI never shows the full secret after save.
 */
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "../auth/AuthContext";
import { RiskDisclaimer } from "../components/layout/RiskDisclaimer";
import { useApi } from "../lib/api";

export type AlpacaStatus = {
  linked: boolean;
  is_paper?: boolean | null;
  api_key_masked?: string | null;
  updated_at?: string | null;
};

const GUIDE_STEPS = [
  {
    title: "Create or log in to Alpaca",
    body: "Open alpaca.markets and create an account (or sign in). Open the Paper or Live dashboard next.",
    img: "/guide/alpaca-login.png",
    alt: "Step 1: Alpaca create or log in screen",
  },
  {
    title: "Find API Keys on the dashboard",
    body: "On the Paper (or Live) dashboard, look at the right sidebar for the API Keys panel under the order ticket. Paper keys only work in Paper mode; Live keys only work in Live.",
    img: "/guide/alpaca-dashboard.png",
    alt: "Step 2: Alpaca paper dashboard with API Keys panel on the right",
  },
  {
    title: "Copy Key & Secret",
    body: "From the API Keys panel, copy the Key and Secret. The secret is shown once — save it before you refresh or navigate away.",
    img: "/guide/alpaca-api-keys.png",
    alt: "Step 3: Alpaca API Keys panel (Key and Secret redacted in this guide)",
  },
  {
    title: "Paste into Signal Gate",
    body: "Paste both values below. Toggle Paper or Live to match the dashboard you used.",
    img: "/guide/alpaca-step-4.svg",
    alt: "Step 4: Paste keys into Settings",
  },
  {
    title: "Save & test",
    body: "We verify with Alpaca before saving. Once linked, Chat unlocks for trading.",
    img: "/guide/alpaca-step-5.svg",
    alt: "Step 5: Connected successfully",
  },
] as const;

export function Settings() {
  const { user, loading } = useAuth();
  const api = useApi();

  const [status, setStatus] = useState<AlpacaStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [apiKeyId, setApiKeyId] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [isPaper, setIsPaper] = useState(true);
  const [busy, setBusy] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [guideOpen, setGuideOpen] = useState(true);

  const refresh = useCallback(async () => {
    const s = (await api.get("/settings/alpaca")) as AlpacaStatus;
    setStatus(s);
    if (s.linked && typeof s.is_paper === "boolean") {
      setIsPaper(s.is_paper);
    }
    return s;
  }, [api]);

  useEffect(() => {
    if (!user) return;
    (async () => {
      try {
        setStatusLoading(true);
        setError("");
        await refresh();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load settings");
      } finally {
        setStatusLoading(false);
      }
    })();
  }, [user, refresh]);

  if (loading) {
    return (
      <div className="page settings-page settings-page--center">
        <p className="settings-boot">Loading settings…</p>
      </div>
    );
  }

  async function onSave(e: FormEvent) {
    e.preventDefault();
    setError("");
    setInfo("");
    setBusy(true);
    try {
      const s = (await api.put("/settings/alpaca", {
        api_key_id: apiKeyId.trim(),
        api_secret: apiSecret.trim(),
        is_paper: isPaper,
      })) as AlpacaStatus;
      setStatus(s);
      setApiSecret("");
      setApiKeyId("");
      setInfo(
        `Linked ${s.is_paper ? "Paper" : "Live"} account (${s.api_key_masked}). Chat is unlocked.`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function onTest() {
    setError("");
    setInfo("");
    setTesting(true);
    try {
      const res = (await api.get("/settings/alpaca/test")) as {
        ok?: boolean;
        paper?: boolean;
        equity?: string;
      };
      setInfo(
        `Connection OK · ${res.paper ? "Paper" : "Live"} · equity ${res.equity ?? "—"}`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Test failed");
    } finally {
      setTesting(false);
    }
  }

  async function onDisconnect() {
    if (
      !window.confirm(
        "Disconnect Alpaca? This will permanently delete all of your chats and messages. Chat will lock until you link again."
      )
    ) {
      return;
    }
    setError("");
    setInfo("");
    setBusy(true);
    try {
      const s = (await api.del("/settings/alpaca")) as AlpacaStatus & {
        chats_cleared?: boolean | null;
        chats_deleted?: number | null;
      };
      setStatus(s);
      // Let Chat clear in-memory list if it's still mounted elsewhere
      window.dispatchEvent(new Event("signal-gate:alpaca-disconnected"));
      const n = typeof s.chats_deleted === "number" ? s.chats_deleted : null;
      setInfo(
        n != null
          ? `Alpaca disconnected. Deleted ${n} chat${n === 1 ? "" : "s"}.`
          : "Alpaca disconnected. Your chats were cleared."
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Disconnect failed");
      // Credentials may already be gone — refresh status + clear local chat UI
      try {
        await refresh();
      } catch {
        /* ignore */
      }
      window.dispatchEvent(new Event("signal-gate:alpaca-disconnected"));
    } finally {
      setBusy(false);
    }
  }

  const linked = !!status?.linked;

  return (
    <div className="page settings-page">
      <motion.div
        className="settings-shell"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      >
        <header className="settings-header">
          <p className="settings-kicker">Account</p>
          <h1 className="settings-title">Settings</h1>
          <p className="settings-sub">
            Link your Alpaca API keys so Chat and portfolio tools trade on{" "}
            <em>your</em> paper or live account.
          </p>
          <p className="settings-key-links">
            Get API keys:{" "}
            <a
              href="https://app.alpaca.markets/paper/dashboard/overview"
              target="_blank"
              rel="noreferrer"
            >
              Alpaca Paper
            </a>
            {" · "}
            <a
              href="https://app.alpaca.markets/live/dashboard/overview"
              target="_blank"
              rel="noreferrer"
            >
              Alpaca Live
            </a>
          </p>
        </header>

        <section className="settings-status" aria-live="polite">
          {statusLoading ? (
            <p className="settings-muted">Checking link status…</p>
          ) : linked ? (
            <div className="settings-status__row">
              <span className="settings-badge settings-badge--ok">Linked</span>
              <span
                className={`settings-badge ${
                  status?.is_paper ? "settings-badge--paper" : "settings-badge--live"
                }`}
              >
                {status?.is_paper ? "Paper" : "Live"}
              </span>
              <span className="settings-masked mono">
                Key {status?.api_key_masked}
              </span>
            </div>
          ) : (
            <div className="settings-status__row">
              <span className="settings-badge settings-badge--off">Not linked</span>
              <span className="settings-muted">Chat stays locked until you connect.</span>
            </div>
          )}
        </section>

        {!isPaper && (
          <div className="settings-warn" role="alert">
            <strong>Live trading uses real money.</strong> Orders hit your live Alpaca
            account. Double-check keys and mode before saving.
          </div>
        )}

        <details
          className="settings-guide"
          open={guideOpen}
          onToggle={(e) => setGuideOpen((e.target as HTMLDetailsElement).open)}
        >
          <summary>How to get your Alpaca keys</summary>
          <ol className="settings-guide__list">
            {GUIDE_STEPS.map((step, i) => (
              <li key={step.title} className="settings-guide__step">
                <div className="settings-guide__copy">
                  <h3>
                    <span className="settings-guide__num">{i + 1}</span>
                    {step.title}
                  </h3>
                  <p>{step.body}</p>
                </div>
                <figure className="settings-guide__figure">
                  <img src={step.img} alt={step.alt} loading="lazy" />
                </figure>
              </li>
            ))}
          </ol>
          <p className="settings-guide__note">
            Dashboard screenshots are from Alpaca Paper UI with Key and Secret
            redacted. Open Alpaca → API Keys:{" "}
            <a
              href="https://app.alpaca.markets/paper/dashboard/overview"
              target="_blank"
              rel="noreferrer"
            >
              Paper dashboard
            </a>
            {" · "}
            <a
              href="https://app.alpaca.markets/live/dashboard/overview"
              target="_blank"
              rel="noreferrer"
            >
              Live dashboard
            </a>
            . Docs:{" "}
            <a
              href="https://alpaca.markets/docs/trading/getting-started/"
              target="_blank"
              rel="noreferrer"
            >
              Getting Started
            </a>
            .
          </p>
        </details>

        <form className="settings-form auth-form" onSubmit={onSave}>
          <label>
            API Key ID
            <input
              type="text"
              autoComplete="off"
              spellCheck={false}
              value={apiKeyId}
              onChange={(e) => setApiKeyId(e.target.value)}
              placeholder={linked ? "Enter new key to update" : "PKxxxxxxxx"}
              required={!linked}
            />
          </label>
          <label>
            Secret Key
            <input
              type="password"
              autoComplete="new-password"
              spellCheck={false}
              value={apiSecret}
              onChange={(e) => setApiSecret(e.target.value)}
              placeholder={linked ? "•••••••• (hidden after save)" : "Your secret key"}
              required={!linked || apiKeyId.trim().length > 0}
            />
          </label>

          <fieldset className="settings-mode">
            <legend>Mode</legend>
            <div className="settings-mode__toggle" role="group" aria-label="Paper or Live">
              <button
                type="button"
                className={`settings-mode__btn${isPaper ? " settings-mode__btn--on" : ""}`}
                onClick={() => setIsPaper(true)}
              >
                Paper
              </button>
              <button
                type="button"
                className={`settings-mode__btn settings-mode__btn--live${!isPaper ? " settings-mode__btn--on-live" : ""}`}
                onClick={() => setIsPaper(false)}
              >
                Live
              </button>
            </div>
            <p className="settings-mode__hint">
              Must match the Alpaca dashboard where you generated the keys.{" "}
              <a
                href={
                  isPaper
                    ? "https://app.alpaca.markets/paper/dashboard/overview"
                    : "https://app.alpaca.markets/live/dashboard/overview"
                }
                target="_blank"
                rel="noreferrer"
              >
                Get your API keys from Alpaca →
              </a>
            </p>
          </fieldset>

          {error && <p className="auth-form__error">{error}</p>}
          {info && <p className="auth-form__info">{info}</p>}

          <div className="settings-actions">
            <button
              type="submit"
              className="btn btn--primary"
              disabled={busy || (!apiKeyId.trim() && !apiSecret.trim() && linked)}
            >
              {busy ? "Saving…" : linked ? "Update keys" : "Save & link"}
            </button>
            {linked && (
              <>
                <button
                  type="button"
                  className="btn btn--ghost"
                  disabled={testing || busy}
                  onClick={() => void onTest()}
                >
                  {testing ? "Testing…" : "Test connection"}
                </button>
                <button
                  type="button"
                  className="btn btn--ghost settings-actions__danger"
                  disabled={busy}
                  onClick={() => void onDisconnect()}
                >
                  Disconnect
                </button>
              </>
            )}
          </div>
          <RiskDisclaimer className="settings-form__disclaimer" />
        </form>

        <p className="settings-footer-links">
          {linked ? (
            <Link to="/chat" className="btn btn--primary">
              Open Chat
            </Link>
          ) : (
            <span className="settings-muted">Link Alpaca to unlock Chat.</span>
          )}
        </p>
      </motion.div>
    </div>
  );
}
