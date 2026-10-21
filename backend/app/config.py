from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Crypto Chart AI"
    default_exchange: str = "BINANCE"
    default_timeframe: str = "1h"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Prefer Cursor (same agent runtime as the IDE). Falls back to OpenAI.
    cursor_api_key: str | None = None
    cursor_model: str = "composer-2.5"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    marketaux_api_token: str | None = None
    # Optional: Coinglass key for real liquidation history (estimated map works without it)
    coinglass_api_key: str | None = None

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


def get_settings() -> Settings:
    # Re-read .env each call so key changes apply without a full restart.
    return Settings()


def _looks_like_real_key(value: str | None, *prefixes: str) -> bool:
    if not value:
        return False
    v = value.strip().strip('"').strip("'")
    if not v or v.endswith("...") or "your_" in v.lower() or "replace" in v.lower():
        return False
    if any(v.startswith(p) for p in prefixes):
        return True
    return len(v) > 20


def resolve_provider(settings: Settings) -> str:
    # Cursor dashboard keys use crsr_ (also accept legacy cursor_)
    if _looks_like_real_key(settings.cursor_api_key, "crsr_", "cursor_"):
        return "cursor"
    if _looks_like_real_key(settings.openai_api_key, "sk-"):
        return "openai"
    return "none"
