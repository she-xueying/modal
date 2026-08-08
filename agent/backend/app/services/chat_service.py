"""Chat service: orchestrates LLM calls, tool execution, and persistence.

Flow:
  1. Get/create conversation, load history from DB
  2. Non-streaming LLM call *with tools* to decide if search/map is needed
  3a. If tool called -> execute tool -> streaming LLM call with results -> yield chunks
  3b. If no tool -> yield the content directly
  4. Persist user message + assistant response to DB

Yields either:
  - str: text chunk for the assistant response
  - dict: {"type": "map", "data": {...}} for map data to render in frontend
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.llm import LLMError, llm_client
from app.core.prompts import SYSTEM_PROMPT
from app.core.search import ALL_TOOLS, TOOL_EXECUTORS, SearchError
from app.core.map_service import map_search, map_result_to_text
from app.core.weather_service import weather_search, weather_result_to_text
from app.models.database import Conversation, Message

# Maximum number of past messages to include as context (excluding system prompt)
MAX_CONTEXT_MESSAGES = 20


def get_or_create_conversation(
    db: Session, conversation_id: str | None, user_message: str
) -> Conversation:
    """Return an existing conversation or create a new one.

    For new conversations, auto-generate a title from the first user message.
    """
    if conversation_id:
        conv = db.get(Conversation, conversation_id)
        if conv is not None:
            return conv

    # Create new conversation
    title = user_message[:30] + ("…" if len(user_message) > 30 else "")
    conv = Conversation(title=title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def load_history(db: Session, conv: Conversation) -> list[dict[str, str]]:
    """Load recent messages from DB as OpenAI-format dicts."""
    messages = sorted(conv.messages, key=lambda m: m.created_at)
    # Keep only the most recent N messages
    recent = messages[-MAX_CONTEXT_MESSAGES:]

    history: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in recent:
        history.append({"role": msg.role, "content": msg.content})
    return history


def save_message(
    db: Session,
    conv: Conversation,
    role: str,
    content: str,
    map_data: dict | None = None,
    weather_data: dict | None = None,
) -> Message:
    """Persist a message and update conversation timestamp."""
    msg = Message(conversation_id=conv.id, role=role, content=content)
    if map_data is not None:
        msg.map_data = json.dumps(map_data, ensure_ascii=False)
    if weather_data is not None:
        msg.weather_data = json.dumps(weather_data, ensure_ascii=False)
    db.add(msg)
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(msg)
    return msg


async def chat_stream(
    db: Session,
    conv: Conversation,
    user_message: str,
    user_lat: float | None = None,
    user_lon: float | None = None,
) -> AsyncGenerator[Any, None]:
    """Process a user message and yield response chunks (streaming).

    Yields:
      - str: text chunks for the assistant response
      - dict: {"type": "map", "data": {...}} for map rendering in frontend
    """
    # 1. Build context
    messages = load_history(db, conv)
    messages.append({"role": "user", "content": user_message})

    # 2. Non-streaming call with tools to check if search/map is needed
    full_response = ""
    saved_map_data: dict | None = None
    saved_weather_data: dict | None = None
    try:
        resp = await llm_client.chat_with_tools(
            messages=messages,
            tools=ALL_TOOLS,
            temperature=0.2,
        )
    except LLMError as e:
        yield f"[错误] LLM 调用失败: {e}"
        return

    choice = resp.get("choices", [{}])[0]
    msg = choice.get("message", {})

    # 3a. Tool calling path
    tool_calls = msg.get("tool_calls")
    if tool_calls:
        # Add the assistant's tool-call message to context
        messages.append(msg)

        for tc in tool_calls:
            fn = tc.get("function", {})
            fn_name = fn.get("name", "")
            fn_args_str = fn.get("arguments", "{}")

            try:
                fn_args = json.loads(fn_args_str)
            except json.JSONDecodeError:
                fn_args = {"query": fn_args_str}

            # Handle map_search tool specially (needs user location)
            if fn_name == "map_search":
                place = fn_args.get("place", "")
                try:
                    map_data = await map_search(
                        place=place,
                        user_lat=user_lat,
                        user_lon=user_lon,
                    )
                    # Yield map data to frontend for rendering
                    saved_map_data = map_data
                    yield {"type": "map", "data": map_data}
                    # Convert to text for LLM context
                    tool_result = map_result_to_text(map_data)
                except Exception as e:
                    tool_result = f"地图查询失败: {e}"

            # Handle weather_search specially (needs user location fallback + frontend card)
            elif fn_name == "weather_search":
                place = fn_args.get("place", "")
                try:
                    weather_data = await weather_search(
                        place=place,
                        user_lat=user_lat,
                        user_lon=user_lon,
                    )
                    saved_weather_data = weather_data
                    # Yield weather data to frontend for rendering
                    yield {"type": "weather", "data": weather_data}
                    # Convert to text for LLM context
                    tool_result = weather_result_to_text(weather_data)
                except Exception as e:
                    tool_result = f"天气查询失败: {e}"

            # Handle web_search and other tools
            elif fn_name in TOOL_EXECUTORS:
                executor = TOOL_EXECUTORS[fn_name]
                try:
                    tool_result = await executor(**fn_args)
                except SearchError as e:
                    tool_result = f"搜索失败: {e}"
            else:
                tool_result = f"工具 {fn_name} 不可用"

            # Add tool result to context (OpenAI tool message format)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": tool_result,
            })

        # 4. Streaming call with tool results to generate final answer
        try:
            async for chunk in llm_client.chat_stream(
                messages=messages,
                temperature=0.7,
            ):
                full_response += chunk
                yield chunk
        except LLMError as e:
            yield f"\n[错误] 生成回复失败: {e}"
    else:
        # 3b. No tool needed - yield content directly
        full_response = msg.get("content", "")
        if full_response:
            yield full_response
        else:
            # Fallback: streaming call without tools
            try:
                async for chunk in llm_client.chat_stream(messages=messages):
                    full_response += chunk
                    yield chunk
            except LLMError as e:
                yield f"[错误] 生成回复失败: {e}"

    # 5. Persist the assistant response (save even if only map/weather data)
    if full_response.strip() or saved_map_data is not None or saved_weather_data is not None:
        save_message(
            db, conv, "assistant", full_response,
            map_data=saved_map_data,
            weather_data=saved_weather_data,
        )
