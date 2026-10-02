"""Factory for instantiating the configured LLM provider."""

from app.core.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.llm.ollama_provider import OllamaProvider


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Return configured LLM provider instance."""
    app_settings = settings or get_settings()

    if app_settings.llm_provider == "mock":
        return MockLLMProvider(model=app_settings.llm_model)
    elif app_settings.llm_provider == "ollama":
        return OllamaProvider(
            base_url=app_settings.ollama_base_url,
            model=app_settings.llm_model,
            timeout_seconds=app_settings.llm_timeout_seconds,
            max_retries=app_settings.max_tool_retries,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {app_settings.llm_provider}")
