"""Async Ollama provider implementation."""

from __future__ import annotations

from collections.abc import Sequence

import httpx


class OllamaProvider:
    """LLM provider backed by Ollama's chat API."""

    def __init__(self, base_url: str = "http://localhost:11434", timeout: float = 60.0) -> None:
        self._api_url = f"{base_url.rstrip('/')}/api/chat"
        self._client = httpx.AsyncClient(timeout=timeout)

    async def generate(
        self,
        *,
        model_profile: str,
        system: str,
        messages: Sequence[dict[str, str]],
    ) -> str:
        payload = {
            "model": self._extract_model_name(model_profile),
            "stream": False,
            "messages": [{"role": "system", "content": system}, *messages],
        }
        response = await self._client.post(self._api_url, json=payload)
        response.raise_for_status()
        data = response.json()
        message = data.get("message", {})
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Ollama returned an empty response.")
        return content.strip()

    async def aclose(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _extract_model_name(model_profile: str) -> str:
        _, _, model_name = model_profile.partition("/")
        return model_name or model_profile
