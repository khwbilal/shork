"""choose_provider.set_env_values: in-place .env updates (tmp file only)."""

from __future__ import annotations

import pytest

from app import choose_provider


@pytest.fixture
def env_file(monkeypatch, tmp_path):
    path = tmp_path / ".env"
    monkeypatch.setattr(choose_provider, "ENV_FILE", path)
    return path


def lines(path):
    return path.read_text(encoding="utf-8").splitlines()


def test_creates_missing_file(env_file):
    choose_provider.set_env_values({"AI_PROVIDER": "none"})
    assert env_file.read_text(encoding="utf-8") == "AI_PROVIDER=none\n"


def test_updates_existing_and_preserves_other_lines(env_file):
    env_file.write_text(
        "# comment line\nAI_PROVIDER=claude\n\nOPENAI_MODEL=gpt-4o-mini\n  ANTHROPIC_API_KEY = old\n",
        encoding="utf-8",
    )
    choose_provider.set_env_values({"AI_PROVIDER": "claude_code", "ANTHROPIC_API_KEY": "new"})
    assert lines(env_file) == [
        "# comment line",
        "AI_PROVIDER=claude_code",
        "",
        "OPENAI_MODEL=gpt-4o-mini",
        "ANTHROPIC_API_KEY=new",
    ]


def test_appends_missing_keys_in_order(env_file):
    env_file.write_text("AI_PROVIDER=none\n", encoding="utf-8")
    choose_provider.set_env_values({"AI_PROVIDER": "openai", "OPENAI_API_KEY": "k1", "OPENAI_MODEL": "m"})
    assert lines(env_file) == ["AI_PROVIDER=openai", "OPENAI_API_KEY=k1", "OPENAI_MODEL=m"]


def test_every_duplicate_is_updated(env_file):
    env_file.write_text("AI_PROVIDER=claude\nX=1\nAI_PROVIDER=cursor\n", encoding="utf-8")
    choose_provider.set_env_values({"AI_PROVIDER": "none"})
    assert lines(env_file) == ["AI_PROVIDER=none", "X=1", "AI_PROVIDER=none"]


def test_commented_key_is_left_alone(env_file):
    env_file.write_text("# AI_PROVIDER=claude\n", encoding="utf-8")
    choose_provider.set_env_values({"AI_PROVIDER": "none"})
    assert lines(env_file) == ["# AI_PROVIDER=claude", "AI_PROVIDER=none"]


def test_file_without_trailing_newline(env_file):
    env_file.write_text("A=1", encoding="utf-8")
    choose_provider.set_env_values({"B": "2"})
    assert env_file.read_text(encoding="utf-8") == "A=1\nB=2\n"
