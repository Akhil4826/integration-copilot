"""Unit tests for OllamaProvider, message formatting, and LLM factory."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.config import Settings
from app.llm.base import LLMMessage, LLMToolCall
from app.llm.factory import get_llm_provider
from app.llm.mock_provider import MockLLMProvider
from app.llm.ollama_provider import OllamaProvider


class TestOllamaProvider:
    def test_format_messages(self):
        provider = OllamaProvider(base_url="http://localhost:11434", model="qwen3:4b")
        messages = [
            LLMMessage(role="system", content="System instruction"),
            LLMMessage(
                role="assistant",
                content="Calling tool",
                tool_calls=[
                    LLMToolCall(
                        id="c1", name="get_customer", arguments={"customer_id": "CUST-1004"}
                    )
                ],
            ),
            LLMMessage(
                role="tool", content='{"name": "Patricia"}', name="get_customer", tool_call_id="c1"
            ),
        ]
        formatted = provider._format_messages_for_ollama(messages)
        assert len(formatted) == 3
        assert formatted[0]["role"] == "system"
        assert formatted[1]["tool_calls"][0]["function"]["name"] == "get_customer"

    @pytest.mark.asyncio
    async def test_health_check_success_and_failure(self):
        provider = OllamaProvider(base_url="http://localhost:11434")

        # Mock success
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            assert await provider.health_check() is True

        # Mock connection error
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused")
            assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self):
        provider = OllamaProvider(base_url="http://localhost:11434", max_retries=1)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            # First fails with ConnectError, second succeeds
            mock_post.side_effect = [
                httpx.ConnectError("Transient connection drop"),
                MagicMock(
                    status_code=200,
                    json=lambda: {
                        "message": {
                            "role": "assistant",
                            "content": "Success response",
                            "tool_calls": [],
                        },
                        "done": True,
                    },
                    raise_for_status=lambda: None,
                ),
            ]

            resp = await provider.generate([LLMMessage(role="user", content="Hello")])
            assert resp.content == "Success response"
            assert mock_post.call_count == 2

    def test_llm_factory(self):
        mock_settings = Settings(llm_provider="mock", llm_model="test-mock")
        provider = get_llm_provider(mock_settings)
        assert isinstance(provider, MockLLMProvider)

        ollama_settings = Settings(llm_provider="ollama", llm_model="qwen3:4b")
        provider = get_llm_provider(ollama_settings)
        assert isinstance(provider, OllamaProvider)
