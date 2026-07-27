"""
Paper trading routes (fake money via Alpaca).

  GET  /paper/account
  GET  /paper/positions
  POST /paper/buy        { "qty": 0.01, "ticker": "ETH" }
  POST /paper/buy-max    { "ticker": "XRP" }   ← spend most cash
  POST /paper/sell       { "qty": 0.5, "ticker": "BTC" }
  POST /paper/exits      { "ticker": "BTC", "stop_loss": 90000, "take_profit": 110000 }
  GET  /paper/exits
  DELETE /paper/exits/{ticker}
"""

from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from app.core.alpaca_client import get_trading_client
from app.exits import store as exit_store

router = APIRouter(prefix="/paper", tags=["paper"])


class TradeBody(BaseModel):
    qty: float = Field(gt=0)
    ticker: str


class TickerBody(BaseModel):
    ticker: str


class ExitBody(BaseModel):
    ticker: str
    stop_loss: Optional[float] = Field(default=None, gt=0)
    take_profit: Optional[float] = Field(default=None, gt=0)
    qty: Optional[float] = Field(default=None, gt=0)  # omit = sell all on trigger

    @model_validator(mode="after")
    def need_at_least_one_exit(self):
        if self.stop_loss is None and self.take_profit is None:
            raise ValueError("Provide stop_loss and/or take_profit")
        if (
            self.stop_loss is not None
            and self.take_profit is not None
            and self.stop_loss >= self.take_profit
        ):
            raise ValueError("stop_loss must be below take_profit")
        return self


def to_symbol(ticker: str) -> str:
    """Turn ETH / ETHUSD / ETH-USD into ETH/USD for Alpaca."""
    t = ticker.strip().upper().replace("-", "/")
    if "/" in t:
        return t
    if t.endswith("USD") and len(t) > 3:
        return t[:-3] + "/USD"  # BTCUSD → BTC/USD
    return t + "/USD"


def base_ticker(ticker: str) -> str:
    """ETH / ETHUSD / ETH/USD → ETH"""
    return to_symbol(ticker).split("/")[0]


def held_qty(ticker: str) -> float:
    """How many units of this coin we hold (0 if none)."""
    symbol = to_symbol(ticker)
    target = symbol.replace("/", "")
    client = get_trading_client()
    for p in client.get_all_positions():
        if str(p.symbol).replace("/", "").upper() == target:
            return float(p.qty)
    return 0.0


def market_sell(ticker: str, qty: float) -> dict:
    """Submit a paper market sell. Used by /paper/sell and the exit monitor."""
    symbol = to_symbol(ticker)
    qty = round(float(qty), 8)
    held = held_qty(ticker)
    if held <= 0:
        coin = base_ticker(ticker)
        raise ValueError(f"You don't hold any {coin} to sell.")

    qty = round(min(qty, held), 8)
    order = get_trading_client().submit_order(
        MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.GTC,
        )
    )
    return {
        "message": "Paper sell submitted",
        "symbol": symbol,
        "qty": qty,
        "side": "sell",
        "order_id": str(order.id),
        "status": str(order.status),
    }


def _current_price(ticker: str) -> float:
    base = base_ticker(ticker)
    r = requests.get(
        f"https://api.coinbase.com/v2/prices/{base}-USD/spot",
        timeout=10,
    )
    r.raise_for_status()
    amount = r.json().get("data", {}).get("amount")
    if amount is None:
        raise ValueError(f"No price for {base}")
    return float(amount)


@router.get("/account", status_code=status.HTTP_200_OK)
def get_account():
    """Cash + portfolio value."""
    try:
        account = get_trading_client().get_account()
        return {
            "cash": account.cash,
            "equity": account.equity,
            "buying_power": account.buying_power,
            "status": account.status,
            "paper": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions", status_code=status.HTTP_200_OK)
def get_positions():
    """What coins you currently hold."""
    try:
        rows = []
        for p in get_trading_client().get_all_positions():
            symbol = to_symbol(p.symbol)
            rows.append(
                {
                    "symbol": symbol,
                    "ticker": symbol.split("/")[0],
                    "qty": p.qty,
                    "avg_entry_price": p.avg_entry_price,
                    "current_price": p.current_price,
                    "unrealized_pl": p.unrealized_pl,
                }
            )
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/buy", status_code=status.HTTP_200_OK)
def buy(body: TradeBody):
    """Buy a specific amount of a coin."""
    symbol = to_symbol(body.ticker)
    qty = round(float(body.qty), 8)
    try:
        order = get_trading_client().submit_order(
            MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.GTC,
            )
        )
        return {
            "message": "Paper buy submitted",
            "symbol": symbol,
            "qty": qty,
            "side": "buy",
            "order_id": str(order.id),
            "status": str(order.status),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/buy-max", status_code=status.HTTP_200_OK)
def buy_max(body: TickerBody):
    """Spend ~95% of cash on one coin (Alpaca picks the qty)."""
    symbol = to_symbol(body.ticker)
    try:
        cash = float(get_trading_client().get_account().cash)
        if cash < 1:
            raise HTTPException(status_code=400, detail="Not enough cash to buy.")

        dollars = round(cash * 0.95, 2)
        order = get_trading_client().submit_order(
            MarketOrderRequest(
                symbol=symbol,
                notional=dollars,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.GTC,
            )
        )
        return {
            "message": "Paper buy-max submitted",
            "symbol": symbol,
            "notional_usd": dollars,
            "side": "buy",
            "order_id": str(order.id),
            "status": str(order.status),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sell", status_code=status.HTTP_200_OK)
def sell(body: TradeBody):
    """Sell a coin you hold (won't sell more than you have)."""
    try:
        return market_sell(body.ticker, body.qty)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/exits", status_code=status.HTTP_200_OK)
def list_exits():
    """Active stop-loss / take-profit rules."""
    return [r.to_dict() for r in exit_store.list_rules()]


@router.post("/exits", status_code=status.HTTP_200_OK)
def set_exits(body: ExitBody):
    """
    Set SL and/or TP for a ticker you hold.
    One rule per ticker — a new set replaces the old one.
    qty omitted = sell entire position when triggered.
    """
    ticker = base_ticker(body.ticker)
    held = held_qty(ticker)
    if held <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"You don't hold any {ticker}. Buy first, then set exits.",
        )

    if body.qty is not None and body.qty > held:
        raise HTTPException(
            status_code=400,
            detail=f"qty {body.qty} exceeds holdings ({held}).",
        )

    try:
        price = _current_price(ticker)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not fetch price: {e}")

    if body.stop_loss is not None and body.stop_loss >= price:
        raise HTTPException(
            status_code=400,
            detail=f"stop_loss ({body.stop_loss}) must be below current price ({price}).",
        )
    if body.take_profit is not None and body.take_profit <= price:
        raise HTTPException(
            status_code=400,
            detail=f"take_profit ({body.take_profit}) must be above current price ({price}).",
        )

    rule = exit_store.upsert_rule(
        ticker,
        stop_loss=body.stop_loss,
        take_profit=body.take_profit,
        qty=body.qty,
    )
    return {
        "message": "Exit rule set (replaces any previous rule for this ticker)",
        "current_price": price,
        "rule": rule.to_dict(),
    }


@router.delete("/exits/{ticker}", status_code=status.HTTP_200_OK)
def cancel_exits(ticker: str):
    """Cancel SL/TP for a ticker."""
    key = base_ticker(ticker)
    removed = exit_store.delete_rule(key)
    if removed is None:
        raise HTTPException(status_code=404, detail=f"No exit rule for {key}")
    return {"message": "Exit rule cancelled", "rule": removed.to_dict()}
