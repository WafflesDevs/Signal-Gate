"""
AI agent for Signal Gate.

Used by:
  - the website chat (app/routers/chat.py)
  - the CLI (python -m app.agent.cli)

Simple flow:
  run_turn()     → user sends a message (wait for full reply)
  stream_turn()  → same, but yield text tokens as they arrive
  resume_turn()  → user clicks Approve or Reject
"""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import AsyncIterator

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

load_dotenv()

# Paths to the MCP tool scripts (project root = two levels up from this file)
ROOT = Path(__file__).resolve().parents[2]
MCP_PORTFOLIO = str(ROOT / "MCP" / "portfolio.py")
MCP_TICKERS = str(ROOT / "MCP" / "tickers.py")
PYTHON = str(ROOT / ".venv" / "bin" / "python")

# Exit tools stay in MCP/API for the app UI — never expose them to the LLM
_EXIT_TOOL_NAMES = frozenset({"set_exits", "cancel_exits", "list_exits"})

SYSTEM_PROMPT = """
You are an AI assistant for a paper trading platform.
RULES:
1. Only use the tools you are given.
2. Do not share secrets or credentials.
3. Buy a specific amount → execute_trade(qty, ticker). Use tickers like BTC or XRP, never BTCUSD.
4. Multi-coin buys (e.g. "buy BTC and ETH", "split cash between A and B"):
   - ALWAYS use execute_trade once per coin with a concrete qty.
   - Call all execute_trade tools in the same step so Approve covers every coin together.
   - NEVER call buy_max_trade for multi-coin requests — it spends ~95% of cash on ONE coin
     and leaves almost nothing for the rest.
   - If the user gives amounts ("0.01 BTC and 0.1 ETH"), use those exact qtys.
   - If they say "split cash" / "buy A and B" without amounts: check cash + prices,
     pick fair qtys (equal $ split is fine), then call execute_trade for each coin.
5. buy_max_trade(ticker) — ONLY when the user clearly wants MAX for ONE coin:
   words like "max", "all in", "fill portfolio", "as much as possible" for a single ticker.
   Call it once. Do not guess the qty. Never use it for two or more coins.
6. Sell all of a coin → get_current_positions, then sell_trade once with the full qty.
7. Use get_price for prices and get_tickers for the list.
8. After a trade, call get_current_portfoilo and show the new amounts.
9. For research, use search_web. Do not make up facts.
10. Stop-loss / take-profit: Do NOT set, cancel, or list exits. The user chooses
    Investment (no exits) or Short-term trade (optional SL/TP) on the Approve card.
    Never call set_exits, cancel_exits, or list_exits. Do not invent exit prices or
    ask them to confirm exits in chat — just propose the buy and wait for Approve/Reject.
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

        # 1) Start MCP servers (portfolio + tickers tools)
        client = MultiServerMCPClient(
            {
                "portfolio": {
                    "transport": "stdio",
                    "command": PYTHON,
                    "args": [MCP_PORTFOLIO],
                },
                "tickers": {
                    "transport": "stdio",
                    "command": PYTHON,
                    "args": [MCP_TICKERS],
                },
            }
        )
        all_tools = await client.get_tools()
        # Keep exit MCP tools for /paper/exits + monitor; hide from the agent
        tools = [
            t
            for t in all_tools
            if getattr(t, "name", None) not in _EXIT_TOOL_NAMES
        ]

        # 2) Pause before buy/sell so the user can Approve / Reject
        # 3) InMemorySaver remembers where we paused (needs a thread_id)
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
    # Pull the message list out of the result
    if hasattr(result, "value") and result.value is not None:
        messages = result.value.get("messages", [])
    elif isinstance(result, dict):
        messages = result.get("messages", [])
    else:
        messages = []

    # Only look at messages after the latest user message
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


async def _reset_chat(thread_id: str):
    """Wipe this chat's agent memory (used when state gets stuck)."""
    if _checkpointer is not None:
        await _checkpointer.adelete_thread(thread_id)


async def _prepare_turn(thread_id: str):
    """Load agent + config; clear a stuck Approve interrupt if needed."""
    agent = await get_agent()
    config = {"configurable": {"thread_id": thread_id}}
    state = await agent.aget_state(config)
    if getattr(state, "interrupts", None):
        await _reset_chat(thread_id)
    return agent, config


async def run_turn(thread_id: str, user_message: str) -> dict:
    """
    Send one user message.
    Returns: { "reply": str, "pending_trades": list }
    """
    agent, config = await _prepare_turn(thread_id)

    try:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config=config,
            version="v2",
        )
    except Exception as e:
        # Broken memory after a server reload — reset and try once more
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


async def stream_turn(thread_id: str, user_message: str) -> AsyncIterator[dict]:
    """
    Same as run_turn, but yields events as the model writes:

      {"type": "token", "text": "..."}   ← each text chunk
      {"type": "done", "reply": "...", "pending_trades": [...]}

    HITL interrupts still work — pending_trades land on the done event.
    """
    agent, config = await _prepare_turn(thread_id)
    payload = {"messages": [{"role": "user", "content": user_message}]}

    async def _stream_once():
        async for part in agent.astream(
            payload,
            config=config,
            stream_mode=["messages", "values"],
            version="v2",
        ):
            yield part

    try:
        stream = _stream_once()
        async for part in stream:
            if part.get("type") != "messages":
                continue
            msg, meta = part["data"]
            # Only stream tokens from the LLM node (skip tool noise)
            if meta.get("langgraph_node") != "model":
                continue
            text = _chunk_text(msg)
            if text:
                yield {"type": "token", "text": text}
    except Exception as e:
        if "tool_call_id" not in str(e):
            raise
        # Broken memory after a server reload — reset and try once more
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

    # Final state has the full reply + any Approve/Reject interrupt
    state = await agent.aget_state(config)
    turn = _finish_turn(_result_from_state(state))
    yield {"type": "done", **turn}


async def resume_turn(thread_id: str, decisions: list[dict]) -> dict:
    """
    Continue after Approve / Reject.
    If the agent asks again in the same run, keep using the same choice.
    """
    agent = await get_agent()
    config = {"configurable": {"thread_id": thread_id}}

    state = await agent.aget_state(config)
    if not getattr(state, "interrupts", None):
        return {
            "reply": "Nothing to approve — that request expired. Send it again.",
            "pending_trades": [],
        }

    result = None
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

        # Same Approve/Reject for any follow-up trades
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
