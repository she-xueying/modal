"""Memory service: extract, store, and inject cross-conversation memories.

Write path: after each assistant response, call LLM to extract memorable facts.
Read path: before each LLM call, fetch memories and append to system prompt.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading

from sqlalchemy.orm import Session

from app.core.llm import LLMError, LLMClient
from app.models.database import Memory, SessionLocal

logger = logging.getLogger(__name__)


# Category labels for prompt formatting
_CATEGORY_LABELS = {
    "personal_info": "个人信息",
    "preference": "偏好",
    "fact": "事实",
    "context": "上下文",
}

# Extraction prompt - short and focused to minimize token cost
_EXTRACT_PROMPT = (
    "从以下对话中提取值得长期记忆的用户信息。\n"
    "只提取用户明确表达的事实，不要猜测或推断。\n"
    "分类：personal_info（姓名/城市/职业等）、preference（喜好/习惯）、fact（重要事实）、context（正在做的事）\n"
    "返回 JSON 数组，每项格式：{{\"category\": \"...\", \"content\": \"...\"}}\n"
    "没有值得记忆的内容则返回 []\n\n"
    "用户说：{user_msg}\n"
    "助手回复：{assistant_msg}"
)

# Skip extraction for very short messages (likely not containing memorable info)
_MIN_MSG_LEN = 10


async def _extract_with_client(client, user_message: str, assistant_response: str) -> list[dict[str, str]]:
    """Call LLM to extract memorable facts from a single exchange."""
    if len(user_message.strip()) < _MIN_MSG_LEN:
        return []

    prompt = _EXTRACT_PROMPT.format(
        user_msg=user_message[:500],
        assistant_msg=assistant_response[:500],
    )

    try:
        resp = await client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=512,
        )
    except LLMError as e:
        logger.warning("Memory extraction LLM call failed: %s", e)
        return []

    try:
        content = resp["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
        memories = json.loads(content)
        if not isinstance(memories, list):
            return []
        result: list[dict[str, str]] = []
        for item in memories:
            if isinstance(item, dict) and "content" in item:
                cat = item.get("category", "fact")
                if cat not in _CATEGORY_LABELS:
                    cat = "fact"
                result.append({"category": cat, "content": str(item["content"]).strip()})
        return result
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
        logger.warning("Memory extraction parse failed: %s", e)
        return []


def get_all_memories(db: Session, limit: int = 50) -> list[Memory]:
    """Fetch recent memories, newest first."""
    return (
        db.query(Memory)
        .order_by(Memory.updated_at.desc())
        .limit(limit)
        .all()
    )


def build_memory_prompt(memories: list[Memory]) -> str:
    """Format memories into a natural-language block for the system prompt."""
    if not memories:
        return ""
    lines: list[str] = []
    for m in memories:
        label = _CATEGORY_LABELS.get(m.category, m.category)
        lines.append(f"- [{label}] {m.content}")
    return (
        "以下是关于用户的长期记忆，请在回复时自然地参考这些信息"
        "（不要生硬地罗列，而是在相关时自然地使用）：\n"
        + "\n".join(lines)
    )


def _extract_and_save(conversation_id: str, user_message: str, assistant_response: str) -> None:
    """Run extraction + save in its own event loop (called from a daemon thread)."""
    async def run() -> None:
        client = LLMClient()
        try:
            memories = await _extract_with_client(client, user_message, assistant_response)
            if not memories:
                return
            db: Session = SessionLocal()
            try:
                for m in memories:
                    db.add(Memory(
                        category=m["category"],
                        content=m["content"],
                        source_conversation_id=conversation_id,
                    ))
                db.commit()
                logger.info("Saved %d memories from conversation %s", len(memories), conversation_id)
            except Exception as e:
                logger.error("Failed to save memories: %s", e)
                db.rollback()
            finally:
                db.close()
        finally:
            await client.close()

    asyncio.run(run())


def schedule_extraction(conversation_id: str, user_message: str, assistant_response: str) -> None:
    """Schedule memory extraction in a background daemon thread (fire-and-forget)."""
    if len((user_message or "").strip()) < _MIN_MSG_LEN:
        return
    t = threading.Thread(
        target=_extract_and_save,
        args=(conversation_id, user_message, assistant_response),
        daemon=True,
    )
    t.start()
