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


def test_get_trading_client_maps_fernet_decrypt_failure():
    with patch(
        "app.core.alpaca_client.load_credentials",
        side_effect=RuntimeError(
            "Could not decrypt stored Alpaca secret — check CREDENTIALS_FERNET_KEY"
        ),
    ):
        with pytest.raises(TradingAuthError) as err:
            get_trading_client("user-123")
        assert "decrypt" in err.value.detail.lower() or "FERNET" in err.value.detail


def test_build_trading_client_rejects_empty_keys():
    from app.core.alpaca_client import INCOMPLETE_CREDS, build_trading_client
    from app.core.alpaca_credentials import AlpacaCredentials

    creds = AlpacaCredentials(
        user_id="u", api_key_id="  ", api_secret="", is_paper=True
    )
    with pytest.raises(TradingAuthError) as err:
        build_trading_client(creds)
    assert err.value.detail == INCOMPLETE_CREDS


def test_friendly_trading_error_maps_unauthorized_json():
    from app.core.alpaca_client import friendly_trading_error

    class FakeApiError(Exception):
        status_code = 401

    msg = friendly_trading_error(
        FakeApiError('{"message": "unauthorized."}'), is_paper=True
    )
    assert msg is not None
    assert "Incorrect Alpaca keys" in msg
    assert "Paper" in msg


def test_market_get_price_calls_coinbase_not_loopback():
    from app.agent import market_tools

    fake = MagicMock()
    fake.raise_for_status = MagicMock()
    fake.json.return_value = {"data": {"amount": "3500.12"}}

    with patch("app.agent.market_tools.requests.get", return_value=fake) as get:
        out = market_tools.get_price("ETH")
        assert "3500.12" in out
        assert "ETH" in out
        url = get.call_args[0][0]
        assert "api.coinbase.com" in url
        assert "127.0.0.1" not in url


def test_get_agent_uses_in_process_market_tools_only():
    """Agent must not spawn MCP stdio (broken on Render)."""
    import asyncio

    import app.agent.agent_service as svc

    svc._agent = None
    svc._checkpointer = None

    async def _run():
        with patch("app.agent.agent_service.create_agent") as create:
            create.return_value = object()
            with patch("app.agent.agent_service.ChatOpenAI"):
                with patch("app.agent.agent_service.InMemorySaver"):
                    with patch(
                        "app.agent.agent_service.build_portfolio_tools",
                        return_value=["p"],
                    ):
                        with patch(
                            "app.agent.agent_service.build_market_tools",
                            return_value=["m"],
                        ) as market:
                            await svc.get_agent()
                            market.assert_called_once()
                            assert create.call_args.kwargs.get("tools") == ["p", "m"]

    try:
        asyncio.run(_run())
    finally:
        svc._agent = None
        svc._checkpointer = None

