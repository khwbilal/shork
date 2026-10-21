# 0001: The Claude subscription runs through the local Claude Code CLI, locked down

**Date:** 2026-10-21 · **Work item:** WL-010 · **Status:** accepted

## Context

Sheryar wanted analyses paid by "my claude tokens" (a Claude Pro plan) rather than a per-token API key. The Anthropic API does not accept subscription logins; the Claude Code CLI does, and Sheryar is logged in to it.

## Decision

Provider `claude_code` runs `claude -p` headless per request from an empty temporary directory with `--tools ""`, `--strict-mcp-config`, `--setting-sources ""`, `--no-session-persistence` and the desk prompt in `--system-prompt-file`; the market prompt goes in on stdin. `ANTHROPIC_API_KEY` is removed from the child environment. The CLI's own login is used, or `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token`. `auto` never picks it without an explicit token.

## Consequences

- No API key needed; usage counts against the plan's limits; about 30 to 40 s per full analysis.
- The model cannot read files, run tools or load project settings, so the reply depends only on our prompt.
- The call is a blocking subprocess and must run in a thread (uvicorn's loop on Windows cannot spawn subprocesses).
- For personal local use only; a shared deployment uses the Claude API provider instead.
