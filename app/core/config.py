from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    test_database_url: str | None = None
    jwt_secret_key: str = Field(min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    cors_allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    exchange_rate_provider_base_url: str = "https://dolarapi.com/v1"
    exchange_rate_ttl_seconds: int = 60 * 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
