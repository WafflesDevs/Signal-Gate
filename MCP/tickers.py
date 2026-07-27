"""
Legacy MCP tickers server (optional local use).

Production chat no longer uses this — agent_service loads in-process
market_tools that call Coinbase directly. Kept for local MCP experiments.

If you still run this via stdio, it hits Coinbase (not 127.0.0.1:8000).
"""

import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tickers")

COINBASE_SPOT = "https://api.coinbase.com/v2/prices/{base}-USD/spot"
_tracked: list[str] = ["BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "LINK", "AVAX"]


def _clean(ticker: str) -> str:
    return ticker.strip().upper().replace("/USD", "").replace("-USD", "")


@mcp.tool()
def get_tickers() -> str:
    """Get the current tickers tracked on the trading platform."""
    return str({"tickers": list(_tracked)})


@mcp.tool()
def add_ticker(ticker: str) -> str:
    """Add a coin ticker to the tracked list (e.g. ETH, BTC, SOL, DOGE)."""
    t = _clean(ticker)
    if t not in _tracked:
        _tracked.append(t)
    return str({"tickers": list(_tracked), "added": t})


@mcp.tool()
def remove_ticker(ticker: str) -> str:
    """Remove a coin ticker from the tracked list."""
    t = _clean(ticker)
    if t not in _tracked:
        return str({"error": f"{t} is not in the ticker list"})
    _tracked.remove(t)
    return str({"tickers": list(_tracked), "removed": t})


@mcp.tool()
def get_price(ticker: str) -> str:
    """Get the current USD price of a ticker (e.g. ETH, BTC, SOL)."""
    t = _clean(ticker)
    try:
        r = requests.get(COINBASE_SPOT.format(base=t), timeout=10)
        r.raise_for_status()
        amount = (r.json().get("data") or {}).get("amount")
        if amount is None:
            return str({"error": f"No USD price for {t}"})
        if t not in _tracked:
            _tracked.append(t)
        return str({"ticker": t, "price": amount, "currency": "USD", "source": "coinbase"})
    except Exception as e:
        return str({"error": str(e)})


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
