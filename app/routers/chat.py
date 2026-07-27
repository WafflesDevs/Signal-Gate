"""
Chat API (needs a logged-in user).

  GET    /chat/conversations
  POST   /chat/conversations
  GET    /chat/conversations/{id}/messages
  POST   /chat/conversations/{id}/messages          ← send a message (full reply)
  POST   /chat/conversations/{id}/messages/stream   ← send a message (SSE tokens)
  POST   /chat/conversations/{id}/resume            ← Approve / Reject
  DELETE /chat/conversations/{id}
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.agent.agent_service import resume_turn, run_turn, stream_turn
from app.core.auth import AuthUser, get_current_user
from app.schemas.schemas import (
    ChatMessageBody,
    ChatTurnOut,
    ConversationOut,
    CreateConversationBody,
    MessageOut,
    PendingTrade,
    ResumeBody,
)
from app.core.supabase_client import get_supabase

router = APIRouter(prefix="/chat", tags=["Chatting"])

# Storage caps — keep chats small in Supabase
MAX_CONVERSATIONS = 5
MAX_MESSAGES_PER_CHAT = 30

CHAT_LIMIT_MSG = (
    "Chat limit reached (5). Delete a chat in the sidebar to open a new one."
)
MESSAGE_LIMIT_MSG = (
    "Message limit reached (30). Delete this chat and open a new one."
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_title(message: str) -> str:
    """Short sidebar title from the first message."""
    text = " ".join(message.strip().split())
    if not text:
        return "New chat"
    if len(text) <= 48:
        return text
    return text[:45] + "…"


def count_conversations(user_id: str) -> int:
    res = (
        get_supabase()
        .table("conversations")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    if res.count is not None:
        return int(res.count)
    return len(res.data or [])


def count_messages(conversation_id: str) -> int:
    res = (
        get_supabase()
        .table("messages")
        .select("id", count="exact")
        .eq("conversation_id", conversation_id)
        .execute()
    )
    if res.count is not None:
        return int(res.count)
    return len(res.data or [])


def get_conversation(conversation_id: str, user_id: str) -> dict:
    """Load a chat and make sure it belongs to this user."""
    sb = get_supabase()
    res = (
        sb.table("conversations")
        .select("*")
        .eq("id", conversation_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return res.data[0]


def save_message(conversation_id: str, role: str, content: str, metadata: dict | None = None):
    """Save one chat message to Supabase."""
    sb = get_supabase()
    res = (
        sb.table("messages")
        .insert(
            {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "metadata": metadata or {},
            }
        )
        .execute()
    )
    row = (res.data or [None])[0]
    if row is not None:
        row["metadata"] = row.get("metadata") or {}
    return row


def touch_conversation(conversation_id: str, title: str | None = None):
    """Bump updated_at (and maybe set the title)."""
    data = {"updated_at": now()}
    if title is not None:
        data["title"] = title
    get_supabase().table("conversations").update(data).eq("id", conversation_id).execute()


def clear_pending(conversation_id: str, resolution: str):
    """Remove Approve/Reject buttons from old messages in this chat."""
    sb = get_supabase()
    res = (
        sb.table("messages")
        .select("id,metadata")
        .eq("conversation_id", conversation_id)
        .eq("role", "assistant")
        .order("created_at", desc=True)
        .limit(30)
        .execute()
    )
    for row in res.data or []:
        meta = row.get("metadata") or {}
        if not meta.get("pending_trades"):
            continue
        sb.table("messages").update(
            {
                "metadata": {
                    **meta,
                    "pending_trades": [],
                    "resolved": True,
                    "resolution": resolution,
                }
            }
        ).eq("id", row["id"]).execute()


def turn_response(turn: dict, saved_message: dict | None) -> ChatTurnOut:
    pending = turn.get("pending_trades") or []
    return ChatTurnOut(
        reply=turn.get("reply") or "",
        pending_trades=[PendingTrade(**p) for p in pending],
        message=MessageOut(**saved_message) if saved_message else None,
    )


# ---------- list / create / delete ----------

@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(user: AuthUser = Depends(get_current_user)):
    res = (
        get_supabase()
        .table("conversations")
        .select("id,title,created_at,updated_at")
        .eq("user_id", user.id)
        .order("updated_at", desc=True)
        .limit(MAX_CONVERSATIONS)
        .execute()
    )
    return res.data or []


@router.post("/conversations", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    body: CreateConversationBody,
    user: AuthUser = Depends(get_current_user),
):
    if count_conversations(user.id) >= MAX_CONVERSATIONS:
        raise HTTPException(status_code=400, detail=CHAT_LIMIT_MSG)

    res = (
        get_supabase()
        .table("conversations")
        .insert({"user_id": user.id, "title": body.title or "New chat"})
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=500, detail="Could not create conversation")
    return res.data[0]


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: str, user: AuthUser = Depends(get_current_user)):
    get_conversation(conversation_id, user.id)
    get_supabase().table("conversations").delete().eq("id", conversation_id).eq(
        "user_id", user.id
    ).execute()
    return None


# ---------- messages ----------

@router.get("/conversations/{conversation_id}", response_model=list[MessageOut])
@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(conversation_id: str, user: AuthUser = Depends(get_current_user)):
    get_conversation(conversation_id, user.id)
    res = (
        get_supabase()
        .table("messages")
        .select("id,role,content,metadata,created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .limit(MAX_MESSAGES_PER_CHAT)
        .execute()
    )
    rows = res.data or []
    for row in rows:
        row["metadata"] = row.get("metadata") or {}
    return rows


def _prepare_send(conversation_id: str, user: AuthUser, message: str) -> dict:
    """Shared checks + save user message before run_turn / stream_turn."""
    convo = get_conversation(conversation_id, user.id)

    # Need room for this user message + the assistant reply (2 rows)
    existing = count_messages(conversation_id)
    if existing >= MAX_MESSAGES_PER_CHAT - 1:
        raise HTTPException(status_code=400, detail=MESSAGE_LIMIT_MSG)

    # User typed something new → cancel old Approve buttons
    clear_pending(conversation_id, "cancelled")

    # 1) Save user message
    save_message(conversation_id, "user", message)

    # 2) Title from first message
    if convo.get("title") in (None, "", "New chat"):
        touch_conversation(conversation_id, title=make_title(message))
    else:
        touch_conversation(conversation_id)

    return convo


@router.post("/conversations/{conversation_id}/messages", response_model=ChatTurnOut)
async def send_message(
    conversation_id: str,
    body: ChatMessageBody,
    user: AuthUser = Depends(get_current_user),
):
    _prepare_send(conversation_id, user, body.message)

    # 3) Run the agent
    try:
        turn = await run_turn(conversation_id, body.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {e}") from e

    # 4) Save assistant reply
    pending = turn.get("pending_trades") or []
    saved = save_message(
        conversation_id,
        "assistant",
        turn.get("reply") or "",
        {"pending_trades": pending} if pending else {},
    )
    return turn_response(turn, saved)


@router.post("/conversations/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: str,
    body: ChatMessageBody,
    user: AuthUser = Depends(get_current_user),
):
    """
    SSE stream for a chat turn.

    Events (each line is `data: {json}\\n\\n`):
      {"type": "token", "text": "..."}
      {"type": "final", "reply": "...", "pending_trades": [...], "message": {...}}
      {"type": "error", "detail": "..."}
    """
    _prepare_send(conversation_id, user, body.message)

    async def event_gen():
        try:
            async for event in stream_turn(conversation_id, body.message):
                if event.get("type") == "token":
                    yield f"data: {json.dumps(event)}\n\n"
                    continue

                if event.get("type") != "done":
                    continue

                # Save assistant reply, then send final payload (HITL fields included)
                pending = event.get("pending_trades") or []
                reply = event.get("reply") or ""
                saved = save_message(
                    conversation_id,
                    "assistant",
                    reply,
                    {"pending_trades": pending} if pending else {},
                )
                out = turn_response(
                    {"reply": reply, "pending_trades": pending},
                    saved,
                )
                yield f"data: {json.dumps({'type': 'final', **out.model_dump()})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'detail': f'Agent error: {e}'})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/conversations/{conversation_id}/resume", response_model=ChatTurnOut)
async def resume_message(
    conversation_id: str,
    body: ResumeBody,
    user: AuthUser = Depends(get_current_user),
):
    get_conversation(conversation_id, user.id)

    # Build approve/reject list for the agent
    decisions = []
    for d in body.decisions:
        item = {"type": d.type}
        if d.message:
            item["message"] = d.message
        elif d.type == "reject":
            item["message"] = "User said no. Do not retry this trade."
        decisions.append(item)

    try:
        turn = await resume_turn(conversation_id, decisions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {e}") from e

    resolution = decisions[0]["type"] if decisions else "approve"
    clear_pending(conversation_id, resolution)

    pending = turn.get("pending_trades") or []
    reply = (turn.get("reply") or "").strip()
    if not reply and not pending:
        reply = (
            "Trade approved and submitted."
            if resolution == "approve"
            else "Trade rejected. Nothing was sent."
        )

    # Allow one final assistant note even near the cap (finishing a trade)
    if count_messages(conversation_id) >= MAX_MESSAGES_PER_CHAT:
        return turn_response({**turn, "reply": reply}, None)

    saved = save_message(
        conversation_id,
        "assistant",
        reply,
        {"pending_trades": pending} if pending else {},
    )
    touch_conversation(conversation_id)
    return turn_response({**turn, "reply": reply}, saved)
