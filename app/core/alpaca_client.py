import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()


def get_trading_client() -> TradingClient:
    """Paper trading client. Keys come from .env — never hardcode them."""
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")

    if not api_key or not secret_key:
        raise RuntimeError("Missing ALPACA_API_KEY or ALPACA_SECRET_KEY in .env")

    return TradingClient(
        api_key=api_key,
        secret_key=secret_key,
        paper=True,
    )
