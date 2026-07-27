"""Unit tests for Alpaca credential helpers + buy args (no network)."""

import os
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.agent.portfolio_tools import BuyArgs
from app.core.alpaca_client import (
    LINK_REQUIRED,
    TradingAuthError,
    get_trading_client,
    mode_prefix_hint,
    sanitize_credential,
)


def test_sanitize_strips_whitespace_and_zero_width():
    assert sanitize_credential("  PKTEST\u200b  ") == "PKTEST"
    assert sanitize_credential("\ufeffsecret\u00a0") == "secret"


def test_mode_prefix_hint_detects_mismatch():
    assert mode_prefix_hint("AKxxxxxxxx", True) is not None
    assert mode_prefix_hint("PKxxxxxxxx", False) is not None
    assert mode_prefix_hint("PKxxxxxxxx", True) is None
    assert mode_prefix_hint("AKxxxxxxxx", False) is None


def test_buy_args_requires_exactly_one_of_qty_or_notional():
    with pytest.raises(ValidationError):
        BuyArgs(ticker="XRP")
    with pytest.raises(ValidationError):
        BuyArgs(ticker="XRP", qty=10, notional_usd=10000)
    assert BuyArgs(ticker="XRP", notional_usd=10000).notional_usd == 10000
    assert BuyArgs(ticker="XRP", qty=10).qty == 10


def test_get_trading_client_never_uses_env_alpaca_keys():
    """Even if .env keys exist, trading requires linked user credentials."""
    env = {
        **os.environ,
        "ALPACA_API_KEY": "PK_FROM_ENV_SHOULD_NOT_BE_USED",
        "ALPACA_SECRET_KEY": "SECRET_FROM_ENV_SHOULD_NOT_BE_USED",
    }
    with patch.dict(os.environ, env, clear=False):
        with pytest.raises(TradingAuthError) as no_user:
            get_trading_client(None)
        assert "Login" in no_user.value.detail or "Login" in str(no_user.value)

        with patch(
            "app.core.alpaca_client.load_credentials", return_value=None
        ) as load:
            with pytest.raises(TradingAuthError) as unlinked:
                get_trading_client("user-123")
            load.assert_called_once_with("user-123")
            assert unlinked.value.detail == LINK_REQUIRED


def test_get_trading_client_builds_from_linked_creds():
    creds = MagicMock()
    creds.api_key_id = "PKUSER"
    creds.api_secret = "user-secret"
    creds.is_paper = True
    fake_client = object()

    with patch("app.core.alpaca_client.load_credentials", return_value=creds):
        with patch(
            "app.core.alpaca_client.build_trading_client", return_value=fake_client
        ) as build:
            client = get_trading_client("user-123")
            assert client is fake_client
            build.assert_called_once_with(creds)
