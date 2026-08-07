"""Pydantic request / response schemas for the API layer."""

from datetime import datetime
from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
#  Chat
# --------------------------------------------------------------------------- #

class ChatRequest(BaseModel):
    """Send a message in a conversation."""
    conversation_id: str | None = Field(None, description="对话 ID，为空则新建对话")
    message: str = Field(..., description="用户消息内容")
    user_lat: float | None = Field(None, description="用户当前纬度（用于地图出行时间计算）")
    user_lon: float | None = Field(None, description="用户当前经度（用于地图出行时间计算）")


class ConversationCreate(BaseModel):
    """Create a new conversation."""
    title: str = Field("新对话", description="对话标题")


class MessageOut(BaseModel):
    """A single message returned to the frontend."""
    id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    """A conversation with its metadata."""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationOut):
    """A conversation including all messages."""
    messages: list[MessageOut] = []
