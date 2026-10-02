from app.core.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.openai_compatible_provider import OpenAICompatibleProvider


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
    elif app_settings.llm_provider in ("groq", "openai_compatible"):
        base_url = (
            "https://api.groq.com/openai/v1"
            if app_settings.llm_provider == "groq"
            else app_settings.openai_api_base
        )
        model = (
            "llama-3.1-8b-instant"
            if app_settings.llm_provider == "groq" and app_settings.llm_model == "qwen3:4b"
            else app_settings.llm_model
        )
        return OpenAICompatibleProvider(
            api_key=app_settings.groq_api_key,
            base_url=base_url,
            model=model,
            timeout_seconds=app_settings.llm_timeout_seconds,
            max_retries=app_settings.max_tool_retries,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {app_settings.llm_provider}")
