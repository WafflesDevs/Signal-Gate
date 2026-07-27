"""
JSON-backed store for SL/TP exit rules.

One active rule per (user_id, ticker). Setting again replaces it.
Survives restarts via data/exit_rules.json.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
STORE_PATH = ROOT / "data" / "exit_rules.json"

_lock = threading.Lock()


@dataclass
class ExitRule:
    id: str
    ticker: str  # base, e.g. BTC
    qty: Optional[float]  # None = sell all holdings when triggered
    stop_loss: Optional[float]
    take_profit: Optional[float]
    created_at: str
    user_id: Optional[str] = None  # owner — required for multi-user sells

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ExitRule":
        return cls(
            id=str(data["id"]),
            ticker=str(data["ticker"]).upper(),
            qty=float(data["qty"]) if data.get("qty") is not None else None,
            stop_loss=float(data["stop_loss"]) if data.get("stop_loss") is not None else None,
            take_profit=float(data["take_profit"]) if data.get("take_profit") is not None else None,
            created_at=str(data.get("created_at") or ""),
            user_id=str(data["user_id"]) if data.get("user_id") else None,
        )


def _empty() -> dict[str, ExitRule]:
    return {}


def _rule_key(user_id: Optional[str], ticker: str) -> str:
    uid = (user_id or "_anon").strip()
    return f"{uid}:{ticker.strip().upper()}"


def _load() -> dict[str, ExitRule]:
    if not STORE_PATH.exists():
        return _empty()
    try:
        raw = json.loads(STORE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return _empty()
    if not isinstance(raw, list):
        return _empty()
    rules: dict[str, ExitRule] = {}
    for item in raw:
        if not isinstance(item, dict) or "ticker" not in item:
            continue
        rule = ExitRule.from_dict(item)
        rules[_rule_key(rule.user_id, rule.ticker)] = rule
    return rules


def _save(rules: dict[str, ExitRule]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = [r.to_dict() for r in rules.values()]
    STORE_PATH.write_text(json.dumps(payload, indent=2) + "\n")


def list_rules(user_id: Optional[str] = None) -> list[ExitRule]:
    with _lock:
        rules = list(_load().values())
    if user_id is None:
        return rules
    return [r for r in rules if r.user_id == user_id]


def get_rule(ticker: str, user_id: Optional[str] = None) -> Optional[ExitRule]:
    key = _rule_key(user_id, ticker)
    with _lock:
        return _load().get(key)


def upsert_rule(
    ticker: str,
    *,
    user_id: Optional[str] = None,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    qty: Optional[float] = None,
) -> ExitRule:
    """Create or replace the single active rule for this user+ticker."""
    key_ticker = ticker.strip().upper()
    rule = ExitRule(
        id=str(uuid.uuid4()),
        ticker=key_ticker,
        qty=qty,
        stop_loss=stop_loss,
        take_profit=take_profit,
        created_at=datetime.now(timezone.utc).isoformat(),
        user_id=user_id,
    )
    with _lock:
        rules = _load()
        rules[_rule_key(user_id, key_ticker)] = rule
        _save(rules)
    return rule


def delete_rule(ticker: str, user_id: Optional[str] = None) -> Optional[ExitRule]:
    key = _rule_key(user_id, ticker)
    with _lock:
        rules = _load()
        removed = rules.pop(key, None)
        if removed is not None:
            _save(rules)
        return removed


def delete_all_for_user(user_id: str) -> int:
    """Remove every exit rule owned by this user. Returns count deleted."""
    uid = (user_id or "").strip()
    if not uid:
        return 0
    with _lock:
        rules = _load()
        keep = {k: r for k, r in rules.items() if r.user_id != uid}
        removed = len(rules) - len(keep)
        if removed:
            _save(keep)
        return removed
