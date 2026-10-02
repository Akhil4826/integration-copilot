"""Ollama LLM Provider implementation with tool-calling and retry resilience."""

import asyncio
import json
import time
from typing import Any, Dict, List, cast

import httpx

from app.core.logging import logger
from app.core.metrics import LLM_REQUEST_DURATION_SECONDS, LLM_REQUESTS_TOTAL
from app.llm.base import LLMMessage, LLMProvider, LLMResponse, LLMToolCall


class OllamaProvider(LLMProvider):
    """Integrates with locally running Ollama instance via HTTP API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen3:4b",
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def _format_messages_for_ollama(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        formatted = []
        for m in messages:
            entry: Dict[str, Any] = {"role": m.role, "content": m.content or ""}
            if m.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": tc.arguments},
                    }
                    for tc in m.tool_calls
                ]
            formatted.append(entry)
        return formatted

    async def _post_chat_with_retry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/api/chat"
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    return cast(Dict[str, Any], resp.json())
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    backoff = 0.5 * (2**attempt)
                    logger.warning(
                        f"Ollama request failed (attempt {attempt + 1}/{self.max_retries + 1}): {exc}. "
                        f"Retrying in {backoff:.1f}s..."
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        f"Ollama request failed after {self.max_retries + 1} attempts: {exc}"
                    )

        raise ConnectionError(
            f"Failed to communicate with Ollama at {self.base_url} after {self.max_retries + 1} attempts: {last_error}"
        )

    async def generate(self, messages: List[LLMMessage], **kwargs: Any) -> LLMResponse:
        return await self.generate_with_tools(messages=messages, tools=[], **kwargs)

    async def generate_with_tools(
        self,
        messages: List[LLMMessage],
        tools: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> LLMResponse:
        start_time = time.perf_counter()
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": self._format_messages_for_ollama(messages),
            "stream": False,
            "options": {"temperature": kwargs.get("temperature", 0.0)},
        }

        if tools:
            payload["tools"] = tools

        try:
            data = await self._post_chat_with_retry(payload)
            duration = time.perf_counter() - start_time

            # Update metrics
            LLM_REQUESTS_TOTAL.labels(model=self.model, status="success").inc()
            LLM_REQUEST_DURATION_SECONDS.labels(model=self.model).observe(duration)

            msg = data.get("message", {})
            content = msg.get("content", "")
            raw_tool_calls = msg.get("tool_calls", [])

            parsed_tool_calls: List[LLMToolCall] = []
            for i, tc in enumerate(raw_tool_calls):
                fn = tc.get("function", {})
                name = fn.get("name", "")
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"raw": args}
                parsed_tool_calls.append(
                    LLMToolCall(
                        id=tc.get("id", f"call_{i}_{int(time.time() * 1000)}"),
                        name=name,
                        arguments=args if isinstance(args, dict) else {},
                    )
                )

            return LLMResponse(
                content=content or None,
                tool_calls=parsed_tool_calls if parsed_tool_calls else None,
                finish_reason="tool_calls" if parsed_tool_calls else "stop",
                model=self.model,
                duration_seconds=round(duration, 3),
                prompt_tokens=data.get("prompt_eval_count"),
                completion_tokens=data.get("eval_count"),
            )

        except Exception:
            duration = time.perf_counter() - start_time
            LLM_REQUESTS_TOTAL.labels(model=self.model, status="failure").inc()
            LLM_REQUEST_DURATION_SECONDS.labels(model=self.model).observe(duration)
            raise

    async def health_check(self) -> bool:
        """Check if Ollama service is reachable and responsive."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False
