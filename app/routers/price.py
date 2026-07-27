"""
Price + ticker + candle routes.

  GET /tickers
  GET /getprice/{ticker}
  GET /candles/{ticker}?interval=15m
"""

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field
import requests

from app.core.alpaca_tickers import ALPACA_BASES

router = APIRouter(tags=["price"])

# In-memory list the agent can add/remove from
tickers: list[str] = list(ALPACA_BASES)

# Timeframes Binance understands (+ a few aliases people click)
INTERVALS = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "60": "1h",
    "4h": "4h",
    "1d": "1d",
    "d": "1d",
    "1w": "1w",
    "w": "1w",
}

# How many bars to keep for each timeframe (enough to scroll back)
HISTORY_BARS = {
    "1m": 1500,   # ~25 hours
    "5m": 1500,   # ~5 days
    "15m": 1500,  # ~15 days
    "30m": 1500,  # ~1 month
    "1h": 1500,   # ~2 months
    "4h": 1500,   # ~8 months
    "1d": 1000,   # ~3 years
    "1w": 500,    # ~10 years
}

BINANCE_URL = "https://data-api.binance.vision/api/v3/klines"
BINANCE_LIMIT = 1000  # max per request


class TickerBody(BaseModel):
    ticker: str = Field(min_length=1, description="Coin symbol, e.g. ETH")


def clean_ticker(ticker: str) -> str:
    """ETH / ETH-USD / ETH/USD → ETH"""
    return ticker.strip().upper().replace("/USD", "").replace("-USD", "")


def fetch_binance_klines(symbol: str, binance_interval: str, want: int) -> list:
    """
    Pull older + newer candles from Binance.
    One call maxes out at 1000 bars, so we walk backward until we have enough.
    """
    rows: list = []
    end_time = None  # None = most recent

    while len(rows) < want:
        params: dict = {
            "symbol": symbol,
            "interval": binance_interval,
            "limit": BINANCE_LIMIT,
        }
        if end_time is not None:
            params["endTime"] = end_time

        r = requests.get(BINANCE_URL, params=params, timeout=20)
        if r.status_code != 200:
            break

        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break

        # batch is oldest → newest; prepend older page in front
        rows = batch + rows
        end_time = int(batch[0][0]) - 1

        # Last page (fewer than max) means no more history
        if len(batch) < BINANCE_LIMIT:
            break

    # Drop duplicate timestamps if pages overlapped
    seen = set()
    unique = []
    for row in rows:
        t = int(row[0])
        if t in seen:
            continue
        seen.add(t)
        unique.append(row)

    # Keep the most recent `want` bars
    if len(unique) > want:
        unique = unique[-want:]
    return unique


@router.get("/tickers", status_code=status.HTTP_200_OK)
def get_tickers():
    return {"tickers": tickers}


@router.post("/tickers", status_code=status.HTTP_200_OK)
def add_ticker(body: TickerBody):
    ticker = clean_ticker(body.ticker)
    if ticker not in tickers:
        tickers.append(ticker)
    return {"tickers": tickers, "added": ticker}


@router.delete("/tickers/{ticker}", status_code=status.HTTP_200_OK)
def remove_ticker(ticker: str):
    ticker = clean_ticker(ticker)
    if ticker not in tickers:
        raise HTTPException(status_code=404, detail=f"{ticker} is not in the ticker list")
    tickers.remove(ticker)
    return {"tickers": tickers, "removed": ticker}


@router.get("/getprice/{ticker}", status_code=status.HTTP_200_OK)
def get_price(ticker: str):
    """Current USD price from Coinbase (public; no Alpaca)."""
    ticker = clean_ticker(ticker)
    try:
        r = requests.get(
            f"https://api.coinbase.com/v2/prices/{ticker}-USD/spot",
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        amount = data.get("data", {}).get("amount")
        if amount is None:
            raise HTTPException(status_code=404, detail=f"No USD price for {ticker}")
        if ticker not in tickers:
            tickers.append(ticker)
        return {
            "ticker": ticker,
            "price": amount,
            "currency": "USD",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/candles/{ticker}", status_code=status.HTTP_200_OK)
def get_candles(
    ticker: str,
    interval: str = Query(default="15m"),
):
    """
    Candle bars for the chart UI (includes older history you can scroll into).
    Returns: { ticker, interval, candles: [{ time, open, high, low, close, volume }] }
    """
    ticker = clean_ticker(ticker)
    key = interval.strip().lower()
    binance_interval = INTERVALS.get(key)
    if not binance_interval:
        raise HTTPException(
            status_code=400,
            detail=f"Bad interval. Use: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w",
        )

    want = HISTORY_BARS.get(binance_interval, 1000)

    try:
        rows = fetch_binance_klines(f"{ticker}USDT", binance_interval, want)
        if not rows:
            raise HTTPException(status_code=400, detail=f"No chart data for {ticker}")

        candles = []
        for row in rows:
            candles.append(
                {
                    "time": int(row[0]) // 1000,  # ms → seconds
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                }
            )

        return {
            "ticker": ticker,
            "interval": binance_interval,
            "candles": candles,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
