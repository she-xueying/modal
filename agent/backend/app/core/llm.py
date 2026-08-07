"""LLM client wrapper for GLM-4V (Zhipu AI) with sync + streaming + tool calling.

Uses the OpenAI-compatible API endpoint.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from app.config import settings


class LLMError(Exception):
    """Raised when the LLM API call fails."""


class LLMClient:
    """Thin async wrapper around the GLM-4V API (OpenAI-compatible)."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or settings.glm_api_key
        self.base_url = (base_url or settings.glm_base_url).rstrip("/")
        self.model = model or settings.glm_model
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._client

    # ------------------------------------------------------------------ #
    #  Non-streaming chat
    # ------------------------------------------------------------------ #

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Synchronous (non-streaming) chat completion.

        Returns the full response dict from the API.
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        resp = await self.client.post("/chat/completions", json=payload)
        if resp.status_code != 200:
            raise LLMError(f"LLM API error {resp.status_code}: {resp.text}")

        return resp.json()

    # ------------------------------------------------------------------ #
    #  Streaming chat
    # ------------------------------------------------------------------ #

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Streaming chat completion. Yields content delta strings."""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        async with self.client.stream(
            "POST", "/chat/completions", json=payload
        ) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise LLMError(
                    f"LLM API error {resp.status_code}: {body.decode()}"
                )

            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:]  # strip "data: " prefix
                if data.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue

    # ------------------------------------------------------------------ #
    #  Tool-calling chat
    # ------------------------------------------------------------------ #

    async def chat_with_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict],
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Chat completion with tool/function calling support.

        Returns the full response. The caller is responsible for
        executing any tool calls and re-invoking if needed.
        """
        return await self.chat(
            messages=messages,
            temperature=temperature,
            tools=tools,
        )

    async def close(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# Module-level singleton
llm_client = LLMClient()
