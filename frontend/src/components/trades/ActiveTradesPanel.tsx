/**
 * Signal Gate desk view — open Alpaca positions + SL/TP exit rules.
 * Polls GET /paper/active-trades while Chat is open.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useApi } from "../../lib/api";

export type ActiveTrade = {
  symbol: string;
  ticker: string;
  qty: number;
  avg_entry_price: number | null;
  current_price: number | null;
  unrealized_pl: number | null;
  unrealized_plpc?: number | null;
  market_value?: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  exit_qty?: number | null;
  has_exit: boolean;
};

type ActiveTradesResponse = {
  trades: ActiveTrade[];
  count: number;
  paper: boolean;
};

type Props = {
  /** Bump after a trade approve so the panel refreshes immediately. */
  refreshKey?: number;
  collapsed?: boolean;
  onToggle?: () => void;
  /** Compact rail (desktop) vs drawer strip (mobile). */
  variant?: "rail" | "drawer";
};

const POLL_MS = 4000;

function formatQty(n: number) {
  if (n >= 1000) return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
  if (n >= 1) return n.toLocaleString(undefined, { maximumFractionDigits: 4 });
  return n.toLocaleString(undefined, { maximumFractionDigits: 8 });
}

function formatPx(n: number) {
  if (n >= 1000) return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
  if (n >= 1) return n.toLocaleString(undefined, { maximumFractionDigits: 4 });
  return n.toFixed(6);
}

function formatPl(n: number) {
  const abs = Math.abs(n);
  const formatted =
    abs >= 1000
      ? abs.toLocaleString(undefined, { maximumFractionDigits: 2 })
      : abs.toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
  return `${n < 0 ? "-" : "+"}$${formatted}`;
}

function formatPct(n: number) {
  // Alpaca unrealized_plpc is typically a fraction (0.05 = 5%)
  const pct = Math.abs(n) <= 1 ? n * 100 : n;
  const sign = pct < 0 ? "" : "+";
  return `${sign}${pct.toFixed(2)}%`;
}

export function ActiveTradesPanel({
  refreshKey = 0,
  collapsed = false,
  onToggle,
  variant = "rail",
}: Props) {
  const api = useApi();
  const [trades, setTrades] = useState<ActiveTrade[]>([]);
  const [count, setCount] = useState(0);
  const [paper, setPaper] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const mounted = useRef(true);
  const loadSeq = useRef(0);
  const inflight = useRef(false);

  const load = useCallback(async () => {
    // Skip overlapping polls — slow Alpaca+spot responses were overwriting newer data
    if (inflight.current) return;
    inflight.current = true;
    const seq = ++loadSeq.current;
    try {
      const data = (await api.get("/paper/active-trades")) as ActiveTradesResponse;
      if (!mounted.current || seq !== loadSeq.current) return;
      const next = Array.isArray(data.trades) ? data.trades : [];
      setTrades(next);
      setCount(
        typeof data.count === "number" ? data.count : next.length,
      );
      setPaper(data.paper !== false);
      setError("");
      setUpdatedAt(new Date());
    } catch (e) {
      if (!mounted.current || seq !== loadSeq.current) return;
      const msg = e instanceof Error ? e.message : "Could not load positions";
      // Link / auth failures — surface a clear empty-state style message
      setError(msg);
      if (
        msg.toLowerCase().includes("link") ||
        msg.toLowerCase().includes("alpaca") ||
        msg.toLowerCase().includes("401") ||
        msg.toLowerCase().includes("403")
      ) {
        setTrades([]);
        setCount(0);
      }
    } finally {
      inflight.current = false;
      if (mounted.current && seq === loadSeq.current) setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    mounted.current = true;
    void load();
    const id = window.setInterval(() => void load(), POLL_MS);
    return () => {
      mounted.current = false;
      loadSeq.current += 1; // invalidate in-flight apply
      window.clearInterval(id);
    };
  }, [load]);

  // Immediate refresh after trade approval (parent bumps refreshKey)
  useEffect(() => {
    if (refreshKey > 0) {
      inflight.current = false; // allow forced refresh even if a poll is mid-flight
      void load();
    }
  }, [refreshKey, load]);

  const linkNeeded =
    !!error &&
    (error.toLowerCase().includes("link") ||
      error.toLowerCase().includes("credentials") ||
      error.toLowerCase().includes("not connected"));

  return (
    <aside
      className={`active-trades active-trades--${variant}${
        collapsed ? " is-collapsed" : ""
      }`}
      aria-label="Active trades"
    >
      <header className="active-trades__head">
        <div className="active-trades__titles">
          <p className="active-trades__kicker">Desk · Signal Gate</p>
          <h2 className="active-trades__title">
            Active trades
            {count > 0 && (
              <span className="active-trades__count">{count}</span>
            )}
          </h2>
          <p className="active-trades__sub">
            Live book from your {paper ? "paper" : "live"} Alpaca account
          </p>
        </div>
        <div className="active-trades__head-right">
          <span
            className={`active-trades__live${loading && !updatedAt ? "" : " is-live"}`}
            title={
              updatedAt
                ? `Updated ${updatedAt.toLocaleTimeString()}`
                : "Connecting…"
            }
          >
            <span className="active-trades__live-dot" />
            Live
          </span>
          {onToggle && (
            <button
              type="button"
              className="active-trades__toggle"
              onClick={onToggle}
              aria-expanded={!collapsed}
              aria-label={collapsed ? "Expand active trades" : "Collapse active trades"}
              title={collapsed ? "Expand" : "Collapse"}
            >
              {variant === "rail"
                ? collapsed
                  ? "▸"
                  : "◂"
                : collapsed
                  ? "▸"
                  : "▾"}
            </button>
          )}
        </div>
      </header>

      {!collapsed && (
        <div className="active-trades__body">
          {loading && !updatedAt && (
            <p className="active-trades__empty">Loading positions…</p>
          )}

          {!loading && linkNeeded && (
            <div className="active-trades__empty">
              <p>Link Alpaca in Settings to see open positions.</p>
              <Link to="/settings" className="active-trades__link">
                Open Settings →
              </Link>
            </div>
          )}

          {!loading && !linkNeeded && error && trades.length === 0 && (
            <p className="active-trades__empty active-trades__empty--err">
              {error}
            </p>
          )}

          {!loading && !error && trades.length === 0 && (
            <p className="active-trades__empty">
              No open trades. Approve a buy on the desk and it will show up here.
            </p>
          )}

          {trades.length > 0 && (
            <ul className="active-trades__list">
              {trades.map((t) => {
                const pl = t.unrealized_pl;
                const plUp = pl != null && pl >= 0;
                const plDown = pl != null && pl < 0;
                return (
                  <li key={t.symbol} className="active-trades__row">
                    <div className="active-trades__row-top">
                      <div>
                        <span className="active-trades__sym">{t.ticker}</span>
                        <span className="active-trades__pair">{t.symbol}</span>
                      </div>
                      <div
                        className={`active-trades__pl${
                          plUp ? " is-up" : plDown ? " is-down" : ""
                        }`}
                      >
                        {pl != null ? formatPl(pl) : "—"}
                        {t.unrealized_plpc != null && (
                          <small>{formatPct(t.unrealized_plpc)}</small>
                        )}
                      </div>
                    </div>

                    <div className="active-trades__meta">
                      <span>
                        Qty <strong>{formatQty(t.qty)}</strong>
                      </span>
                      <span>
                        Avg{" "}
                        <strong>
                          {t.avg_entry_price != null
                            ? `$${formatPx(t.avg_entry_price)}`
                            : "—"}
                        </strong>
                      </span>
                      <span>
                        Now{" "}
                        <strong>
                          {t.current_price != null
                            ? `$${formatPx(t.current_price)}`
                            : "—"}
                        </strong>
                      </span>
                    </div>

                    <div className="active-trades__exits">
                      {t.has_exit ? (
                        <>
                          <span className="active-trades__exit active-trades__exit--sl">
                            SL{" "}
                            {t.stop_loss != null
                              ? `$${formatPx(t.stop_loss)}`
                              : "—"}
                          </span>
                          <span className="active-trades__exit active-trades__exit--tp">
                            TP{" "}
                            {t.take_profit != null
                              ? `$${formatPx(t.take_profit)}`
                              : "—"}
                          </span>
                        </>
                      ) : (
                        <span className="active-trades__exit active-trades__exit--none">
                          No SL/TP
                        </span>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </aside>
  );
}
