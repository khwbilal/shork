"""Startup menu: pick the AI analyst and make sure it has credentials.

Run by start.ps1 / start.sh before the server starts:

    uv run python -m app.choose_provider                 # interactive menu
    uv run python -m app.choose_provider --provider claude_code
    uv run python -m app.choose_provider --keep          # no menu, keep .env

The choice is written to AI_PROVIDER in backend/.env, together with any key you
paste, so the server (which re-reads .env on every request) uses it straight away.
"""

from __future__ import annotations

import argparse
import getpass
import json
import re
import subprocess
import sys
from dataclasses import dataclass

from .config import (
    ENV_FILE,
    PROVIDERS,
    Settings,
    claude_cli,
    is_configured,
    looks_like_real_key,
    normalize_provider,
    provider_model,
)


@dataclass(frozen=True)
class Choice:
    key: str
    title: str
    detail: str
    env_key: str | None = None
    key_prefix: str | None = None
    key_url: str | None = None


CHOICES = [
    Choice("claude_code", "Claude subscription", "your Claude Code login (Pro / Max plan)"),
    Choice(
        "claude", "Claude API", "ANTHROPIC_API_KEY, billed per token",
        "ANTHROPIC_API_KEY", "sk-ant-", "https://console.anthropic.com/settings/keys",
    ),
    Choice(
        "cursor", "Cursor", "CURSOR_API_KEY, Cursor agents",
        "CURSOR_API_KEY", "crsr_", "https://cursor.com/dashboard/integrations",
    ),
    Choice(
        "openai", "OpenAI", "OPENAI_API_KEY",
        "OPENAI_API_KEY", "sk-", "https://platform.openai.com/api-keys",
    ),
    Choice("none", "No AI", "market data and the deterministic plan only"),
]
BY_KEY = {c.key: c for c in CHOICES}


# ─── .env editing ────────────────────────────────────────────────────────────

def set_env_values(values: dict[str, str]) -> None:
    """Update KEY=value lines in backend/.env in place; append missing keys."""
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    found: set[str] = set()
    for i, line in enumerate(lines):
        m = re.match(r"^\s*([A-Z0-9_]+)\s*=", line)
        if m and m.group(1) in values:
            # Every occurrence: a later duplicate line would otherwise win.
            lines[i] = f"{m.group(1)}={values[m.group(1)]}"
            found.add(m.group(1))
    lines.extend(f"{k}={v}" for k, v in values.items() if k not in found)
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ─── Claude Code login ───────────────────────────────────────────────────────

def claude_login(settings: Settings) -> dict | None:
    """`claude auth status` as a dict, or None when the CLI is missing or fails."""
    cli = claude_cli(settings)
    if not cli:
        return None
    try:
        proc = subprocess.run(  # noqa: S603
            [cli, "auth", "status", "--json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        return json.loads(proc.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return None


def status_line(settings: Settings, choice: Choice) -> tuple[bool, str]:
    """(ready, short status) for the menu."""
    if choice.key == "none":
        return True, "always available"
    if choice.key == "claude_code":
        if not claude_cli(settings):
            return False, "Claude Code CLI not installed"
        if looks_like_real_key(settings.claude_code_oauth_token):
            return True, "token in .env"
        info = claude_login(settings) or {}
        if info.get("loggedIn"):
            plan = info.get("subscriptionType") or info.get("authMethod") or "logged in"
            return True, f"logged in ({plan})"
        return False, "not logged in"
    return (True, "key set") if is_configured(settings, choice.key) else (False, "needs key")


# ─── Prompts ─────────────────────────────────────────────────────────────────

def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def ask_secret(prompt: str) -> str:
    try:
        return getpass.getpass(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def ensure_api_key(choice: Choice) -> bool:
    """Ask for a missing key and save it. Returns False when the user skips."""
    assert choice.env_key
    print(f"\n{choice.title} needs {choice.env_key}. Create one at {choice.key_url}")
    while True:
        key = ask_secret(f"Paste {choice.env_key} (input hidden, Enter to skip): ")
        if not key:
            return False
        if not looks_like_real_key(key, choice.key_prefix or ""):
            print("That doesn't look like a real key - try again, or press Enter to skip.")
            continue
        if choice.key_prefix and not key.startswith(choice.key_prefix):
            print(f"Note: {choice.title} keys usually start with '{choice.key_prefix}'. Saving anyway.")
        set_env_values({choice.env_key: key})
        print(f"Saved {choice.env_key} to backend/.env")
        return True


def ensure_claude_code(settings: Settings) -> bool:
    """Make sure the Claude Code CLI is installed and signed in."""
    if not claude_cli(settings):
        print(
            "\nThe Claude Code CLI isn't installed. Install it with:\n"
            "    npm install -g @anthropic-ai/claude-code\n"
            "then run `claude auth login`, or set CLAUDE_CODE_PATH in backend/.env."
        )
        return False
    ready, _ = status_line(settings, BY_KEY["claude_code"])
    if ready:
        return True
    print(
        "\nClaude Code is installed but not signed in.\n"
        "  1) Sign in now (opens your browser)\n"
        "  2) Paste a long-lived token from `claude setup-token`\n"
        "  3) Skip"
    )
    pick = ask("Choose [1-3]: ") or "1"
    if pick == "1":
        subprocess.run([claude_cli(settings) or "claude", "auth", "login"], check=False)  # noqa: S603
        return status_line(Settings(), BY_KEY["claude_code"])[0]
    if pick == "2":
        token = ask_secret("Paste CLAUDE_CODE_OAUTH_TOKEN (input hidden): ")
        if token:
            set_env_values({"CLAUDE_CODE_OAUTH_TOKEN": token})
            print("Saved CLAUDE_CODE_OAUTH_TOKEN to backend/.env")
            return True
    return False


def ensure_ready(choice: Choice) -> bool:
    settings = Settings()
    if choice.key == "none":
        return True
    if choice.key == "claude_code":
        return ensure_claude_code(settings)
    if is_configured(settings, choice.key):
        return True
    return ensure_api_key(choice)


def menu(current: str) -> Choice | None:
    settings = Settings()
    print("\n  Crypto Chart AI - which AI should analyse?\n")
    rows = []
    default_index = 1
    for i, c in enumerate(CHOICES, start=1):
        ready, status = status_line(settings, c)
        marker = "ready " if ready else "setup "
        is_current = c.key == current
        if is_current:
            default_index = i
        rows.append(
            f"  {i}) {c.title:<20} {c.detail:<44} [{marker}] {status}{'   <- current' if is_current else ''}"
        )
    print("\n".join(rows))
    while True:
        raw = ask(f"\nChoose 1-{len(CHOICES)} (Enter = {default_index}, q = quit): ").lower()
        if raw in ("q", "quit", "exit"):
            return None
        if not raw:
            return CHOICES[default_index - 1]
        if raw.isdigit() and 1 <= int(raw) <= len(CHOICES):
            return CHOICES[int(raw) - 1]
        if normalize_provider(raw) in BY_KEY:
            return BY_KEY[normalize_provider(raw)]
        print("Please enter a number from the list.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Choose the AI provider for Crypto Chart AI.")
    parser.add_argument("--provider", help="claude_code | claude | cursor | openai | none (skips the menu)")
    parser.add_argument("--keep", action="store_true", help="Keep AI_PROVIDER from backend/.env without asking")
    args = parser.parse_args(argv)

    current = normalize_provider(Settings().ai_provider)
    interactive = sys.stdin.isatty() and not args.keep and not args.provider

    if args.provider:
        key = normalize_provider(args.provider)
        if key not in BY_KEY:
            print(f"Unknown provider '{args.provider}'. Use one of: {', '.join(BY_KEY)}")
            return 2
        choice = BY_KEY[key]
    elif not interactive:
        print(f"Using AI_PROVIDER={current} from backend/.env")
        return 0
    else:
        while True:
            choice = menu(current)
            if choice is None:
                print("Cancelled.")
                return 1
            if ensure_ready(choice):
                break
            print(f"\n{choice.title} isn't set up yet - pick another option, or choose it again once it's ready.")

    if args.provider and not ensure_ready(choice) and sys.stdin.isatty():
        print(f"{choice.title} isn't set up; the app will run without AI until it is.")

    set_env_values({"AI_PROVIDER": choice.key})
    settings = Settings()
    model = provider_model(settings, choice.key)
    print(f"\nUsing {choice.title}{f' ({model})' if model else ''}. Saved AI_PROVIDER={choice.key} to backend/.env.")
    if choice.key in PROVIDERS:
        print("Change models or keys any time in backend/.env - no restart needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
