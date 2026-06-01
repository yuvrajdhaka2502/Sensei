from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    user_id: str = Field(default="primary")
    telegram_bot_token: str
    gemini_api_key: str
    vault_path: Path = Field(default=Path("./vault"))
    db_path: Path = Field(default=Path("./state.sqlite"))
    timezone: str = Field(default="Asia/Kolkata")
    gemini_model: str = Field(default="gemini-2.0-flash")
    log_level: str = Field(default="INFO")

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
