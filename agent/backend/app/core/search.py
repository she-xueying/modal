"""Web search + map tools for LLM function calling."""

from __future__ import annotations

import httpx

from app.config import settings
from app.core.map_service import map_search, map_result_to_text, MapError


class SearchError(Exception):
    """Raised when the search API call fails."""


async def tavily_search(query: str, max_results: int = 5) -> str:
    """Search the web using Tavily API.

    Returns a formatted string with search results that can be
    injected into the LLM context.
    """
    key = (settings.tavily_api_key or "").strip()
    if not key or key.startswith("your_") or "your_tavily" in key:
        raise SearchError("TAVILY_API_KEY is not configured (set it in backend/.env)")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": settings.tavily_api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "advanced",
                "include_answer": True,
            },
        )
        if resp.status_code != 200:
            raise SearchError(f"Tavily API error {resp.status_code}: {resp.text}")

        data = resp.json()

    # Build a readable context string
    parts: list[str] = []

    # Tavily returns a direct answer
    direct_answer = data.get("answer")
    if direct_answer:
        parts.append(f"搜索摘要: {direct_answer}\n")

    # Append individual results
    for i, result in enumerate(data.get("results", []), 1):
        title = result.get("title", "无标题")
        url = result.get("url", "")
        snippet = result.get("content", "")
        parts.append(f"[{i}] {title}\n   链接: {url}\n   内容: {snippet}\n")

    return "\n".join(parts) if parts else "未找到相关搜索结果。"


# --------------------------------------------------------------------------- #
#  Tool definition for LLM function calling (OpenAI tools format)
# --------------------------------------------------------------------------- #

WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "当用户询问实时信息（如天气、新闻、股价、体育比赛结果、最新动态等）时，"
            "调用此工具进行联网搜索。对于通识知识、编程、写作等不需要实时信息的问题，"
            "不要调用此工具。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，用中文或英文描述要搜索的内容",
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回结果数量，默认5",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}

MAP_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "map_search",
        "description": (
            "当用户询问某个地点在哪里、想查看地图、或询问某地的当前时间和出行方式时，"
            "调用此工具查询地点信息。会返回地点坐标、当地时间、以及从用户位置出发的出行时间。"
            "例如：'北京在哪里'、'巴黎现在几点'、'去上海要多久'等。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "place": {
                    "type": "string",
                    "description": "要查询的地点名称，如城市名、地标名等",
                },
            },
            "required": ["place"],
        },
    },
}

ALL_TOOLS = [WEB_SEARCH_TOOL, MAP_SEARCH_TOOL]


# Map tool names to their async executor functions
# map_search is handled specially in chat_service because it needs user location
TOOL_EXECUTORS = {
    "web_search": tavily_search,
}
