"""Pydantic request / response schemas for the API layer."""

import json
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# --------------------------------------------------------------------------- #
#  Chat
# --------------------------------------------------------------------------- #

class ChatRequest(BaseModel):
    """Send a message in a conversation."""
    conversation_id: str | None = Field(None, description="对话 ID，为空则新建对话")
    message: str = Field(..., description="用户消息内容")
    user_lat: float | None = Field(None, description="用户当前纬度（用于地图出行时间计算）")
    user_lon: float | None = Field(None, description="用户当前经度（用于地图出行时间计算）")
    file_id: str | None = Field(None, description="上传的文档文件ID（可选，docx 编辑）")
    image_id: str | None = Field(None, description="上传的图片文件ID（可选，图片识别）")


class ConversationCreate(BaseModel):
    """Create a new conversation."""
    title: str = Field("新对话", description="对话标题")


class MessageOut(BaseModel):
    """A single message returned to the frontend."""
    id: str
    role: str
    content: str
    created_at: datetime
    map_data: dict | None = None
    weather_data: dict | None = None
    file_data: dict | None = None
    image_data: dict | None = None

    @field_validator("map_data", mode="before")
    @classmethod
    def _parse_map_data(cls, v):
        if isinstance(v, str) and v:
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return None
        return v

    @field_validator("weather_data", mode="before")
    @classmethod
    def _parse_weather_data(cls, v):
        if isinstance(v, str) and v:
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return None
        return v

    @field_validator("file_data", mode="before")
    @classmethod
    def _parse_file_data(cls, v):
        if isinstance(v, str) and v:
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return None
        return v

    @field_validator("image_data", mode="before")
    @classmethod
    def _parse_image_data(cls, v):
        if isinstance(v, str) and v:
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return None
        return v

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


class DefaultLocation(BaseModel):
    """User's default weather location."""
    place: str
    display_name: str
    lat: float
    lon: float
