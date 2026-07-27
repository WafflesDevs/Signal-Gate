"""
JSON-backed store for SL/TP exit rules.

One active rule per ticker (base symbol, e.g. BTC). Setting again replaces it.
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
        )


def _empty() -> dict[str, ExitRule]:
    return {}


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
        rules[rule.ticker] = rule
    return rules


def _save(rules: dict[str, ExitRule]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = [r.to_dict() for r in rules.values()]
    STORE_PATH.write_text(json.dumps(payload, indent=2) + "\n")


def list_rules() -> list[ExitRule]:
    with _lock:
        return list(_load().values())


def get_rule(ticker: str) -> Optional[ExitRule]:
    key = ticker.strip().upper()
    with _lock:
        return _load().get(key)


def upsert_rule(
    ticker: str,
    *,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    qty: Optional[float] = None,
) -> ExitRule:
    """Create or replace the single active rule for this ticker."""
    key = ticker.strip().upper()
    rule = ExitRule(
        id=str(uuid.uuid4()),
        ticker=key,
        qty=qty,
        stop_loss=stop_loss,
        take_profit=take_profit,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    with _lock:
        rules = _load()
        rules[key] = rule
        _save(rules)
    return rule


def delete_rule(ticker: str) -> Optional[ExitRule]:
    key = ticker.strip().upper()
    with _lock:
        rules = _load()
        removed = rules.pop(key, None)
        if removed is not None:
            _save(rules)
        return removed
