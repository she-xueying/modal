"""Chat API routes: conversation CRUD + streaming chat."""

from __future__ import annotations

import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.file_service import FileError, create_file_record, save_docx_upload, save_image_upload
from app.models.database import Conversation, File as FileRecord, Message, Setting, get_db
from app.models.schemas import (
    ChatRequest,
    ConversationCreate,
    ConversationDetail,
    ConversationOut,
    DefaultLocation,
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

    # 2. Persist the user message (with uploaded file/image reference if any)
    user_file_data = None
    if req.file_id:
        file_rec = db.get(FileRecord, req.file_id)
        if file_rec is not None:
            user_file_data = {
                "id": file_rec.id,
                "filename": file_rec.filename,
                "url": f"/api/files/{file_rec.id}/download",
            }
    user_image_data = None
    if req.image_id:
        img_rec = db.get(FileRecord, req.image_id)
        if img_rec is not None:
            user_image_data = {
                "id": img_rec.id,
                "filename": img_rec.filename,
                "url": f"/api/files/{img_rec.id}/view",
            }
    save_message(
        db, conv, "user", req.message,
        file_data=user_file_data,
        image_data=user_image_data,
    )

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
                file_id=req.file_id,
                image_id=req.image_id,
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

# --------------------------------------------------------------------------- #
#  File upload / download (docx)
# --------------------------------------------------------------------------- #

@router.post("/files/upload")
async def upload_docx(file: UploadFile = FastFile(...), db: Session = Depends(get_db)):
    """Upload a .docx file; returns {id, filename}."""
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="仅支持 .docx 文件")
    content = await file.read()
    try:
        data = save_docx_upload(content, filename or "document.docx")
    except FileError as e:
        raise HTTPException(status_code=400, detail=str(e))
    rec = create_file_record(db, **data)
    return {"id": rec.id, "filename": rec.filename}


@router.get("/files/{file_id}/download")
def download_file(file_id: str, db: Session = Depends(get_db)):
    """Download an uploaded or generated file."""
    rec = db.get(FileRecord, file_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    from pathlib import Path
    path = Path(rec.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=rec.filename,
    )


# --------------------------------------------------------------------------- #
#  Image upload / view (for vision / OCR)
# --------------------------------------------------------------------------- #

@router.post("/files/upload-image")
async def upload_image(file: UploadFile = FastFile(...), db: Session = Depends(get_db)):
    """Upload an image file; returns {id, filename, url}."""
    filename = (file.filename or "").strip()
    content = await file.read()
    try:
        data = save_image_upload(content, filename or "image.png")
    except FileError as e:
        raise HTTPException(status_code=400, detail=str(e))
    rec = create_file_record(db, **data)
    return {"id": rec.id, "filename": rec.filename, "url": f"/api/files/{rec.id}/view"}


@router.get("/files/{file_id}/view")
def view_image(file_id: str, db: Session = Depends(get_db)):
    """Serve an image file for display in the browser."""
    rec = db.get(FileRecord, file_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="图片不存在")
    from pathlib import Path
    import mimetypes
    path = Path(rec.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="图片不存在")
    media_type = mimetypes.types_map.get(path.suffix.lower(), "image/jpeg")
    return FileResponse(path, media_type=media_type, filename=rec.filename)


# --------------------------------------------------------------------------- #
#  Default weather location (user-configurable)
# --------------------------------------------------------------------------- #

DEFAULT_LOCATION_KEY = "default_weather_location"


def _read_default_location(db: Session) -> dict | None:
    row = db.get(Setting, DEFAULT_LOCATION_KEY)
    if row is None:
        return None
    try:
        data = json.loads(row.value)
        return data if isinstance(data, dict) else None
    except (ValueError, TypeError):
        return None


@router.get("/settings/default-location")
def get_default_location(db: Session = Depends(get_db)):
    """Get the user's default weather location (or null)."""
    return {"default": _read_default_location(db)}


@router.put("/settings/default-location")
def set_default_location(req: DefaultLocation, db: Session = Depends(get_db)):
    """Set the user's default weather location."""
    payload = req.model_dump()
    row = db.get(Setting, DEFAULT_LOCATION_KEY)
    if row is None:
        row = Setting(key=DEFAULT_LOCATION_KEY, value=json.dumps(payload, ensure_ascii=False))
        db.add(row)
    else:
        row.value = json.dumps(payload, ensure_ascii=False)
    db.commit()
    return {"default": payload}


@router.delete("/settings/default-location")
def delete_default_location(db: Session = Depends(get_db)):
    """Clear the user's default weather location."""
    row = db.get(Setting, DEFAULT_LOCATION_KEY)
    if row is not None:
        db.delete(row)
        db.commit()
    return {"default": None}


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
