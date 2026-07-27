"""
In-process market data tools (prices / ticker list).

Public Coinbase spot — no Alpaca keys, no MCP stdio, no loopback HTTP.
Used by the chat agent on Render where MCP + 127.0.0.1:8000 fails.
"""

from __future__ import annotations

import json

import requests
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.routers import price as price_svc

COINBASE_SPOT = "https://api.coinbase.com/v2/prices/{base}-USD/spot"


class TickerArg(BaseModel):
    ticker: str = Field(description="Base ticker like BTC, ETH, XRP, SOL")


def _fetch_spot_usd(ticker: str) -> dict:
    base = price_svc.clean_ticker(ticker)
    if not base:
        raise ValueError("ticker is required")
    r = requests.get(COINBASE_SPOT.format(base=base), timeout=10)
    r.raise_for_status()
    amount = (r.json().get("data") or {}).get("amount")
    if amount is None:
        raise ValueError(f"No USD spot price for {base}")
    # Keep agent-tracked list in sync when users ask about a new coin
    if base not in price_svc.tickers:
        price_svc.tickers.append(base)
    return {
        "ticker": base,
        "price": str(amount),
        "currency": "USD",
        "source": "coinbase",
    }


def get_tickers() -> str:
    """Get the current tickers tracked on the trading platform."""
    return json.dumps({"tickers": list(price_svc.tickers)})


def add_ticker(ticker: str) -> str:
    """Add a coin ticker to the tracked list (e.g. ETH, BTC, SOL, DOGE)."""
    base = price_svc.clean_ticker(ticker)
    if base not in price_svc.tickers:
        price_svc.tickers.append(base)
    return json.dumps({"tickers": list(price_svc.tickers), "added": base})


def remove_ticker(ticker: str) -> str:
    """Remove a coin ticker from the tracked list."""
    base = price_svc.clean_ticker(ticker)
    if base not in price_svc.tickers:
        return json.dumps({"error": f"{base} is not in the ticker list"})
    price_svc.tickers.remove(base)
    return json.dumps({"tickers": list(price_svc.tickers), "removed": base})


def get_price(ticker: str) -> str:
    """Get the current USD price of a ticker (e.g. ETH, BTC, SOL). Uses Coinbase spot."""
    try:
        return json.dumps(_fetch_spot_usd(ticker))
    except Exception as e:
        return json.dumps({"error": str(e)})


def build_market_tools() -> list[StructuredTool]:
    """LangChain tools matching former MCP tickers server names."""
    return [
        StructuredTool.from_function(
            func=get_tickers,
            name="get_tickers",
            description=get_tickers.__doc__ or "List tracked tickers",
        ),
        StructuredTool.from_function(
            func=add_ticker,
            name="add_ticker",
            description=add_ticker.__doc__ or "Add a ticker",
            args_schema=TickerArg,
        ),
        StructuredTool.from_function(
            func=remove_ticker,
            name="remove_ticker",
            description=remove_ticker.__doc__ or "Remove a ticker",
            args_schema=TickerArg,
        ),
        StructuredTool.from_function(
            func=get_price,
            name="get_price",
            description=get_price.__doc__ or "Get USD spot price",
            args_schema=TickerArg,
        ),
    ]
