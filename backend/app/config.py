import logging
import shutil
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"

logger = logging.getLogger(__name__)

# Order used by AI_PROVIDER=auto (claude_code only when a token is in .env).
PROVIDERS = ("claude", "claude_code", "cursor", "openai")

_ALIASES = {
    "anthropic": "claude",
    "claude_api": "claude",
    "claude-api": "claude",
    "claude-code": "claude_code",
    "claudecode": "claude_code",
    "subscription": "claude_code",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Crypto Chart AI"
    default_exchange: str = "BINANCE"
    default_timeframe: str = "1h"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # claude | claude_code | cursor | openai | none | auto. The start scripts ask
    # and write this; auto picks the first configured provider in PROVIDERS order.
    ai_provider: str = "auto"

    # Claude API (pay per token) — https://console.anthropic.com/settings/keys
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-5-5"
    # low | medium | high | xhigh | max — leave blank for models without effort support
    anthropic_effort: str = "medium"

    # Claude subscription via the local Claude Code CLI (Pro / Max plan usage).
    # Uses the CLI's own login, or a long-lived token from `claude setup-token`.
    claude_code_oauth_token: str | None = None
    claude_code_model: str = ""  # blank = your plan's default; or opus / sonnet / a full model id
    claude_code_effort: str = "medium"
    claude_code_path: str | None = None  # blank = find `claude` on PATH
    claude_code_timeout: int = 300

    # Cursor agents — https://cursor.com/dashboard/integrations
    cursor_api_key: str | None = None
    cursor_model: str = "composer-2.5"

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    marketaux_api_token: str | None = None
    # Optional: Coinglass key for real liquidation history (estimated map works without it)
    coinglass_api_key: str | None = None

    # SQLite file for journal, signals and later tables; blank = backend/data/app.db
    db_path: str = ""
    # Folder for the daily backup job; blank = <repo>/backups
    backup_dir: str = ""

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


def get_settings() -> Settings:
    # Re-read .env each call so key changes apply without a full restart.
    return Settings()


def looks_like_real_key(value: str | None, *prefixes: str) -> bool:
    if not value:
        return False
    v = value.strip().strip('"').strip("'")
    if not v or v.endswith("...") or "your_" in v.lower() or "replace" in v.lower():
        return False
    if any(v.startswith(p) for p in prefixes):
        return True
    return len(v) > 20


def claude_cli(settings: Settings) -> str | None:
    """Path to the Claude Code CLI, or None when it isn't installed."""
    configured = (settings.claude_code_path or "").strip()
    if configured:
        return configured if Path(configured).exists() else shutil.which(configured)
    return shutil.which("claude")


def normalize_provider(value: str | None) -> str:
    v = (value or "auto").strip().lower()
    return _ALIASES.get(v, v)


def is_configured(settings: Settings, provider: str) -> bool:
    if provider == "claude":
        return looks_like_real_key(settings.anthropic_api_key, "sk-ant-")
    if provider == "claude_code":
        # The CLI login is checked when the call runs; here we only need the CLI.
        return claude_cli(settings) is not None
    if provider == "cursor":
        # Cursor dashboard keys use crsr_ (also accept legacy cursor_)
        return looks_like_real_key(settings.cursor_api_key, "crsr_", "cursor_")
    if provider == "openai":
        return looks_like_real_key(settings.openai_api_key, "sk-")
    return False


def resolve_provider(settings: Settings) -> str:
    pinned = normalize_provider(settings.ai_provider)
    if pinned == "none":
        return "none"
    if pinned in PROVIDERS:
        if is_configured(settings, pinned):
            return pinned
        logger.warning("AI_PROVIDER=%s is selected but not configured - running without AI", pinned)
        return "none"
    for provider in PROVIDERS:
        if provider == "claude_code" and not looks_like_real_key(settings.claude_code_oauth_token):
            continue  # auto never spends subscription usage without an explicit token
        if is_configured(settings, provider):
            return provider
    return "none"


def provider_model(settings: Settings, provider: str) -> str | None:
    return {
        "claude": settings.anthropic_model,
        "claude_code": settings.claude_code_model or "plan default",
        "cursor": settings.cursor_model,
        "openai": settings.openai_model,
    }.get(provider)
