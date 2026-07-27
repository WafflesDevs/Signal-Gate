"""
AI agent for Signal Gate.

Used by:
  - the website chat (app/routers/chat.py)
  - the CLI (python -m app.agent.cli)

Simple flow:
  run_turn()     → user sends a message (wait for full reply)
  stream_turn()  → same, but yield text tokens as they arrive
  resume_turn()  → user clicks Approve or Reject

Portfolio/trading tools run in-process (not MCP HTTP) so they use the
logged-in user's Alpaca keys via current_user_id contextvar.
"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import AsyncIterator, Iterator, Optional

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.agent.portfolio_tools import build_portfolio_tools
from app.core.user_context import trading_user

load_dotenv()

# Paths to the MCP tool scripts (project root = two levels up from this file)
ROOT = Path(__file__).resolve().parents[2]
MCP_TICKERS = str(ROOT / "MCP" / "tickers.py")
PYTHON = str(ROOT / ".venv" / "bin" / "python")

SYSTEM_PROMPT = """
You are an AI assistant for a trading platform (user's linked Alpaca Paper or Live account).
RULES:
1. Only use the tools you are given.
2. Do not share secrets or credentials.
3. Buying — execute_trade(ticker, …) with EXACTLY ONE size field:
   A) Dollar / "worth" / USD / $ language → notional_usd (Alpaca spends that many dollars).
      Examples: "10k usd worth of XRP", "$10,000 of XRP", "buy 500 dollars of ETH"
      → execute_trade(ticker="XRP", notional_usd=10000). Expand k/m: 10k=10000, 1.5k=1500.
      NEVER pass qty=10 for "10k". NEVER convert dollars to coin qty yourself.
   B) Coin-unit language → qty only.
      Examples: "buy 10 XRP", "0.01 BTC" → execute_trade(ticker="XRP", qty=10).
   Tickers are BTC / ETH / XRP (never BTCUSD).
4. Multi-coin buys (e.g. "buy BTC and ETH", "split cash between A and B"):
   - ALWAYS use execute_trade once per coin.
   - Call all execute_trade tools in the same step so Approve covers every coin together.
   - NEVER call buy_max_trade for multi-coin requests — it spends ~95% of cash on ONE coin.
   - Coin amounts → qty; dollar splits → notional_usd per coin (equal $ split is fine).
5. buy_max_trade(ticker) — ONLY when the user clearly wants MAX for ONE coin:
   words like "max", "all in", "fill portfolio", "as much as possible" for a single ticker.
   Never use it when they named a dollar amount — use notional_usd instead.
6. Sell all of a coin → get_current_positions, then sell_trade once with the full qty.
7. Use get_price for prices and get_tickers for the list.
8. After a trade, call get_current_portfoilo and report the tool results honestly.
   If the tool returned notional_usd=10000, say you spent ~$10,000 — do not invent fills.
   If cash only moved a little, say so; never claim $10,000 when tools show otherwise.
9. For research, use search_web. Do not make up facts.
10. Stop-loss / take-profit: Do NOT set, cancel, or list exits. The user chooses
    Investment (no exits) or Short-term trade (optional SL/TP) on the Approve card.
    Never call set_exits, cancel_exits, or list_exits. Do not invent exit prices or
    ask them to confirm exits in chat — just propose the buy and wait for Approve/Reject.
11. If tools say no Alpaca account is linked, tell the user to open Settings and connect keys.
12. After every trade based execution tell the user to check the active trades panel on their right side.
13. If the user asks about withdrawing money, tell them to check the Alpaca Dashboard.
"""

# Build the agent once, then reuse it
_agent = None
_checkpointer = None
_lock = asyncio.Lock()


async def get_agent():
    """Create the agent the first time we need it."""
    global _agent, _checkpointer

    if _agent is not None:
        return _agent

    async with _lock:
        if _agent is not None:
            return _agent

        # Tickers/prices stay on MCP (public endpoints, no user keys).
        # Portfolio/trading tools are in-process so they see current_user_id.
        client = MultiServerMCPClient(
            {
                "tickers": {
                    "transport": "stdio",
                    "command": PYTHON,
                    "args": [MCP_TICKERS],
                },
            }
        )
        ticker_tools = await client.get_tools()
        tools = [*build_portfolio_tools(), *ticker_tools]

        _checkpointer = InMemorySaver()
        _agent = create_agent(
            ChatOpenAI(model="gpt-4o-mini", temperature=0),
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            middleware=[
                HumanInTheLoopMiddleware(
                    interrupt_on={
                        "execute_trade": {"allowed_decisions": ["approve", "reject"]},
                        "buy_max_trade": {"allowed_decisions": ["approve", "reject"]},
                        "sell_trade": {"allowed_decisions": ["approve", "reject"]},
                    },
                ),
            ],
            checkpointer=_checkpointer,
        )
        return _agent


def _get_reply(result) -> str:
    """Get the assistant's text from this turn only."""
    if hasattr(result, "value") and result.value is not None:
        messages = result.value.get("messages", [])
    elif isinstance(result, dict):
        messages = result.get("messages", [])
    else:
        messages = []

    start = 0
    for i, msg in enumerate(messages):
        if getattr(msg, "type", None) == "human":
            start = i + 1

    for msg in reversed(messages[start:]):
        if getattr(msg, "type", None) != "ai":
            continue
        text = getattr(msg, "content", "") or ""
        if isinstance(text, str) and text.strip():
            return text.strip()
    return ""


def _get_pending(result) -> list[dict]:
    """If the agent paused for approval, return those trades."""
    interrupts = getattr(result, "interrupts", None) or ()
    if not interrupts:
        return []

    value = interrupts[0].value or {}
    actions = value.get("action_requests", []) if isinstance(value, dict) else []

    pending = []
    for action in actions:
        pending.append(
            {
                "name": action.get("name"),
                "arguments": action.get("arguments") or action.get("args") or {},
            }
        )
    return pending


def _chunk_text(msg) -> str:
    """Pull plain text out of an AIMessageChunk (string or content blocks)."""
    text = getattr(msg, "text", None)
    if isinstance(text, str) and text:
        return text

    content = getattr(msg, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text") or "")
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return ""


def _result_from_state(state) -> SimpleNamespace:
    """Make aget_state output look like an ainvoke(version='v2') result."""
    return SimpleNamespace(
        value=getattr(state, "values", None) or {},
        interrupts=getattr(state, "interrupts", None) or (),
    )


def _finish_turn(result) -> dict:
    """Shared reply + pending_trades shaping for run/stream."""
    pending = _get_pending(result)
    reply = _get_reply(result)
    if pending and not reply:
        reply = "I need your approval before running this trade."
    return {"reply": reply, "pending_trades": pending}


@contextmanager
def _user_scope(user_id: Optional[str]) -> Iterator[None]:
    if user_id:
        with trading_user(user_id):
            yield
    else:
        yield


async def _reset_chat(thread_id: str):
    """Wipe this chat's agent memory (used when state gets stuck)."""
    if _checkpointer is not None:
        await _checkpointer.adelete_thread(thread_id)


async def clear_thread_memory(thread_ids: list[str]) -> None:
    """Best-effort wipe of in-memory HITL/agent state for the given chat ids."""
    if not thread_ids or _checkpointer is None:
        return
    for tid in thread_ids:
        try:
            await _checkpointer.adelete_thread(tid)
        except Exception:
            pass


def _agent_config(thread_id: str, user_id: Optional[str] = None) -> dict:
    """thread_id + user_id so in-process tools load that user's Alpaca keys."""
    configurable: dict = {"thread_id": thread_id}
    if user_id:
        configurable["user_id"] = user_id
    return {"configurable": configurable}


async def _prepare_turn(thread_id: str, user_id: Optional[str] = None):
    """Load agent + config; clear a stuck Approve interrupt if needed."""
    agent = await get_agent()
    config = _agent_config(thread_id, user_id)
    state = await agent.aget_state(config)
    if getattr(state, "interrupts", None):
        await _reset_chat(thread_id)
    return agent, config


async def run_turn(
    thread_id: str, user_message: str, *, user_id: Optional[str] = None
) -> dict:
    """
    Send one user message.
    Returns: { "reply": str, "pending_trades": list }
    """
    agent, config = await _prepare_turn(thread_id, user_id)

    with _user_scope(user_id):
        try:
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": user_message}]},
                config=config,
                version="v2",
            )
        except Exception as e:
            if "tool_call_id" in str(e):
                await _reset_chat(thread_id)
                result = await agent.ainvoke(
                    {"messages": [{"role": "user", "content": user_message}]},
                    config=config,
                    version="v2",
                )
            else:
                raise

    return _finish_turn(result)


async def stream_turn(
    thread_id: str, user_message: str, *, user_id: Optional[str] = None
) -> AsyncIterator[dict]:
    """
    Same as run_turn, but yields events as the model writes:

      {"type": "token", "text": "..."}   ← each text chunk
      {"type": "done", "reply": "...", "pending_trades": [...]}

    HITL interrupts still work — pending_trades land on the done event.
    """
    agent, config = await _prepare_turn(thread_id, user_id)
    payload = {"messages": [{"role": "user", "content": user_message}]}

    async def _stream_once():
        async for part in agent.astream(
            payload,
            config=config,
            stream_mode=["messages", "values"],
            version="v2",
        ):
            yield part

    with _user_scope(user_id):
        try:
            stream = _stream_once()
            async for part in stream:
                if part.get("type") != "messages":
                    continue
                msg, meta = part["data"]
                if meta.get("langgraph_node") != "model":
                    continue
                text = _chunk_text(msg)
                if text:
                    yield {"type": "token", "text": text}
        except Exception as e:
            if "tool_call_id" not in str(e):
                raise
            await _reset_chat(thread_id)
            async for part in _stream_once():
                if part.get("type") != "messages":
                    continue
                msg, meta = part["data"]
                if meta.get("langgraph_node") != "model":
                    continue
                text = _chunk_text(msg)
                if text:
                    yield {"type": "token", "text": text}

        state = await agent.aget_state(config)
        turn = _finish_turn(_result_from_state(state))
        yield {"type": "done", **turn}


async def resume_turn(
    thread_id: str, decisions: list[dict], *, user_id: Optional[str] = None
) -> dict:
    """
    Continue after Approve / Reject.
    If the agent asks again in the same run, keep using the same choice.
    """
    agent = await get_agent()
    config = _agent_config(thread_id, user_id)

    state = await agent.aget_state(config)
    if not getattr(state, "interrupts", None):
        return {
            "reply": "Nothing to approve — that request expired. Send it again.",
            "pending_trades": [],
        }

    result = None
    with _user_scope(user_id):
        for _ in range(5):
            try:
                result = await agent.ainvoke(
                    Command(resume={"decisions": decisions}),
                    config=config,
                    version="v2",
                )
            except Exception as e:
                if "tool_call_id" in str(e):
                    await _reset_chat(thread_id)
                    return {
                        "reply": "Approval failed. Please send the trade again.",
                        "pending_trades": [],
                    }
                raise

            pending = _get_pending(result)
            if not pending:
                break

            if decisions and decisions[0].get("type") == "approve":
                decisions = [{"type": "approve"}] * len(pending)
            else:
                decisions = [
                    {"type": "reject", "message": "User said no. Do not retry this trade."}
                ] * len(pending)

    pending = _get_pending(result)
    reply = _get_reply(result)

    if pending and not reply:
        reply = "Another trade needs approval."
    elif not pending and (not reply or reply.lower() == "response submitted"):
        if decisions and decisions[0].get("type") == "approve":
            reply = "Trade approved and submitted."
        else:
            reply = "Trade rejected. Nothing was sent."

    return {"reply": reply, "pending_trades": pending}
