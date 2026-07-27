import requests
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

mcp = FastMCP("portfolio")
BASE = "http://127.0.0.1:8000"
tavily = TavilyClient()


@mcp.tool()
def search_web(query: str) -> str:
    """Search the web for information."""
    return str(tavily.search(query))


@mcp.tool()
def get_current_portfoilo() -> str:
    """Get cash / equity in the paper account."""
    return str(requests.get(f"{BASE}/paper/account").json())


@mcp.tool()
def get_current_positions() -> str:
    """Get coins you currently hold."""
    return str(requests.get(f"{BASE}/paper/positions").json())


@mcp.tool()
def execute_trade(qty: float, ticker: str):
    """
    Buy a specific qty of one coin. ticker = BTC / ETH / XRP (not BTCUSD).
    Use this for every normal buy, including multi-coin requests — call once per coin
    with its own qty. Prefer this over buy_max_trade whenever the user names amounts
    or wants more than one coin (e.g. "buy 0.01 BTC and 0.1 ETH", "split cash into BTC and ETH").
    """
    return requests.post(
        f"{BASE}/paper/buy",
        json={"qty": round(float(qty), 8), "ticker": ticker},
    ).json()


@mcp.tool()
def buy_max_trade(ticker: str):
    """
    Spend ~95% of cash on ONE coin only. Use ONLY when the user explicitly wants max
    for a single ticker ('max', 'all in', 'fill portfolio', 'as much as possible').
    NEVER use for multi-coin buys — that empties cash on the first coin.
    """
    return requests.post(f"{BASE}/paper/buy-max", json={"ticker": ticker}).json()


@mcp.tool()
def sell_trade(qty: float, ticker: str):
    """
    Sell a specific qty of one coin. ticker = BTC / ETH / XRP (not BTCUSD).
    For multiple coins, call once per coin with that coin's qty.
    """
    return requests.post(
        f"{BASE}/paper/sell",
        json={"qty": round(float(qty), 8), "ticker": ticker},
    ).json()


@mcp.tool()
def set_exits(
    ticker: str,
    stop_loss: float | None = None,
    take_profit: float | None = None,
    qty: float | None = None,
):
    """
    Set stop-loss and/or take-profit for a coin you hold.
    When price hits either level, the app auto market-sells and clears both.
    Omit qty to sell the full position on trigger. Replaces any existing rule for this ticker.
    Example after a buy: set_exits("BTC", stop_loss=90000, take_profit=110000)
    """
    body: dict = {"ticker": ticker}
    if stop_loss is not None:
        body["stop_loss"] = float(stop_loss)
    if take_profit is not None:
        body["take_profit"] = float(take_profit)
    if qty is not None:
        body["qty"] = round(float(qty), 8)
    return requests.post(f"{BASE}/paper/exits", json=body).json()


@mcp.tool()
def list_exits() -> str:
    """List active stop-loss / take-profit rules."""
    return str(requests.get(f"{BASE}/paper/exits").json())


@mcp.tool()
def cancel_exits(ticker: str):
    """Cancel stop-loss / take-profit for a ticker (e.g. cancel_exits("BTC"))."""
    return requests.delete(f"{BASE}/paper/exits/{ticker}").json()


if __name__ == "__main__":
    mcp.run(transport="stdio")
