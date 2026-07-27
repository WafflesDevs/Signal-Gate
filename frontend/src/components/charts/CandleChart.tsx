/**
 * Draws a candlestick chart for one coin.
 *
 * 1) Make an empty chart in a div
 * 2) Fetch OHLC history from our API
 * 3) Show recent bars (scroll left for older data)
 * 4) Keep the last bar live from the spot price
 */

import { useEffect, useRef, useState } from "react";
import {
  CandlestickSeries,
  ColorType,
  HistogramSeries,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { API_BASE, CHART_INTERVALS, type ChartInterval } from "../../lib/charts";

type Candle = {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
};

type Props = {
  ticker: string;
  height?: number;
  interval?: ChartInterval;
  onIntervalChange?: (next: ChartInterval) => void;
  hideToolbar?: boolean;
  /** Live spot price — updates the current (last) candle as it moves */
  livePrice?: number | null;
};

/** How often to re-fetch candles (ms). Faster for short timeframes. */
function pollMs(interval: ChartInterval) {
  if (interval === "1m") return 5000;
  if (interval === "5m" || interval === "15m") return 8000;
  return 15000;
}

/** How many bars to show on first load (older ones stay off-screen to the left). */
function visibleBars(interval: ChartInterval) {
  if (interval === "1m" || interval === "5m") return 120;
  if (interval === "15m" || interval === "30m") return 100;
  if (interval === "1h" || interval === "4h") return 90;
  return 80; // 1d / 1w
}

/** Price axis precision — PEPE/SHIB need more decimals than BTC. */
function priceFormatFor(price: number) {
  if (price >= 1000) return { type: "price" as const, precision: 2, minMove: 0.01 };
  if (price >= 1) return { type: "price" as const, precision: 4, minMove: 0.0001 };
  if (price >= 0.01) return { type: "price" as const, precision: 6, minMove: 0.000001 };
  return { type: "price" as const, precision: 8, minMove: 0.00000001 };
}

function candleUrl(ticker: string, interval: ChartInterval) {
  return `${API_BASE}/candles/${ticker}?interval=${interval}`;
}

function priceUrl(ticker: string) {
  return `${API_BASE}/getprice/${ticker}`;
}

function errorDetail(data: unknown, fallback: string) {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map(String).join(", ");
  }
  return fallback;
}

export function CandleChart({
  ticker,
  height = 320,
  interval: intervalFromParent,
  onIntervalChange,
  hideToolbar = false,
  livePrice = null,
}: Props) {
  const divRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const lastCandleRef = useRef<Candle | null>(null);
  const hasHistoryRef = useRef(false);
  const barCountRef = useRef(0);

  const [myInterval, setMyInterval] = useState<ChartInterval>("15m");
  const interval = intervalFromParent || myInterval;

  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function changeInterval(next: ChartInterval) {
    if (onIntervalChange) onIntervalChange(next);
    else setMyInterval(next);
  }

  function showRecent(totalBars: number) {
    const chart = chartRef.current;
    if (!chart || totalBars <= 0) return;
    const windowSize = Math.min(visibleBars(interval), totalBars);
    const from = Math.max(-0.5, totalBars - windowSize);
    chart.timeScale().setVisibleLogicalRange({
      from,
      to: totalBars + 3,
    });
  }

  function paintCandles(rows: Candle[], resetView: boolean) {
    if (rows.length) {
      candleRef.current?.applyOptions({
        priceFormat: priceFormatFor(rows[rows.length - 1].close),
      });
    }

    candleRef.current?.setData(
      rows.map((c) => ({
        time: c.time as UTCTimestamp,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
    );

    volumeRef.current?.setData(
      rows.map((c) => ({
        time: c.time as UTCTimestamp,
        value: c.volume || 0,
        color:
          c.close >= c.open
            ? "rgba(62, 207, 154, 0.35)"
            : "rgba(232, 93, 93, 0.35)",
      }))
    );

    lastCandleRef.current = rows.length ? { ...rows[rows.length - 1] } : null;
    hasHistoryRef.current = rows.length > 0;
    barCountRef.current = rows.length;

    if (resetView && rows.length) {
      showRecent(rows.length);
    }
  }

  // Step 1 — create the chart (rebuild when ticker OR timeframe changes)
  useEffect(() => {
    const el = divRef.current;
    if (!el) return;

    hasHistoryRef.current = false;
    lastCandleRef.current = null;
    barCountRef.current = 0;

    const chart = createChart(el, {
      width: el.clientWidth || 360,
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#8b93a7",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.05)" },
        horzLines: { color: "rgba(255,255,255,0.05)" },
      },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.08)" },
      timeScale: {
        borderColor: "rgba(255,255,255,0.08)",
        timeVisible: true,
        rightOffset: 4,
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true },
      handleScale: { mouseWheel: true, pinch: true },
    });

    const candles = chart.addSeries(CandlestickSeries, {
      upColor: "#3ecf9a",
      downColor: "#e85d5d",
      borderUpColor: "#3ecf9a",
      borderDownColor: "#e85d5d",
      wickUpColor: "#3ecf9a",
      wickDownColor: "#e85d5d",
    });

    const volume = chart.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "vol",
    });
    chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    chart.priceScale("right").applyOptions({ scaleMargins: { top: 0.08, bottom: 0.22 } });

    chartRef.current = chart;
    candleRef.current = candles;
    volumeRef.current = volume;
    setReady(true);

    function onResize() {
      if (divRef.current) {
        chart.applyOptions({ width: divRef.current.clientWidth, height });
      }
    }
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
      chartRef.current = null;
      candleRef.current = null;
      volumeRef.current = null;
      setReady(false);
    };
  }, [ticker, interval, height]);

  // Step 2 — load history, then keep refreshing the tip
  useEffect(() => {
    if (!ready) return;

    let cancelled = false;
    let first = true;

    async function loadCandles() {
      if (first) {
        setLoading(true);
        setError("");
      }
      try {
        const res = await fetch(candleUrl(ticker, interval));
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(errorDetail(data, "Could not load candles"));
        if (cancelled) return;

        const rows: Candle[] = data.candles || [];
        if (!rows.length) throw new Error("No candle history returned");

        // Keep the user’s scroll position on live refreshes
        paintCandles(rows, first);
      } catch (e) {
        if (!cancelled && first) {
          const msg =
            e instanceof TypeError
              ? "Cannot reach API (is the backend running?)"
              : e instanceof Error
                ? e.message
                : "Chart failed";
          setError(msg);
        }
      } finally {
        if (!cancelled && first) setLoading(false);
        first = false;
      }
    }

    void loadCandles();
    const id = window.setInterval(() => void loadCandles(), pollMs(interval));

    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
    // interval is already in the chart-create effect deps; keep it here for fetch URL
  }, [ready, ticker, interval]);

  // Step 3 — if parent didn’t pass a price, fetch one ourselves
  const [ownPrice, setOwnPrice] = useState<number | null>(null);
  useEffect(() => {
    if (livePrice != null) return;

    let cancelled = false;
    async function loadPrice() {
      try {
        const res = await fetch(priceUrl(ticker));
        const data = await res.json();
        if (!cancelled && res.ok) setOwnPrice(Number(data.price));
      } catch {
        // ignore
      }
    }

    void loadPrice();
    const id = window.setInterval(() => void loadPrice(), 3000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [ticker, livePrice]);

  const spot = livePrice != null ? livePrice : ownPrice;

  // Step 4 — push live spot price into the CURRENT candle only (after history loaded)
  useEffect(() => {
    if (spot == null || !Number.isFinite(spot)) return;
    if (!hasHistoryRef.current) return;
    const last = lastCandleRef.current;
    const series = candleRef.current;
    if (!last || !series) return;

    const next: Candle = {
      ...last,
      close: spot,
      high: Math.max(last.high, spot),
      low: Math.min(last.low, spot),
    };
    lastCandleRef.current = next;

    try {
      series.update({
        time: next.time as UTCTimestamp,
        open: next.open,
        high: next.high,
        low: next.low,
        close: next.close,
      });
    } catch {
      // Chart may have been torn down mid-update
    }
  }, [spot]);

  return (
    <div className={`candle-chart${hideToolbar ? " candle-chart--bare" : ""}`}>
      {!hideToolbar && (
        <div className="candle-chart__bar">
          <span className="candle-chart__pair">{ticker}/USD</span>
          <div className="candle-chart__intervals">
            {CHART_INTERVALS.map((opt) => (
              <button
                key={opt.id}
                type="button"
                className={
                  interval === opt.id ? "candle-chart__tf is-active" : "candle-chart__tf"
                }
                onClick={() => changeInterval(opt.id)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="candle-chart__canvas-wrap" style={{ height }}>
        <div ref={divRef} className="candle-chart__canvas" />
        {loading && <p className="candle-chart__status">Loading history…</p>}
        {error && !loading && <p className="candle-chart__status">{error}</p>}
      </div>
    </div>
  );
}
