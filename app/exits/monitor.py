"""
Background SL/TP monitor.

Polls prices every few seconds. When stop-loss or take-profit hits,
places a market sell with that rule owner's Alpaca credentials and clears the rule.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import requests

from app.core.user_context import trading_user
from app.exits.store import ExitRule, delete_rule, list_rules

logger = logging.getLogger("signal_gate.exits")

POLL_SECONDS = 4.0


def should_trigger(price: float, rule: ExitRule) -> Optional[str]:
    """
    Return 'stop_loss', 'take_profit', or None.
    Long-only: SL fires when price <= stop; TP when price >= take_profit.
    """
    if rule.stop_loss is not None and price <= rule.stop_loss:
        return "stop_loss"
    if rule.take_profit is not None and price >= rule.take_profit:
        return "take_profit"
    return None


def fetch_spot_price(ticker: str) -> float:
    """Current USD spot from Coinbase (same source as /getprice)."""
    base = ticker.strip().upper()
    r = requests.get(
        f"https://api.coinbase.com/v2/prices/{base}-USD/spot",
        timeout=10,
    )
    r.raise_for_status()
    amount = r.json().get("data", {}).get("amount")
    if amount is None:
        raise ValueError(f"No price for {base}")
    return float(amount)


def _resolve_sell_qty(ticker: str, rule_qty: Optional[float], user_id: Optional[str]) -> Optional[float]:
    """How much to sell; None if no position."""
    from app.routers.paper import held_qty

    held = held_qty(ticker, user_id=user_id)
    if held <= 0:
        return None
    if rule_qty is None:
        return held
    return min(float(rule_qty), held)


def check_and_execute_rule(rule: ExitRule, price: Optional[float] = None) -> Optional[dict]:
    """
    Evaluate one rule. If triggered, market-sell with that user's Settings
    credentials and delete the rule. Never uses .env Alpaca keys.
    """
    from app.core.alpaca_credentials import load_credentials
    from app.routers.paper import market_sell

    if not rule.user_id:
        logger.warning(
            "exit monitor: clearing orphan rule %s (no user_id — env Alpaca unused)",
            rule.ticker,
        )
        delete_rule(rule.ticker, user_id=None)
        return None

    # Only fire for users who still have linked Settings credentials
    if load_credentials(rule.user_id) is None:
        logger.warning(
            "exit monitor: skipping %s for user %s — no linked Alpaca credentials",
            rule.ticker,
            rule.user_id,
        )
        return None

    try:
        with trading_user(rule.user_id):
            # Drop orphan rules left after a manual / agent sell (before price check)
            qty = _resolve_sell_qty(rule.ticker, rule.qty, rule.user_id)
            if qty is None or qty <= 0:
                logger.info(
                    "exit monitor: %s has no position — clearing stale rule",
                    rule.ticker,
                )
                delete_rule(rule.ticker, user_id=rule.user_id)
                return {
                    "ticker": rule.ticker,
                    "reason": "no_position",
                    "sold": False,
                    "detail": "cleared stale rule",
                }

            try:
                px = float(price) if price is not None else fetch_spot_price(rule.ticker)
            except Exception as e:
                logger.warning(
                    "exit monitor: price fetch failed for %s: %s", rule.ticker, e
                )
                return None

            reason = should_trigger(px, rule)
            if reason is None:
                return None

            order = market_sell(rule.ticker, qty, user_id=rule.user_id)
            delete_rule(rule.ticker, user_id=rule.user_id)
            logger.info(
                "exit monitor: %s %s triggered @ %s — sold %s (rule cleared)",
                rule.ticker,
                reason,
                px,
                qty,
            )
            return {
                "ticker": rule.ticker,
                "reason": reason,
                "price": px,
                "sold": True,
                "qty": qty,
                "order": order,
            }
    except Exception as e:
        logger.error(
            "exit monitor: sell failed for %s: %s",
            rule.ticker,
            e,
        )
        return None


async def _tick_once() -> None:
    rules = list_rules()
    if not rules:
        return
    # Run blocking I/O off the event loop
    loop = asyncio.get_running_loop()
    for rule in rules:
        try:
            await loop.run_in_executor(None, check_and_execute_rule, rule)
        except Exception as e:
            logger.error("exit monitor: unexpected error for %s: %s", rule.ticker, e)


async def monitor_loop(stop: asyncio.Event) -> None:
    """Poll forever until stop is set. Never crashes the app."""
    logger.info("exit monitor started (every %ss)", POLL_SECONDS)
    while not stop.is_set():
        try:
            await _tick_once()
        except Exception as e:
            logger.error("exit monitor: tick failed: %s", e)
        try:
            await asyncio.wait_for(stop.wait(), timeout=POLL_SECONDS)
        except asyncio.TimeoutError:
            pass
    logger.info("exit monitor stopped")
