"""Chat API routes: conversation CRUD + streaming chat."""

from __future__ import annotations

import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import Conversation, Message, get_db
from app.models.schemas import (
    ChatRequest,
    ConversationCreate,
    ConversationDetail,
    ConversationOut,
    MessageOut,
)
from app.services.chat_service import chat_stream, get_or_create_conversation, save_message

router = APIRouter(prefix="/api", tags=["chat"])


# --------------------------------------------------------------------------- #
#  Streaming chat
# --------------------------------------------------------------------------- #

@router.post("/chat")
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """Send a message and receive a streaming (SSE) response.

    The response is Server-Sent Events with two event types:
    - ``conversation``: the conversation ID (sent first)
    - ``message``: content delta chunks
    - ``done``: signals completion
    """
    # 1. Get or create conversation
    conv = get_or_create_conversation(db, req.conversation_id, req.message)

    # 2. Persist the user message
    save_message(db, conv, "user", req.message)

    # 3. Stream the assistant response
    conversation_id = conv.id

    async def event_stream():
        # Send conversation ID first so frontend can associate
        yield f"data: {json.dumps({'type': 'conversation', 'id': conversation_id})}\n\n"

        try:
            async for chunk in chat_stream(
                db, conv, req.message,
                user_lat=req.user_lat,
                user_lon=req.user_lon,
            ):
                if isinstance(chunk, dict):
                    # Map data or other structured event - send directly
                    yield f"data: {json.dumps(chunk)}\n\n"
                else:
                    # Text chunk
                    yield f"data: {json.dumps({'type': 'message', 'content': chunk})}\n\n"
        except Exception as e:
            import logging
            logging.exception("chat_stream error")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# --------------------------------------------------------------------------- #
#  Conversation CRUD
# --------------------------------------------------------------------------- #

@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db)):
    """List all conversations, newest first."""
    convs = db.query(Conversation).order_by(Conversation.updated_at.desc()).all()
    result = []
    for conv in convs:
        out = ConversationOut.model_validate(conv)
        out.message_count = len(conv.messages)
        result.append(out)
    return result


@router.post("/conversations", response_model=ConversationOut)
def create_conversation(req: ConversationCreate, db: Session = Depends(get_db)):
    """Create a new conversation."""
    conv = Conversation(title=req.title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    out = ConversationOut.model_validate(conv)
    out.message_count = 0
    return out


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Get a conversation with all its messages."""
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="对话不存在")
    out = ConversationDetail.model_validate(conv)
    out.message_count = len(conv.messages)
    out.messages = [
        MessageOut.model_validate(m)
        for m in sorted(conv.messages, key=lambda m: m.created_at)
    ]
    return out


@router.patch("/conversations/{conversation_id}", response_model=ConversationOut)
def update_conversation(conversation_id: str, title: str, db: Session = Depends(get_db)):
    """Update a conversation's title."""
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="对话不存在")
    conv.title = title.strip() or "无标题"
    from datetime import datetime, timezone
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conv)
    out = ConversationOut.model_validate(conv)
    out.message_count = len(conv.messages)
    return out


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Delete a conversation and all its messages."""
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="对话不存在")
    db.delete(conv)
    db.commit()
    return {"detail": "已删除"}


@router.post("/conversations/{conversation_id}/truncate")
def truncate_conversation(conversation_id: str, keep_count: int, db: Session = Depends(get_db)):
    """Delete all messages beyond keep_count (keep the first keep_count messages).

    Used when a user edits a message: the edited message and everything after
    it is removed from the database before the new message is sent.
    """
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="对话不存在")

    msgs = sorted(conv.messages, key=lambda m: m.created_at)
    to_delete = msgs[keep_count:]
    for msg in to_delete:
        db.delete(msg)

    from datetime import datetime, timezone
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"detail": f"已删除 {len(to_delete)} 条消息", "remaining": keep_count}


# --------------------------------------------------------------------------- #
#  Batch delete conversations
# --------------------------------------------------------------------------- #

class BatchDeleteRequest(BaseModel):
    ids: List[str]


@router.post("/conversations/batch-delete")
def batch_delete_conversations(req: BatchDeleteRequest, db: Session = Depends(get_db)):
    """Delete multiple conversations at once."""
    deleted = 0
    for conv_id in req.ids:
        conv = db.get(Conversation, conv_id)
        if conv:
            db.delete(conv)
            deleted += 1
    db.commit()
    return {"detail": f"已删除 {deleted} 个对话", "deleted": deleted}


# --------------------------------------------------------------------------- #
#  Delete a single message
# --------------------------------------------------------------------------- #

@router.delete("/conversations/{conversation_id}/messages/{message_index}")
def delete_message(conversation_id: str, message_index: int, db: Session = Depends(get_db)):
    """Delete a single message by its index position in the conversation."""
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="对话不存在")

    msgs = sorted(conv.messages, key=lambda m: m.created_at)
    if message_index < 0 or message_index >= len(msgs):
        raise HTTPException(status_code=400, detail="消息索引无效")

    msg_to_delete = msgs[message_index]
    db.delete(msg_to_delete)

    from datetime import datetime, timezone
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"detail": "已删除该消息"}
