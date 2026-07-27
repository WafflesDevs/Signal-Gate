"""
Per-request trading user id.

Chat sets this before the agent runs so in-process portfolio tools
know whose Alpaca credentials to load. Paper routes set it from auth.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Optional

_current_user_id: ContextVar[Optional[str]] = ContextVar("current_user_id", default=None)


def get_current_user_id() -> Optional[str]:
    return _current_user_id.get()


def set_current_user_id(user_id: Optional[str]):
    return _current_user_id.set(user_id)


def reset_current_user_id(token) -> None:
    _current_user_id.reset(token)


@contextmanager
def trading_user(user_id: str) -> Iterator[None]:
    """Bind trading tools / Alpaca client lookups to this user for the block."""
    token = set_current_user_id(user_id)
    try:
        yield
    finally:
        reset_current_user_id(token)
