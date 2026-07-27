"""
Request / response shapes for the chat API.
These tell FastAPI what JSON to expect and return.
"""

from pydantic import BaseModel, Field


# --- what the frontend sends ---

class ChatMessageBody(BaseModel):
    message: str = Field(min_length=1, description="User message")


class CreateConversationBody(BaseModel):
    title: str = Field(default="New chat", max_length=120)


class TradeDecision(BaseModel):
    type: str  # "approve" or "reject"
    message: str | None = None


class ResumeBody(BaseModel):
    decisions: list[TradeDecision]


# --- what the API returns ---

class PendingTrade(BaseModel):
    name: str
    arguments: dict = Field(default_factory=dict)


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    metadata: dict = Field(default_factory=dict)
    created_at: str | None = None


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: str | None = None
    updated_at: str | None = None


class ChatTurnOut(BaseModel):
    reply: str
    pending_trades: list[PendingTrade] = Field(default_factory=list)
    message: MessageOut | None = None
