"""config.resolve_provider: which AI provider runs."""

from __future__ import annotations

import pytest

from app import config

ANTHROPIC = "sk-ant-" + "x" * 30
OPENAI = "sk-" + "y" * 30
CURSOR = "crsr_" + "z" * 30
OAUTH = "sk-ant-oat01-" + "t" * 30


@pytest.fixture
def no_cli(monkeypatch):
    monkeypatch.setattr(config.shutil, "which", lambda _name: None)


@pytest.fixture
def with_cli(monkeypatch):
    monkeypatch.setattr(config.shutil, "which", lambda name: f"C:/fake/{name}.exe")


def test_none_always_wins(make_settings, with_cli):
    s = make_settings(ai_provider="none", anthropic_api_key=ANTHROPIC)
    assert config.resolve_provider(s) == "none"


@pytest.mark.parametrize(
    ("pinned", "values", "expected"),
    [
        ("claude", {"anthropic_api_key": ANTHROPIC}, "claude"),
        ("openai", {"openai_api_key": OPENAI}, "openai"),
        ("cursor", {"cursor_api_key": CURSOR}, "cursor"),
        ("cursor", {"cursor_api_key": "cursor_" + "a" * 30}, "cursor"),
    ],
)
def test_pinned_and_configured(make_settings, no_cli, pinned, values, expected):
    assert config.resolve_provider(make_settings(ai_provider=pinned, **values)) == expected


@pytest.mark.parametrize(
    ("pinned", "values"),
    [
        ("claude", {}),
        ("claude", {"anthropic_api_key": "sk-ant-..."}),
        ("claude", {"anthropic_api_key": "your_key_here"}),
        ("openai", {"openai_api_key": "short"}),
        ("cursor", {"cursor_api_key": "replace-me-with-a-real-key-please"}),
        ("claude_code", {}),
    ],
)
def test_pinned_but_not_configured_runs_without_ai(make_settings, no_cli, pinned, values):
    # A pinned provider never falls through to another one.
    other = {"openai_api_key": OPENAI} if pinned != "openai" else {"anthropic_api_key": ANTHROPIC}
    s = make_settings(ai_provider=pinned, **other, **values)
    assert config.resolve_provider(s) == "none"


def test_pinned_claude_code_needs_only_the_cli(make_settings, with_cli):
    assert config.resolve_provider(make_settings(ai_provider="claude_code")) == "claude_code"


def test_claude_code_path_setting(make_settings, monkeypatch, tmp_path):
    monkeypatch.setattr(config.shutil, "which", lambda _name: None)
    cli = tmp_path / "claude.exe"
    cli.write_text("", encoding="utf-8")
    s = make_settings(ai_provider="claude_code", claude_code_path=str(cli))
    assert config.resolve_provider(s) == "claude_code"
    s = make_settings(ai_provider="claude_code", claude_code_path=str(tmp_path / "missing.exe"))
    assert config.resolve_provider(s) == "none"


@pytest.mark.parametrize(
    ("alias", "expected"),
    [
        ("anthropic", "claude"),
        ("Claude_API", "claude"),
        ("claude-api", "claude"),
        ("claude-code", "claude_code"),
        ("claudecode", "claude_code"),
        ("subscription", "claude_code"),
        ("  NONE ", "none"),
        (None, "auto"),
        ("", "auto"),
    ],
)
def test_aliases(alias, expected):
    assert config.normalize_provider(alias) == expected


def test_alias_resolves(make_settings, with_cli):
    assert config.resolve_provider(make_settings(ai_provider="subscription")) == "claude_code"
    s = make_settings(ai_provider="anthropic", anthropic_api_key=ANTHROPIC)
    assert config.resolve_provider(s) == "claude"


def test_auto_order_prefers_claude_api(make_settings, with_cli):
    s = make_settings(
        ai_provider="auto",
        anthropic_api_key=ANTHROPIC,
        openai_api_key=OPENAI,
        cursor_api_key=CURSOR,
        claude_code_oauth_token=OAUTH,
    )
    assert config.resolve_provider(s) == "claude"


def test_auto_skips_claude_code_without_token(make_settings, with_cli):
    # The CLI is installed, but auto never spends subscription usage without a token.
    s = make_settings(ai_provider="auto", openai_api_key=OPENAI)
    assert config.resolve_provider(s) == "openai"
    assert config.resolve_provider(make_settings(ai_provider="auto")) == "none"


def test_auto_uses_claude_code_with_token_and_cli(make_settings, with_cli):
    s = make_settings(ai_provider="auto", claude_code_oauth_token=OAUTH, cursor_api_key=CURSOR)
    assert config.resolve_provider(s) == "claude_code"


def test_auto_token_without_cli_falls_through(make_settings, no_cli):
    s = make_settings(ai_provider="auto", claude_code_oauth_token=OAUTH, cursor_api_key=CURSOR)
    assert config.resolve_provider(s) == "cursor"


def test_auto_cursor_before_openai(make_settings, no_cli):
    s = make_settings(ai_provider="auto", cursor_api_key=CURSOR, openai_api_key=OPENAI)
    assert config.resolve_provider(s) == "cursor"


def test_unknown_value_behaves_like_auto(make_settings, no_cli):
    s = make_settings(ai_provider="gemini", openai_api_key=OPENAI)
    assert config.resolve_provider(s) == "openai"


def test_settings_default_reads_no_real_env():
    # conftest points the env file at an empty tmp file.
    assert config.get_settings().ai_provider == "auto"
