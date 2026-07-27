"""
Paper / live trading routes (user's linked Alpaca account).

  GET  /paper/account
  GET  /paper/positions
  GET  /paper/active-trades   positions + SL/TP exit rules (desk panel)
  POST /paper/buy        { "qty": 0.01, "ticker": "ETH" }
                         OR { "notional_usd": 10000, "ticker": "XRP" }
  POST /paper/buy-max    { "ticker": "XRP" }   ← spend most cash
  POST /paper/sell       { "qty": 0.5, "ticker": "BTC" }
  POST /paper/exits      { "ticker": "BTC", "stop_loss": 90000, "take_profit": 110000 }
  GET  /paper/exits
  DELETE /paper/exits/{ticker}

All routes require auth. Trades use that user's Settings credentials
(Paper or Live based on is_paper). Never fall back to .env Alpaca keys.
"""

from typing import Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from app.core.alpaca_client import TradingAuthError, get_trading_client
from app.core.alpaca_credentials import load_credentials
from app.core.auth import AuthUser, get_current_user
from app.core.user_context import trading_user
from app.exits import store as exit_store

router = APIRouter(prefix="/paper", tags=["paper"])


def _raise_http(exc: Exception) -> None:
    """Convert domain trading errors to HTTP; re-raise HTTP as-is."""
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, TradingAuthError):
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    raise HTTPException(status_code=400, detail=str(exc)) from exc


class TradeBody(BaseModel):
    """Buy: exactly one of qty (coins) or notional_usd (dollars). Sell: qty required."""

    ticker: str
    qty: Optional[float] = Field(default=None, gt=0)
    notional_usd: Optional[float] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def need_qty_or_notional(self):
        has_qty = self.qty is not None
        has_notional = self.notional_usd is not None
        if has_qty == has_notional:
            raise ValueError("Provide exactly one of qty or notional_usd")
        return self


class SellBody(BaseModel):
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


def _mode_label(user_id: str) -> str:
    creds = load_credentials(user_id)
    if creds is None:
        return "Paper"
    return "Paper" if creds.is_paper else "Live"


def held_qty(ticker: str, user_id: Optional[str] = None) -> float:
    """How many units of this coin we hold (0 if none)."""
    symbol = to_symbol(ticker)
    target = symbol.replace("/", "")
    client = get_trading_client(user_id)
    for p in client.get_all_positions():
        if str(p.symbol).replace("/", "").upper() == target:
            return float(p.qty)
    return 0.0


def market_sell(ticker: str, qty: float, user_id: Optional[str] = None) -> dict:
    """Submit a market sell. Used by /paper/sell and the exit monitor."""
    symbol = to_symbol(ticker)
    qty = round(float(qty), 8)
    held = held_qty(ticker, user_id=user_id)
    if held <= 0:
        coin = base_ticker(ticker)
        raise ValueError(f"You don't hold any {coin} to sell.")

    qty = round(min(qty, held), 8)
    order = get_trading_client(user_id).submit_order(
        MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=OrderSide.SELL,
            time_in_force=TimeInForce.GTC,
        )
    )
    # Full close → drop SL/TP so a later rebuy doesn't inherit phantom exits
    remaining = held - qty
    if remaining <= _POSITION_DUST_QTY:
        exit_store.delete_rule(base_ticker(ticker), user_id=user_id)
    label = _mode_label(user_id) if user_id else "Trade"
    return {
        "message": f"{label} sell submitted",
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


def _account_payload(user_id: str) -> dict:
    account = get_trading_client(user_id).get_account()
    creds = load_credentials(user_id)
    is_paper = True if creds is None else bool(creds.is_paper)
    return {
        "cash": account.cash,
        "equity": account.equity,
        "buying_power": account.buying_power,
        "status": account.status,
        "paper": is_paper,
    }


def _num(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# Alpaca crypto often leaves closed/dust rows (qty 0 or ~1e-8) after sells.
_POSITION_DUST_QTY = 1e-8
_POSITION_DUST_VALUE_USD = 0.01


def _is_open_position(row: dict) -> bool:
    """True when the position has meaningful size (not closed / crypto dust)."""
    qty = abs(_num(row.get("qty")) or 0.0)
    qty_available = abs(_num(row.get("qty_available")) or 0.0)
    held = max(qty, qty_available)
    if held <= _POSITION_DUST_QTY:
        return False
    mv = _num(row.get("market_value"))
    if mv is not None and abs(mv) < _POSITION_DUST_VALUE_USD:
        return False
    return True


def _positions_payload(user_id: str) -> list[dict]:
    rows = []
    for p in get_trading_client(user_id).get_all_positions():
        symbol = to_symbol(p.symbol)
        rows.append(
            {
                "symbol": symbol,
                "ticker": symbol.split("/")[0],
                "qty": _num(p.qty) or 0.0,
                "qty_available": _num(getattr(p, "qty_available", None)),
                "avg_entry_price": _num(p.avg_entry_price),
                "current_price": _num(p.current_price),
                "unrealized_pl": _num(p.unrealized_pl),
                "unrealized_plpc": _num(getattr(p, "unrealized_plpc", None)),
                "market_value": _num(getattr(p, "market_value", None)),
            }
        )
    return rows


def _with_live_mark(row: dict) -> dict:
    """
    Overlay a live Coinbase spot on Alpaca's position snapshot.

    Alpaca crypto `current_price` / unrealized P/L often lag (or stick), so the
    desk panel would look frozen even while the poll loop is healthy.
    """
    ticker = str(row.get("ticker") or "")
    qty = _num(row.get("qty")) or 0.0
    avg = _num(row.get("avg_entry_price"))
    out = dict(row)
    try:
        live = _current_price(ticker)
    except Exception:
        return out

    out["current_price"] = live
    out["market_value"] = live * qty if qty else out.get("market_value")
    if avg is not None and qty:
        pl = (live - avg) * qty
        out["unrealized_pl"] = pl
        out["unrealized_plpc"] = (live - avg) / avg if avg else None
    return out


def _active_trades_payload(user_id: str) -> dict:
    """Open positions merged with this user's active SL/TP exit rules."""
    positions = [
        p
        for p in (_with_live_mark(row) for row in _positions_payload(user_id))
        if _is_open_position(p)
    ]
    rules = {
        r.ticker.upper(): r.to_dict()
        for r in exit_store.list_rules(user_id=user_id)
    }
    trades = []
    for p in positions:
        ticker = str(p["ticker"]).upper()
        rule = rules.get(ticker)
        sl = rule.get("stop_loss") if rule else None
        tp = rule.get("take_profit") if rule else None
        has_exit = sl is not None or tp is not None
        trades.append(
            {
                **p,
                "stop_loss": sl if has_exit else None,
                "take_profit": tp if has_exit else None,
                "exit_qty": rule.get("qty") if rule and has_exit else None,
                "has_exit": has_exit,
            }
        )
    creds = load_credentials(user_id)
    is_paper = True if creds is None else bool(creds.is_paper)
    return {
        "trades": trades,
        "count": len(trades),
        "paper": is_paper,
    }


def account_summary(user_id: str) -> dict:
    """In-process helper for agent tools."""
    with trading_user(user_id):
        return _account_payload(user_id)


def positions_summary(user_id: str) -> list[dict]:
    with trading_user(user_id):
        return _positions_payload(user_id)


def execute_buy(user_id: str, qty: float, ticker: str) -> dict:
    """Market buy a fixed coin quantity."""
    with trading_user(user_id):
        symbol = to_symbol(ticker)
        qty = round(float(qty), 8)
        order = get_trading_client(user_id).submit_order(
            MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.GTC,
            )
        )
        label = _mode_label(user_id)
        return {
            "message": f"{label} buy submitted",
            "symbol": symbol,
            "qty": qty,
            "side": "buy",
            "order_id": str(order.id),
            "status": str(order.status),
        }


def execute_buy_notional(user_id: str, notional_usd: float, ticker: str) -> dict:
    """
    Market buy spending a fixed USD amount (Alpaca notional order).
    Use for "$10k worth of XRP" — do not convert to qty yourself.
    """
    with trading_user(user_id):
        symbol = to_symbol(ticker)
        dollars = round(float(notional_usd), 2)
        if dollars < 1:
            raise ValueError("notional_usd must be at least $1")
        cash = float(get_trading_client(user_id).get_account().cash)
        if dollars > cash:
            raise ValueError(
                f"Not enough cash: need ${dollars:.2f}, have ${cash:.2f}."
            )
        order = get_trading_client(user_id).submit_order(
            MarketOrderRequest(
                symbol=symbol,
                notional=dollars,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.GTC,
            )
        )
        label = _mode_label(user_id)
        return {
            "message": f"{label} notional buy submitted",
            "symbol": symbol,
            "notional_usd": dollars,
            "side": "buy",
            "order_id": str(order.id),
            "status": str(order.status),
        }


def execute_buy_max(user_id: str, ticker: str) -> dict:
    with trading_user(user_id):
        symbol = to_symbol(ticker)
        cash = float(get_trading_client(user_id).get_account().cash)
        if cash < 1:
            raise ValueError("Not enough cash to buy.")
        dollars = round(cash * 0.95, 2)
        order = get_trading_client(user_id).submit_order(
            MarketOrderRequest(
                symbol=symbol,
                notional=dollars,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.GTC,
            )
        )
        label = _mode_label(user_id)
        return {
            "message": f"{label} buy-max submitted",
            "symbol": symbol,
            "notional_usd": dollars,
            "side": "buy",
            "order_id": str(order.id),
            "status": str(order.status),
        }


def execute_sell(user_id: str, qty: float, ticker: str) -> dict:
    with trading_user(user_id):
        return market_sell(ticker, qty, user_id=user_id)


@router.get("/account", status_code=status.HTTP_200_OK)
def get_account(user: AuthUser = Depends(get_current_user)):
    """Cash + portfolio value."""
    try:
        with trading_user(user.id):
            return _account_payload(user.id)
    except TradingAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/positions", status_code=status.HTTP_200_OK)
def get_positions(user: AuthUser = Depends(get_current_user)):
    """What coins you currently hold."""
    try:
        with trading_user(user.id):
            return _positions_payload(user.id)
    except TradingAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/active-trades", status_code=status.HTTP_200_OK)
def get_active_trades(user: AuthUser = Depends(get_current_user)):
    """
    Desk snapshot: open Alpaca positions + any SL/TP exit rules for this user.
    Used by the Chat Active trades panel (poll while desk is open).
    """
    try:
        with trading_user(user.id):
            return _active_trades_payload(user.id)
    except TradingAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/buy", status_code=status.HTTP_200_OK)
def buy(body: TradeBody, user: AuthUser = Depends(get_current_user)):
    """Buy by coin qty or by USD notional (exactly one)."""
    try:
        if body.notional_usd is not None:
            return execute_buy_notional(user.id, body.notional_usd, body.ticker)
        return execute_buy(user.id, float(body.qty), body.ticker)
    except Exception as e:
        _raise_http(e)


@router.post("/buy-max", status_code=status.HTTP_200_OK)
def buy_max(body: TickerBody, user: AuthUser = Depends(get_current_user)):
    """Spend ~95% of cash on one coin (Alpaca picks the qty)."""
    try:
        return execute_buy_max(user.id, body.ticker)
    except Exception as e:
        _raise_http(e)


@router.post("/sell", status_code=status.HTTP_200_OK)
def sell(body: SellBody, user: AuthUser = Depends(get_current_user)):
    """Sell a coin you hold (won't sell more than you have)."""
    try:
        return execute_sell(user.id, body.qty, body.ticker)
    except Exception as e:
        _raise_http(e)


@router.get("/exits", status_code=status.HTTP_200_OK)
def list_exits(user: AuthUser = Depends(get_current_user)):
    """Active stop-loss / take-profit rules for this user."""
    return [r.to_dict() for r in exit_store.list_rules(user_id=user.id)]


@router.post("/exits", status_code=status.HTTP_200_OK)
def set_exits(body: ExitBody, user: AuthUser = Depends(get_current_user)):
    """
    Set SL and/or TP for a ticker you hold.
    One rule per ticker — a new set replaces the old one.
    qty omitted = sell entire position when triggered.
    """
    ticker = base_ticker(body.ticker)
    try:
        with trading_user(user.id):
            held = held_qty(ticker, user_id=user.id)
    except TradingAuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
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
        user_id=user.id,
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
def cancel_exits(ticker: str, user: AuthUser = Depends(get_current_user)):
    """
    Cancel SL/TP for a ticker.

    Idempotent: missing rule is success (used when approving Investment /
    buys without exits so stale Short-term rules cannot linger).
    """
    key = base_ticker(ticker)
    removed = exit_store.delete_rule(key, user_id=user.id)
    if removed is None:
        return {"message": "No exit rule to cancel", "ticker": key, "rule": None}
    return {"message": "Exit rule cancelled", "rule": removed.to_dict()}
