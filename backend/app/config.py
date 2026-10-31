from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime configuration, overridable with PLA_* environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="PLA_",
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Personal Life Assistant API"
    app_version: str = "0.2.0"
    debug: bool = False
    api_prefix: str = "/api/v1"
    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'life_assistant.db'}"

    # Comma-separated origins. "null" is the Origin header used by file://
    # pages in packaged Electron builds.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,null"

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
