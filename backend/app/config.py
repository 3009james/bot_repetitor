from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str
    admin_telegram_id: int
    app_url: str
    database_url: str
    app_timezone: str = "Europe/Moscow"
    upload_dir: str = "/app/data/uploads"
    teacher_telegram_username: str | None = None
    dev_bypass_auth: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
