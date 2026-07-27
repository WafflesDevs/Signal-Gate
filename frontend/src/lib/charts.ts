/**
 * Shared chart settings.
 *
 * API_BASE defaults to "" (same-origin) so Vite can proxy /candles + /getprice
 * (see vite.config.ts). Set VITE_API_BASE / VITE_API_URL only when the API is
 * on another host (split Static Site + Web Service).
 */

export { API_BASE, apiUrl } from "./config";

// Coins on the Charts page + “See it live” detection
export const CHART_COINS = [
  "BTC",
  "ETH",
  "SOL",
  "XRP",
  "DOGE",
  "AVAX",
  "LINK",
  "ADA",
  "DOT",
  "LTC",
  "UNI",
  "PEPE",
  "AAVE",
  "BCH",
  "FIL",
  "SHIB",
];

export const COIN_NAMES: Record<string, string> = {
  BTC: "Bitcoin",
  ETH: "Ethereum",
  SOL: "Solana",
  XRP: "XRP",
  DOGE: "Dogecoin",
  AVAX: "Avalanche",
  LINK: "Chainlink",
  ADA: "Cardano",
  DOT: "Polkadot",
  LTC: "Litecoin",
  UNI: "Uniswap",
  PEPE: "Pepe",
  AAVE: "Aave",
  BCH: "Bitcoin Cash",
  FIL: "Filecoin",
  SHIB: "Shiba Inu",
};

// Time buttons on the chart
export type ChartInterval = "1m" | "5m" | "15m" | "30m" | "1h" | "4h" | "1d" | "1w";

export const CHART_INTERVALS: { id: ChartInterval; label: string }[] = [
  { id: "1m", label: "1m" },
  { id: "5m", label: "5m" },
  { id: "15m", label: "15m" },
  { id: "30m", label: "30m" },
  { id: "1h", label: "1h" },
  { id: "4h", label: "4h" },
  { id: "1d", label: "D" },
  { id: "1w", label: "W" },
];

/** Return a coin ticker if the message looks like a price question. */
export function detectPriceTicker(message: string): string | null {
  const text = message.toUpperCase();

  // Must mention something price-related
  const isPriceAsk =
    text.includes("PRICE") ||
    text.includes("QUOTE") ||
    text.includes("HOW MUCH") ||
    text.includes("WORTH") ||
    text.includes("SPOT");

  if (!isPriceAsk) return null;

  // First coin name we find in the message
  for (const coin of CHART_COINS) {
    if (text.includes(coin)) return coin;
  }
  return null;
}
