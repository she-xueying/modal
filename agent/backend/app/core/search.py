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
                    "description": "搜索关键词，用中文或英文描述要搜索的内容；先纠正错别字再用准确关键词",
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
                    "description": "要查询的地点名称，如城市名、地标名等；用户输入的地点名可能含错别字，请先纠正为正确名称再传入",
                },
            },
            "required": ["place"],
        },
    },
}

WEATHER_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "weather_search",
        "description": (
            "当用户询问任何关于天气的问题（包括当前天气、气温、湿度、风力、降雨、空气质量、"
            "今日或未来预报、是否适合出门/运动等）时，必须调用此工具获取实时天气，"
            "不要根据训练知识编造天气数据。例如：'北京天气怎么样'、'明天上海会下雨吗'、'今天适合出门吗'。"
            "如果用户没有指定地点（如'今天天气怎么样'），可不传 place，将使用用户所在位置查询。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "place": {
                    "type": "string",
                    "description": "要查询天气的地点名称（城市、区县、地标等），用户未指定地点时可省略；地点名含错别字时先纠正为正确名称再传入",
                },
            },
            "required": [],
        },
    },
}

DOCX_EDIT_TOOL = {
    "type": "function",
    "function": {
        "name": "docx_edit",
        "description": (
            "当用户上传了 .docx 文档并要求修改文档中的某处内容时，调用此工具修改文档。"
            "文档内容已在上文以[段落索引]形式给出（文件ID也会给出）。"
            "用 paragraph_index 指定要改的段落（对应上文[索引]），new_text 填修改后的完整段落内容（会替换整段）。"
            "注意：用户描述的目标文字可能含错别字，应根据文档实际内容选择正确的段落；"
            "若不确定段落索引，可用 match_text 填该段落包含的关键文字（取文档中实际存在的正确文本），系统会模糊定位到该段。"
            "修改后系统会生成一个新的文档供用户下载，原文档不会被改动。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "用户上传文档的文件ID（上文已给出）",
                },
                "paragraph_index": {
                    "type": "integer",
                    "description": "要修改的段落索引，从0开始，对应上文[索引]；与 match_text 二选一",
                },
                "match_text": {
                    "type": "string",
                    "description": "要修改段落包含的关键文字（用文档中实际存在的正确文本），用于模糊定位；与 paragraph_index 二选一",
                },
                "new_text": {
                    "type": "string",
                    "description": "修改后该段落的完整新内容（用纠正后的正确内容）",
                },
            },
            "required": ["file_id", "new_text"],
        },
    },
}

ALL_TOOLS = [WEB_SEARCH_TOOL, MAP_SEARCH_TOOL, WEATHER_SEARCH_TOOL, DOCX_EDIT_TOOL]


# Map tool names to their async executor functions
# map_search is handled specially in chat_service because it needs user location
TOOL_EXECUTORS = {
    "web_search": tavily_search,
}
