"""Shared fixtures: keep every test offline and away from the real backend/.env."""

from __future__ import annotations

import httpx
import pytest

from app import choose_provider, config

_ENV_KEYS = (
    "AI_PROVIDER",
    "ANTHROPIC_API_KEY",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "CLAUDE_CODE_PATH",
    "CURSOR_API_KEY",
    "OPENAI_API_KEY",
    "DB_PATH",
    "BACKUP_DIR",
)


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    # Process env vars would override the explicit test values.
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    # Anything that still builds Settings() reads an empty tmp file, not backend/.env.
    fake_env = tmp_path / "fake.env"
    fake_env.write_text("", encoding="utf-8")
    monkeypatch.setitem(config.Settings.model_config, "env_file", str(fake_env))
    monkeypatch.setattr(choose_provider, "ENV_FILE", fake_env)
    # SQLite goes to a per-test file; the real backend/data/app.db is never opened.
    monkeypatch.setenv("DB_PATH", str(tmp_path / "data" / "app.db"))
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path / "backups"))

    def _no_network(*_args, **_kwargs):
        raise RuntimeError("network access is blocked in tests")

    monkeypatch.setattr(httpx.Client, "send", _no_network)
    monkeypatch.setattr(httpx.AsyncClient, "send", _no_network)


@pytest.fixture
def make_settings():
    """Settings built from explicit values only (no env file)."""

    def _make(**values):
        return config.Settings(_env_file=None, **values)

    return _make
