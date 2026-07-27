/**
 * Slide-out chart panel used in Chat (“See it live”).
 * Same live updates as the Charts desk: price ticks + last candle moves.
 */

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { CandleChart } from "./CandleChart";
import { API_BASE, COIN_NAMES, type ChartInterval } from "../../lib/charts";

type Props = {
  ticker: string | null;
  onClose: () => void;
};

function formatPrice(n: number) {
  if (n >= 1000) return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
  if (n >= 1) return n.toLocaleString(undefined, { maximumFractionDigits: 4 });
  return n.toFixed(6);
}

type Flash = "up" | "down" | "";

export function ChartSidebar({ ticker, onClose }: Props) {
  const [height, setHeight] = useState(380);
  // Named timeframe (not setInterval) so we don't shadow window.setInterval
  const [timeframe, setTimeframe] = useState<ChartInterval>("1m");
  const [price, setPrice] = useState<number | null>(null);
  const [flash, setFlash] = useState<Flash>("");
  const prevPrice = useRef<number | null>(null);

  useEffect(() => {
    function measure() {
      const w = window.innerWidth;
      const h = window.innerHeight;
      if (w < 640) setHeight(Math.max(240, Math.round(h * 0.42)));
      else setHeight(380);
    }
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  // Esc closes the panel
  useEffect(() => {
    if (!ticker) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [ticker, onClose]);

  // Live spot price — every 3s, same as Charts desk
  useEffect(() => {
    if (!ticker) return;

    let cancelled = false;
    prevPrice.current = null;
    setPrice(null);
    setFlash("");

    async function loadPrice() {
      try {
        const res = await fetch(`${API_BASE}/getprice/${ticker}`);
        const data = await res.json();
        if (!res.ok || cancelled) return;
        const next = Number(data.price);
        if (!Number.isFinite(next)) return;

        const old = prevPrice.current;
        if (old != null && next !== old) {
          setFlash(next > old ? "up" : "down");
          window.setTimeout(() => setFlash(""), 700);
        }
        prevPrice.current = next;
        setPrice(next);
      } catch {
        // ignore one failed tick
      }
    }

    void loadPrice();
    const id = window.setInterval(() => void loadPrice(), 3000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [ticker]);

  if (!ticker) return null;

  const name = COIN_NAMES[ticker] || ticker;

  return createPortal(
    <>
      <button
        type="button"
        className="chart-sidebar__backdrop"
        aria-label="Close chart"
        onClick={onClose}
      />

      <aside className="chart-sidebar" role="dialog" aria-label={`${ticker} live chart`}>
        <img
          src="/signal-s.png"
          alt=""
          className="chart-sidebar__brand-mark"
          aria-hidden="true"
        />

        <div className="chart-sidebar__head">
          <div>
            <p className="chart-sidebar__kicker">
              <span className="charts-desk__live-dot is-live" /> Live chart
            </p>
            <h2 className="chart-sidebar__title">
              {ticker}
              <span className="chart-sidebar__name">{name}</span>
            </h2>
            <p
              className={
                flash
                  ? `chart-sidebar__price is-flash-${flash}`
                  : "chart-sidebar__price"
              }
            >
              {price != null ? formatPrice(price) : "…"} <small>USD</small>
            </p>
          </div>
          <button type="button" className="chart-sidebar__close" onClick={onClose}>
            ✕
          </button>
        </div>

        <CandleChart
          key={`${ticker}-${timeframe}`}
          ticker={ticker}
          height={height}
          interval={timeframe}
          onIntervalChange={setTimeframe}
          livePrice={price}
        />
      </aside>
    </>,
    document.body
  );
}
