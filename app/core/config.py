from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    app_name: str = "Lanari Candle"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api"
    allowed_origins: List[str] = []

    # dodaj to:
    secret_key: str = "change-me"
    database_url: str = "sqlite:///local.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # opcjonalnie: ignoruje nieznane zmienne z .env
    )


settings = Settings()
