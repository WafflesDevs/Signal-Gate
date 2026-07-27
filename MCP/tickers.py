import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tickers")

BASE = "http://127.0.0.1:8000"


@mcp.tool()
def get_tickers() -> str:
    """Get the current tickers tracked on the trading platform."""
    r = requests.get(f"{BASE}/tickers")
    return str(r.json())


@mcp.tool()
def add_ticker(ticker: str) -> str:
    """Add a coin ticker to the tracked list (e.g. ETH, BTC, SOL, DOGE)."""
    r = requests.post(f"{BASE}/tickers", json={"ticker": ticker})
    return str(r.json())


@mcp.tool()
def remove_ticker(ticker: str) -> str:
    """Remove a coin ticker from the tracked list."""
    r = requests.delete(f"{BASE}/tickers/{ticker}")
    return str(r.json())


@mcp.tool()
def get_price(ticker: str) -> str:
    """Get the current USD price of a ticker (e.g. ETH, BTC, SOL)."""
    r = requests.get(f"{BASE}/getprice/{ticker}")
    return str(r.json())


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
