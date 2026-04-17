from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Part 6 Production Agent"
    app_version: str = "1.0.0"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    redis_url: str = "redis://redis:6379/0"
    agent_api_key: str = Field(default="change-me-in-production", alias="AGENT_API_KEY")
    allowed_origins: str = "*"

    rate_limit_per_minute: int = 10
    monthly_budget_usd: float = 10.0
    history_ttl_seconds: int = 86400
    max_history_messages: int = 20

    llm_provider: str = "mock"
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


settings = Settings()
