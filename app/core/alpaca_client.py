"""
Alpaca TradingClient factory.

Trading/portfolio ALWAYS use the logged-in user's keys from Settings
(encrypted in Supabase). Never reads ALPACA_API_KEY / ALPACA_SECRET_KEY
from .env — those env vars are unused for trades.
"""

from __future__ import annotations

import re
from typing import Optional

from alpaca.trading.client import TradingClient

from app.core.alpaca_credentials import AlpacaCredentials, load_credentials
from app.core.user_context import get_current_user_id


LINK_REQUIRED = "Link your Alpaca account in Settings"
FERNET_KEY_REQUIRED = (
    "Server is missing CREDENTIALS_FERNET_KEY — set it in Render Environment, "
    "then re-link Alpaca in Settings."
)
FERNET_DECRYPT_FAILED = (
    "Could not decrypt stored Alpaca credentials — set CREDENTIALS_FERNET_KEY "
    "on the server (same key used when linking), then re-link Alpaca in Settings."
)
INCOMPLETE_CREDS = (
    "Linked Alpaca credentials are incomplete or empty. Re-link Alpaca in Settings."
)


class TradingAuthError(Exception):
    """Raised when trading cannot proceed (no user / no linked Alpaca)."""

    def __init__(self, detail: str, *, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


# Zero-width / BOM chars that password managers and paste often inject.
_INVISIBLE = re.compile(r"[\u200b-\u200d\ufeff\u00a0]")


def sanitize_credential(value: str) -> str:
    """Strip whitespace and common invisible paste characters. Never log the result."""
    return _INVISIBLE.sub("", (value or "").strip())


def mode_prefix_hint(api_key_id: str, is_paper: bool) -> Optional[str]:
    """
    Alpaca Paper keys typically start with PK; Live with AK.
    Return a user-facing hint if Mode likely mismatches the key id prefix.
    """
    key = sanitize_credential(api_key_id).upper()
    if key.startswith("AK") and is_paper:
        return (
            "This Key ID looks like a Live key (starts with AK), but Mode is Paper. "
            "Switch Mode to Live, or paste keys from the Paper dashboard."
        )
    if key.startswith("PK") and not is_paper:
        return (
            "This Key ID looks like a Paper key (starts with PK), but Mode is Live. "
            "Switch Mode to Paper, or paste keys from the Live dashboard."
        )
    return None


def is_alpaca_unauthorized(exc: BaseException) -> bool:
    """True when Alpaca (or a wrapped body) reports unauthorized / 401."""
    status_code = getattr(exc, "status_code", None)
    try:
        if status_code is not None and int(status_code) == 401:
            return True
    except (TypeError, ValueError):
        pass
    text = str(exc).lower()
    return "unauthorized" in text


def alpaca_auth_error_detail(is_paper: bool, exc: BaseException) -> str:
    """User-facing message for failed Settings link / test. Never includes secrets."""
    mode = "Paper" if is_paper else "Live"
    unauthorized = is_alpaca_unauthorized(exc)

    if unauthorized:
        return (
            f"Incorrect Alpaca keys — they do not work for {mode}. "
            f"Generate a fresh Key + Secret pair from the {mode} dashboard "
            "(Paper ≠ Live) and try again."
        )
    return (
        f"Incorrect Alpaca keys — could not load the {mode} portfolio. "
        "Check Key ID, Secret, and Mode, then try again."
    )


def friendly_trading_error(
    exc: BaseException, *, is_paper: bool = True
) -> Optional[str]:
    """
    Map decrypt / empty-key / Alpaca unauthorized failures to a clear string.
    Returns None when the exception is not a known credentials problem.
    """
    if isinstance(exc, TradingAuthError):
        return exc.detail

    text = str(exc)
    lower = text.lower()
    if "missing credentials_fernet_key" in lower:
        return FERNET_KEY_REQUIRED
    if "could not decrypt" in lower or "credentials_fernet_key" in lower:
        return FERNET_DECRYPT_FAILED
    if is_alpaca_unauthorized(exc):
        return alpaca_auth_error_detail(is_paper, exc)
    return None


def build_trading_client(creds: AlpacaCredentials) -> TradingClient:
    key = sanitize_credential(creds.api_key_id)
    secret = sanitize_credential(creds.api_secret)
    if not key or not secret:
        raise TradingAuthError(INCOMPLETE_CREDS, status_code=400)
    return TradingClient(
        api_key=key,
        secret_key=secret,
        paper=bool(creds.is_paper),
    )


def validate_credentials(api_key_id: str, api_secret: str, is_paper: bool) -> dict:
    """
    Prove keys work by loading portfolio data before Settings may save them.

    Calls Trading API GET /v2/account (and GET /v2/positions) with the submitted
    key + secret. Paper → https://paper-api.alpaca.markets ;
    Live → https://api.alpaca.markets. Auth headers via alpaca-py:
    APCA-API-KEY-ID / APCA-API-SECRET-KEY. Never uses .env Alpaca keys.
    """
    key_id = sanitize_credential(api_key_id)
    secret = sanitize_credential(api_secret)
    if not key_id or not secret:
        raise ValueError("API Key ID and Secret Key are required")

    hint = mode_prefix_hint(key_id, is_paper)
    if hint:
        raise ValueError(hint)

    client = TradingClient(
        api_key=key_id,
        secret_key=secret,
        paper=bool(is_paper),
    )
    # Portfolio gate: account must succeed; positions confirms trading access
    # (empty list is fine — means linked but flat).
    account = client.get_account()
    positions = client.get_all_positions()
    if account is None or getattr(account, "id", None) is None:
        raise ValueError(
            f"Incorrect Alpaca keys — could not load the "
            f"{'Paper' if is_paper else 'Live'} portfolio."
        )
    return {
        "status": str(account.status),
        "cash": str(account.cash),
        "equity": str(account.equity),
        "positions": len(positions or []),
        "paper": bool(is_paper),
    }


def get_trading_client(user_id: Optional[str] = None) -> TradingClient:
    """
    Trading client for a Settings-linked user.

    Resolves user_id from argument, then contextvar (chat / paper routes).
    Raises TradingAuthError if no user or that user has not linked Alpaca.
    Never falls back to project .env Alpaca keys.
    """
    uid = (user_id or get_current_user_id() or "").strip() or None
    if not uid:
        raise TradingAuthError("Login required to trade", status_code=401)

    try:
        creds = load_credentials(uid)
    except RuntimeError as e:
        mapped = friendly_trading_error(e)
        raise TradingAuthError(
            mapped or FERNET_DECRYPT_FAILED,
            status_code=500,
        ) from e

    if creds is None:
        raise TradingAuthError(LINK_REQUIRED, status_code=400)

    return build_trading_client(creds)
