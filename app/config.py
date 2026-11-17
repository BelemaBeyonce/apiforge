from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./apiforge.db"
    log_level: str = "INFO"
    environment: str = "development"


settings = Settings()
