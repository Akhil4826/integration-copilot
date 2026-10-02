from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "testing", "production"] = "development"
    app_name: str = "Integration Copilot"
    app_version: str = "0.1.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Authentication & Security
    api_auth_token: str = "dev-secret-token-12345"
    admin_auth_token: str = "admin-secret-token-67890"

    # LLM Settings
    llm_provider: Literal["ollama", "mock"] = "ollama"
    llm_model: str = "qwen3:4b"
    ollama_base_url: str = "http://localhost:11434"
    llm_timeout_seconds: float = 60.0

    # Database Settings
    database_url: str = "sqlite:///./data/app.db"

    # Agent Limits & Guardrails
    max_agent_steps: int = 8
    max_tool_retries: int = 2
    rate_limit_per_minute: int = 30

    # Observability
    log_level: str = "INFO"


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
