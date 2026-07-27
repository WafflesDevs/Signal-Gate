"""
Store for SL/TP exit rules.

Primary: Supabase `exit_rules` (required on Render / production — survives
ephemeral disk). Fallback: local `data/exit_rules.json` only when Supabase
env is not configured (local-only / offline), never on Render.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("signal_gate.exits.store")

ROOT = Path(__file__).resolve().parents[2]
STORE_PATH = ROOT / "data" / "exit_rules.json"
TABLE = "exit_rules"

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
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        # Keep API payload stable for callers that ignore updated_at
        if d.get("updated_at") is None:
            d.pop("updated_at", None)
        return d

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
            updated_at=str(data["updated_at"]) if data.get("updated_at") else None,
        )


def _on_render() -> bool:
    return bool(os.getenv("RENDER"))


def _supabase_configured() -> bool:
    return bool(
        (os.getenv("SUPABASE_URL") or "").strip()
        and (
            (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
            or (os.getenv("SUPABASE_ANON_KEY") or "").strip()
        )
    )


def _use_supabase() -> bool:
    """Production/Render must use Supabase; local may fall back to JSON."""
    if _on_render() or (os.getenv("ENVIRONMENT") or "").strip().lower() == "production":
        if not _supabase_configured():
            raise RuntimeError(
                "Exit rules require Supabase on Render/production "
                "(set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)"
            )
        return True
    return _supabase_configured()


def _empty() -> dict[str, ExitRule]:
    return {}


def _rule_key(user_id: Optional[str], ticker: str) -> str:
    uid = (user_id or "_anon").strip()
    return f"{uid}:{ticker.strip().upper()}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_rule(row: dict) -> ExitRule:
    return ExitRule.from_dict(row)


# ---------------------------------------------------------------------------
# JSON fallback (local only)
# ---------------------------------------------------------------------------


def _load_json() -> dict[str, ExitRule]:
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


def _save_json(rules: dict[str, ExitRule]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = [r.to_dict() for r in rules.values()]
    STORE_PATH.write_text(json.dumps(payload, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------


def _sb():
    from app.core.supabase_client import get_supabase

    return get_supabase()


def _list_supabase(user_id: Optional[str] = None) -> list[ExitRule]:
    q = _sb().table(TABLE).select(
        "id,user_id,ticker,qty,stop_loss,take_profit,created_at,updated_at"
    )
    if user_id is not None:
        q = q.eq("user_id", user_id)
    res = q.execute()
    return [_row_to_rule(row) for row in (res.data or [])]


def _get_supabase(ticker: str, user_id: Optional[str]) -> Optional[ExitRule]:
    if not user_id:
        return None
    res = (
        _sb()
        .table(TABLE)
        .select("id,user_id,ticker,qty,stop_loss,take_profit,created_at,updated_at")
        .eq("user_id", user_id)
        .eq("ticker", ticker.strip().upper())
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    return _row_to_rule(res.data[0])


def _upsert_supabase(
    ticker: str,
    *,
    user_id: str,
    stop_loss: Optional[float],
    take_profit: Optional[float],
    qty: Optional[float],
) -> ExitRule:
    key_ticker = ticker.strip().upper()
    now = _now_iso()
    payload = {
        "user_id": user_id,
        "ticker": key_ticker,
        "qty": qty,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "updated_at": now,
    }
    # Upsert on unique (user_id, ticker). Omit id/created_at so inserts use
    # DB defaults and updates keep the original id/created_at.
    _sb().table(TABLE).upsert(payload, on_conflict="user_id,ticker").execute()
    rule = _get_supabase(key_ticker, user_id)
    if rule is None:
        # Extremely unlikely race; synthesize from payload for callers
        return ExitRule(
            id=str(uuid.uuid4()),
            ticker=key_ticker,
            qty=qty,
            stop_loss=stop_loss,
            take_profit=take_profit,
            created_at=now,
            user_id=user_id,
            updated_at=now,
        )
    return rule


def _delete_supabase(ticker: str, user_id: Optional[str]) -> Optional[ExitRule]:
    if not user_id:
        return None
    key = ticker.strip().upper()
    existing = _get_supabase(key, user_id)
    if existing is None:
        return None
    _sb().table(TABLE).delete().eq("user_id", user_id).eq("ticker", key).execute()
    return existing


def _delete_all_supabase(user_id: str) -> int:
    existing = _list_supabase(user_id=user_id)
    if not existing:
        return 0
    _sb().table(TABLE).delete().eq("user_id", user_id).execute()
    return len(existing)


# ---------------------------------------------------------------------------
# Public API (unchanged signatures for callers)
# ---------------------------------------------------------------------------


def list_rules(user_id: Optional[str] = None) -> list[ExitRule]:
    if _use_supabase():
        return _list_supabase(user_id=user_id)
    with _lock:
        rules = list(_load_json().values())
    if user_id is None:
        return rules
    return [r for r in rules if r.user_id == user_id]


def get_rule(ticker: str, user_id: Optional[str] = None) -> Optional[ExitRule]:
    if _use_supabase():
        return _get_supabase(ticker, user_id)
    key = _rule_key(user_id, ticker)
    with _lock:
        return _load_json().get(key)


def upsert_rule(
    ticker: str,
    *,
    user_id: Optional[str] = None,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    qty: Optional[float] = None,
) -> ExitRule:
    """Create or replace the single active rule for this user+ticker."""
    if _use_supabase():
        if not user_id:
            raise ValueError("user_id is required to persist exit rules in Supabase")
        return _upsert_supabase(
            ticker,
            user_id=user_id,
            stop_loss=stop_loss,
            take_profit=take_profit,
            qty=qty,
        )

    key_ticker = ticker.strip().upper()
    now = _now_iso()
    rule = ExitRule(
        id=str(uuid.uuid4()),
        ticker=key_ticker,
        qty=qty,
        stop_loss=stop_loss,
        take_profit=take_profit,
        created_at=now,
        user_id=user_id,
        updated_at=now,
    )
    with _lock:
        rules = _load_json()
        rules[_rule_key(user_id, key_ticker)] = rule
        _save_json(rules)
    return rule


def delete_rule(ticker: str, user_id: Optional[str] = None) -> Optional[ExitRule]:
    if _use_supabase():
        return _delete_supabase(ticker, user_id)
    key = _rule_key(user_id, ticker)
    with _lock:
        rules = _load_json()
        removed = rules.pop(key, None)
        if removed is not None:
            _save_json(rules)
        return removed


def delete_all_for_user(user_id: str) -> int:
    """Remove every exit rule owned by this user. Returns count deleted."""
    uid = (user_id or "").strip()
    if not uid:
        return 0
    if _use_supabase():
        return _delete_all_supabase(uid)
    with _lock:
        rules = _load_json()
        keep = {k: r for k, r in rules.items() if r.user_id != uid}
        removed = len(rules) - len(keep)
        if removed:
            _save_json(keep)
        return removed
