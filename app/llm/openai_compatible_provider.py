"""OpenAI-compatible LLM Provider implementation for free cloud inference (e.g. Groq, OpenRouter)."""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, cast

import httpx

from app.core.logging import logger
from app.core.metrics import LLM_REQUEST_DURATION_SECONDS, LLM_REQUESTS_TOTAL
from app.llm.base import LLMMessage, LLMProvider, LLMResponse, LLMToolCall


class OpenAICompatibleProvider(LLMProvider):
    """Integrates with any OpenAI-compatible endpoint (Groq, OpenRouter, vLLM, etc.)."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.groq.com/openai/v1",
        model: str = "llama-3.1-8b-instant",
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def _format_messages(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        formatted = []
        for m in messages:
            entry: Dict[str, Any] = {"role": m.role, "content": m.content or ""}
            if m.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.id or f"call_{i}",
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                            if isinstance(tc.arguments, dict)
                            else str(tc.arguments),
                        },
                    }
                    for i, tc in enumerate(m.tool_calls)
                ]
            if m.tool_call_id:
                entry["tool_call_id"] = m.tool_call_id
            if m.name and m.role == "tool":
                entry["name"] = m.name
            formatted.append(entry)
        return formatted

    async def _post_chat_with_retry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.is_error:
                        err_text = resp.text
                        logger.error(
                            f"Cloud LLM HTTP {resp.status_code} Error: {err_text}",
                            extra={"status_code": resp.status_code, "response_body": err_text},
                        )
                        raise ConnectionError(f"Cloud LLM error ({resp.status_code}): {err_text}")
                    return cast(Dict[str, Any], resp.json())
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    backoff = 0.5 * (2**attempt)
                    logger.warning(
                        f"Cloud LLM request failed (attempt {attempt + 1}/{self.max_retries + 1}): {exc}. "
                        f"Retrying in {backoff:.1f}s..."
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        f"Cloud LLM request failed after {self.max_retries + 1} attempts: {exc}"
                    )

        raise ConnectionError(f"Failed to communicate with Cloud LLM endpoint: {last_error}")

    async def generate(self, messages: List[LLMMessage], **kwargs: Any) -> LLMResponse:
        start_time = time.perf_counter()
        payload = {
            "model": self.model,
            "messages": self._format_messages(messages),
            "temperature": kwargs.get("temperature", 0.0),
        }
        res_data = await self._post_chat_with_retry(payload)
        duration = time.perf_counter() - start_time

        LLM_REQUESTS_TOTAL.labels(model=self.model, status="success").inc()
        LLM_REQUEST_DURATION_SECONDS.labels(model=self.model).observe(duration)

        choice = res_data.get("choices", [{}])[0]
        msg = choice.get("message", {})

        return LLMResponse(
            content=msg.get("content"),
            tool_calls=None,
            finish_reason=choice.get("finish_reason", "stop"),
            model=self.model,
            duration_seconds=round(duration, 3),
        )

    async def generate_with_tools(
        self,
        messages: List[LLMMessage],
        tools: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> LLMResponse:
        start_time = time.perf_counter()

        formatted_tools = []
        for t in tools:
            if "function" in t:
                # Already wrapped in OpenAI tool format {"type": "function", "function": {...}}
                fn = t["function"]
                formatted_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": fn.get("name"),
                            "description": fn.get("description", ""),
                            "parameters": fn.get(
                                "parameters", {"type": "object", "properties": {}}
                            ),
                        },
                    }
                )
            else:
                formatted_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": t.get("name"),
                            "description": t.get("description", ""),
                            "parameters": t.get("parameters", {"type": "object", "properties": {}}),
                        },
                    }
                )

        payload = {
            "model": self.model,
            "messages": self._format_messages(messages),
            "tools": formatted_tools,
            "tool_choice": "auto",
            "temperature": kwargs.get("temperature", 0.0),
        }

        res_data = await self._post_chat_with_retry(payload)
        duration = time.perf_counter() - start_time

        LLM_REQUESTS_TOTAL.labels(model=self.model, status="success").inc()
        LLM_REQUEST_DURATION_SECONDS.labels(model=self.model).observe(duration)

        choice = res_data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        raw_tool_calls = msg.get("tool_calls")

        parsed_tool_calls: Optional[List[LLMToolCall]] = None
        if raw_tool_calls:
            parsed_tool_calls = []
            for tc in raw_tool_calls:
                fn = tc.get("function", {})
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                parsed_tool_calls.append(
                    LLMToolCall(
                        id=tc.get("id", ""),
                        name=fn.get("name", ""),
                        arguments=args,
                    )
                )

        return LLMResponse(
            content=msg.get("content"),
            tool_calls=parsed_tool_calls,
            finish_reason=choice.get("finish_reason", "stop"),
            model=self.model,
            duration_seconds=round(duration, 3),
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return resp.status_code == 200
        except Exception:
            return False
