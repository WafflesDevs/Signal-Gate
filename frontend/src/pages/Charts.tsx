/**
 * Charts page = one big live chart + a coin list on the right.
 * Click a coin → that coin’s chart loads.
 * Prices + the last candle refresh every few seconds.
 */

import { useEffect, useRef, useState } from "react";
import { CandleChart } from "../components/charts/CandleChart";
import {
  API_BASE,
  CHART_COINS,
  CHART_INTERVALS,
  COIN_NAMES,
  type ChartInterval,
} from "../lib/charts";

function formatPrice(n: number) {
  if (n >= 1000) return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
  if (n >= 1) return n.toLocaleString(undefined, { maximumFractionDigits: 4 });
  return n.toFixed(6);
}

type Flash = "up" | "down" | "";

export function Charts() {
  const [selected, setSelected] = useState("ETH");
  // Named timeframe (not setInterval) so we don't shadow window.setInterval
  const [timeframe, setTimeframe] = useState<ChartInterval>("4h");
  // Map of ticker → last price, e.g. { ETH: 1945.32 }
  const [prices, setPrices] = useState<Record<string, number>>({});
  const [flashes, setFlashes] = useState<Record<string, Flash>>({});
  const prevPrices = useRef<Record<string, number>>({});
  const [chartHeight, setChartHeight] = useState(520);

  // Keep the chart tall on desktop, shorter on phones
  useEffect(() => {
    function measure() {
      const w = window.innerWidth;
      const h = window.innerHeight;
      if (w < 640) setChartHeight(Math.max(260, Math.round(h * 0.38)));
      else if (w < 960) setChartHeight(400);
      else setChartHeight(520);
    }
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  // Load prices often so the numbers keep moving
  useEffect(() => {
    let cancelled = false;

    async function loadPrices() {
      const next: Record<string, number> = {};
      await Promise.all(
        CHART_COINS.map(async (coin) => {
          try {
            const res = await fetch(`${API_BASE}/getprice/${coin}`);
            const data = await res.json();
            if (res.ok) next[coin] = Number(data.price);
          } catch {
            // skip failed coins
          }
        })
      );
      if (cancelled) return;

      const nextFlashes: Record<string, Flash> = {};
      for (const coin of Object.keys(next)) {
        const old = prevPrices.current[coin];
        const neu = next[coin];
        if (old != null && neu !== old) {
          nextFlashes[coin] = neu > old ? "up" : "down";
        }
      }
      prevPrices.current = { ...prevPrices.current, ...next };
      setPrices((p) => ({ ...p, ...next }));
      if (Object.keys(nextFlashes).length) {
        setFlashes((f) => ({ ...f, ...nextFlashes }));
        window.setTimeout(() => {
          setFlashes((f) => {
            const cleared = { ...f };
            for (const coin of Object.keys(nextFlashes)) cleared[coin] = "";
            return cleared;
          });
        }, 700);
      }
    }

    void loadPrices();
    const id = window.setInterval(() => void loadPrices(), 3000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const price = prices[selected];
  const flash = flashes[selected] || "";

  return (
    <div className="page charts-desk">
      <div className="charts-desk__shell">
        {/* LEFT: big chart */}
        <section className="charts-desk__main">
          <header className="charts-desk__toolbar">
            <div className="charts-desk__symbol">
              <span className="charts-desk__pair">{selected}USD</span>
              <span className="charts-desk__name">
                {COIN_NAMES[selected] || selected} / U.S. Dollar
              </span>
            </div>

            <div className="charts-desk__intervals">
              {CHART_INTERVALS.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  className={
                    timeframe === opt.id ? "charts-desk__tf is-active" : "charts-desk__tf"
                  }
                  onClick={() => setTimeframe(opt.id)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </header>

          <div className="charts-desk__stage">
            <div className="charts-desk__watermark" aria-hidden="true">
              <strong>
                {selected}USD, {timeframe}
              </strong>
              <span>{COIN_NAMES[selected] || selected} / U.S. Dollar</span>
            </div>

            <img
              src="/signal-s.png"
              alt=""
              className="charts-desk__brand-mark"
              aria-hidden="true"
            />

            <CandleChart
              key={`${selected}-${timeframe}`}
              ticker={selected}
              height={chartHeight}
              interval={timeframe}
              onIntervalChange={setTimeframe}
              hideToolbar
              livePrice={price ?? null}
            />
          </div>
        </section>

        {/* RIGHT: selected coin + list */}
        <aside className="charts-desk__side">
          <div className="charts-desk__detail">
            <p className="charts-desk__detail-kicker">Selected</p>
            <h2 className="charts-desk__detail-title">
              {selected}
              <span>{COIN_NAMES[selected] || ""}</span>
            </h2>
            <p
              className={
                flash
                  ? `charts-desk__detail-price is-flash-${flash}`
                  : "charts-desk__detail-price"
              }
            >
              {price != null ? formatPrice(price) : "—"} <small>USD</small>
            </p>
            <p className="charts-desk__detail-status">
              <span className="charts-desk__live-dot is-live" /> Live · updating
            </p>
          </div>

          <div className="charts-desk__watch">
            <div className="charts-desk__watch-head">
              <span>Symbol</span>
              <span>Last</span>
            </div>
            <ul className="charts-desk__watch-list">
              {CHART_COINS.map((coin) => {
                const rowFlash = flashes[coin] || "";
                return (
                  <li key={coin}>
                    <button
                      type="button"
                      className={
                        coin === selected
                          ? "charts-desk__row is-active"
                          : "charts-desk__row"
                      }
                      onClick={() => setSelected(coin)}
                    >
                      <span className="charts-desk__row-sym">{coin}</span>
                      <span
                        className={
                          rowFlash
                            ? `charts-desk__row-px is-flash-${rowFlash}`
                            : "charts-desk__row-px"
                        }
                      >
                        {prices[coin] != null ? formatPrice(prices[coin]) : "…"}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}
