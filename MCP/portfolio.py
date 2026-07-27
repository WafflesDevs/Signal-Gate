"""
DEPRECATED for the chat agent.

Trading/portfolio tools now run in-process via app/agent/portfolio_tools.py
using the logged-in user's Settings credentials (never .env Alpaca keys).

This MCP script is kept only for local experiments. Unauthenticated HTTP
calls to /paper/* will fail (auth required). Do not re-wire the agent to
this file for live trading.
"""

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

mcp = FastMCP("portfolio")
tavily = TavilyClient()

_DISABLED = (
    "Portfolio MCP HTTP tools are disabled. "
    "Use Settings-linked credentials via in-process agent tools."
)


@mcp.tool()
def search_web(query: str) -> str:
    """Search the web for information."""
    return str(tavily.search(query))


@mcp.tool()
def get_current_portfoilo() -> str:
    """Disabled — agent uses in-process tools with per-user Alpaca keys."""
    return _DISABLED


@mcp.tool()
def get_current_positions() -> str:
    """Disabled — agent uses in-process tools with per-user Alpaca keys."""
    return _DISABLED


@mcp.tool()
def execute_trade(qty: float, ticker: str):
    """Disabled — agent uses in-process tools with per-user Alpaca keys."""
    return {"error": _DISABLED}


@mcp.tool()
def buy_max_trade(ticker: str):
    """Disabled — agent uses in-process tools with per-user Alpaca keys."""
    return {"error": _DISABLED}


@mcp.tool()
def sell_trade(qty: float, ticker: str):
    """Disabled — agent uses in-process tools with per-user Alpaca keys."""
    return {"error": _DISABLED}


@mcp.tool()
def set_exits(
    ticker: str,
    stop_loss: float | None = None,
    take_profit: float | None = None,
    qty: float | None = None,
):
    """Disabled — use authenticated /paper/exits API."""
    return {"error": _DISABLED}


@mcp.tool()
def list_exits() -> str:
    """Disabled — use authenticated /paper/exits API."""
    return _DISABLED


@mcp.tool()
def cancel_exits(ticker: str):
    """Disabled — use authenticated /paper/exits API."""
    return {"error": _DISABLED}


if __name__ == "__main__":
    mcp.run(transport="stdio")
