"""Unit tests for exit-rule trigger logic (no network / Alpaca)."""

from app.exits.monitor import should_trigger
from app.exits.store import ExitRule


def _rule(**kwargs) -> ExitRule:
    base = dict(
        id="test",
        ticker="BTC",
        qty=None,
        stop_loss=None,
        take_profit=None,
        created_at="2026-01-01T00:00:00+00:00",
    )
    base.update(kwargs)
    return ExitRule(**base)


def test_stop_loss_triggers_at_or_below():
    rule = _rule(stop_loss=90_000.0, take_profit=110_000.0)
    assert should_trigger(89_999.0, rule) == "stop_loss"
    assert should_trigger(90_000.0, rule) == "stop_loss"
    assert should_trigger(90_001.0, rule) is None


def test_take_profit_triggers_at_or_above():
    rule = _rule(stop_loss=90_000.0, take_profit=110_000.0)
    assert should_trigger(110_000.0, rule) == "take_profit"
    assert should_trigger(110_001.0, rule) == "take_profit"
    assert should_trigger(109_999.0, rule) is None


def test_sl_preferred_when_both_could_fire():
    # Degenerate prices shouldn't happen after validation, but SL wins first.
    rule = _rule(stop_loss=100.0, take_profit=100.0)
    assert should_trigger(100.0, rule) == "stop_loss"


def test_sl_only_or_tp_only():
    assert should_trigger(50.0, _rule(stop_loss=60.0)) == "stop_loss"
    assert should_trigger(70.0, _rule(take_profit=60.0)) == "take_profit"
    assert should_trigger(55.0, _rule(stop_loss=50.0)) is None
