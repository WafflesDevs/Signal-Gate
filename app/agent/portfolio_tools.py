"""
In-process LangChain tools for portfolio / trading.

Trades use the chat user's Settings-linked Alpaca credentials.
User id comes from LangGraph config.configurable.user_id (preferred)
or current_user_id contextvar — never from .env Alpaca keys.
"""

from __future__ import annotations

import json
from typing import Optional

from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, model_validator
from tavily import TavilyClient

from app.core.alpaca_client import LINK_REQUIRED, TradingAuthError, friendly_trading_error
from app.core.user_context import get_current_user_id, trading_user
from app.routers import paper as paper_svc

load_dotenv()

_tavily: Optional[TavilyClient] = None


def _tavily_client() -> TavilyClient:
    global _tavily
    if _tavily is None:
        _tavily = TavilyClient()
    return _tavily


def _user_from_config(config: Optional[RunnableConfig]) -> Optional[str]:
    if not config:
        return None
    cfg = config.get("configurable") if isinstance(config, dict) else None
    if not isinstance(cfg, dict):
        return None
    uid = cfg.get("user_id")
    return str(uid).strip() if uid else None


def _require_user(config: Optional[RunnableConfig] = None) -> str:
    uid = _user_from_config(config) or get_current_user_id()
    if not uid:
        raise TradingAuthError(
            "No trading user in context. Link Alpaca in Settings and chat while logged in.",
            status_code=401,
        )
    return uid


def _err(e: Exception) -> str:
    if isinstance(e, TradingAuthError):
        return json.dumps({"error": e.detail})
    mapped = friendly_trading_error(e)
    if mapped:
        return json.dumps({"error": mapped})
    detail = getattr(e, "detail", None)
    if isinstance(detail, str) and detail:
        return json.dumps({"error": detail})
    return json.dumps({"error": str(e)})


class BuyArgs(BaseModel):
    """Buy by coin units OR by USD spend — exactly one."""

    ticker: str = Field(description="Base ticker like BTC, ETH, XRP (not BTCUSD)")
    qty: Optional[float] = Field(
        default=None,
        gt=0,
        description=(
            "Coin units to buy. ONLY when the user names a coin amount "
            "(e.g. 'buy 10 XRP', '0.01 BTC'). Never use for dollar amounts."
        ),
    )
    notional_usd: Optional[float] = Field(
        default=None,
        gt=0,
        description=(
            "USD dollars to spend (Alpaca notional). Use when the user says "
            "dollars / worth / USD / $ — e.g. '10k usd worth of XRP', '$500 of BTC', "
            "'10000 USD of ETH'. Expand suffixes before calling: 10k→10000, 1.5k→1500, "
            "2m→2000000. Do NOT convert dollars to qty yourself."
        ),
    )

    @model_validator(mode="after")
    def exactly_one_size(self):
        has_qty = self.qty is not None
        has_notional = self.notional_usd is not None
        if has_qty == has_notional:
            raise ValueError(
                "Provide exactly one of qty (coin units) or notional_usd (USD dollars)"
            )
        return self


class QtyTicker(BaseModel):
    qty: float = Field(gt=0, description="Amount of the coin to trade")
    ticker: str = Field(description="Base ticker like BTC, ETH, XRP")


class TickerOnly(BaseModel):
    ticker: str = Field(description="Base ticker like BTC, ETH, XRP")


class SearchQuery(BaseModel):
    query: str = Field(description="Web search query")


def get_current_portfoilo(config: RunnableConfig = None) -> str:
    """Get cash / equity in the linked Alpaca account."""
    try:
        uid = _require_user(config)
        with trading_user(uid):
            return json.dumps(paper_svc.account_summary(uid))
    except Exception as e:
        return _err(e)


def get_current_positions(config: RunnableConfig = None) -> str:
    """Get coins you currently hold."""
    try:
        uid = _require_user(config)
        with trading_user(uid):
            return json.dumps(paper_svc.positions_summary(uid))
    except Exception as e:
        return _err(e)


def execute_trade(
    ticker: str,
    qty: Optional[float] = None,
    notional_usd: Optional[float] = None,
    config: RunnableConfig = None,
) -> str:
    """
    Buy one coin. Pass EXACTLY ONE of:
      - notional_usd: USD to spend ("$10k worth of XRP", "10000 USD of ETH") —
        expand 10k→10000. Prefer this for any dollar / worth / USD language.
      - qty: coin units ("buy 10 XRP", "0.01 BTC") only.
    Never invent qty from dollars (and never treat "10k" as qty=10).
    """
    try:
        uid = _require_user(config)
        # Re-validate (LLM may omit schema validator path)
        args = BuyArgs(ticker=ticker, qty=qty, notional_usd=notional_usd)
        with trading_user(uid):
            if args.notional_usd is not None:
                return json.dumps(
                    paper_svc.execute_buy_notional(
                        uid, float(args.notional_usd), args.ticker
                    )
                )
            return json.dumps(
                paper_svc.execute_buy(uid, float(args.qty), args.ticker)
            )
    except Exception as e:
        return _err(e)


def buy_max_trade(ticker: str, config: RunnableConfig = None) -> str:
    """
    Spend ~95% of cash on ONE coin only. Use ONLY when the user explicitly wants max
    for a single ticker ('max', 'all in', 'fill portfolio', 'as much as possible').
    NEVER use for multi-coin buys — that empties cash on the first coin.
    NEVER use for a stated dollar amount — use execute_trade(notional_usd=...) instead.
    """
    try:
        uid = _require_user(config)
        with trading_user(uid):
            return json.dumps(paper_svc.execute_buy_max(uid, ticker))
    except Exception as e:
        return _err(e)


def sell_trade(
    qty: float, ticker: str, config: RunnableConfig = None
) -> str:
    """
    Sell a specific qty of one coin. ticker = BTC / ETH / XRP (not BTCUSD).
    For multiple coins, call once per coin with that coin's qty.
    """
    try:
        uid = _require_user(config)
        with trading_user(uid):
            return json.dumps(paper_svc.execute_sell(uid, qty, ticker))
    except Exception as e:
        return _err(e)


def search_web(query: str, config: RunnableConfig = None) -> str:
    """Search the web for information."""
    try:
        return str(_tavily_client().search(query))
    except Exception as e:
        return _err(e)


def build_portfolio_tools() -> list[StructuredTool]:
    """LangChain tools; user id from config / contextvar (same names as former MCP tools)."""
    return [
        StructuredTool.from_function(
            func=get_current_portfoilo,
            name="get_current_portfoilo",
            description=get_current_portfoilo.__doc__ or "Get account cash/equity",
        ),
        StructuredTool.from_function(
            func=get_current_positions,
            name="get_current_positions",
            description=get_current_positions.__doc__ or "Get open positions",
        ),
        StructuredTool.from_function(
            func=execute_trade,
            name="execute_trade",
            description=execute_trade.__doc__ or "Buy by qty or notional_usd",
            args_schema=BuyArgs,
        ),
        StructuredTool.from_function(
            func=buy_max_trade,
            name="buy_max_trade",
            description=buy_max_trade.__doc__ or "Buy max of one ticker",
            args_schema=TickerOnly,
        ),
        StructuredTool.from_function(
            func=sell_trade,
            name="sell_trade",
            description=sell_trade.__doc__ or "Sell qty of ticker",
            args_schema=QtyTicker,
        ),
        StructuredTool.from_function(
            func=search_web,
            name="search_web",
            description=search_web.__doc__ or "Search the web",
            args_schema=SearchQuery,
        ),
    ]


# Re-export for tests / clarity
__all__ = [
    "LINK_REQUIRED",
    "BuyArgs",
    "build_portfolio_tools",
    "execute_trade",
]
