from secrets import token_urlsafe
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./apiforge.db"
    log_level: str = "INFO"
    environment: Literal["development", "test", "production"] = "development"
    jwt_secret: SecretStr = Field(default_factory=lambda: SecretStr(token_urlsafe(48)))
    token_minutes: int = Field(default=30, ge=1, le=120)
    cors_origins: list[str] = []
    auth_rate_limit: int = Field(default=10, ge=1, le=1000)
    max_request_bytes: int = Field(default=262144, ge=1024, le=1048576)
    ai_enabled: bool = False
    ai_allow_external: bool = False
    ai_provider: Literal["openai", "mock"] = "openai"
    ai_base_url: str = "https://api.openai.com/v1"
    ai_api_key: SecretStr | None = None
    ai_model: str = "gpt-4o-mini"
    ai_timeout_seconds: float = Field(default=15, ge=0.1, le=60)
    ai_retries: int = Field(default=1, ge=0, le=2)

    @model_validator(mode="after")
    def validate_security(self):
        if len(self.jwt_secret.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters")
        if "*" in self.cors_origins:
            raise ValueError("Use explicit CORS origins")
        if self.environment == "production":
            if "jwt_secret" not in self.model_fields_set:
                raise ValueError("Production requires an explicit JWT_SECRET")
            if not self.database_url.startswith("postgresql+psycopg://"):
                raise ValueError("Production requires PostgreSQL")
            if any(not o.startswith("https://") for o in self.cors_origins):
                raise ValueError("Production CORS origins must use HTTPS")
            if self.ai_enabled and self.ai_provider == "mock":
                raise ValueError("Mock AI is limited to development and tests")
        if self.ai_enabled and self.ai_provider == "openai":
            if not self.ai_allow_external or not self.ai_api_key:
                raise ValueError("AI requires explicit external transmission opt-in and an API key")
            if not self.ai_base_url.startswith("https://"):
                raise ValueError("AI provider URL must use HTTPS")
        return self


settings = Settings()
