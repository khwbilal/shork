# Configuration

All settings live in **`backend/.env`** (copy it from `backend/.env.example`). They are loaded by `backend/app/config.py` with pydantic-settings. Variable names are case-insensitive, and **the file is re-read on every request**, so edits apply without a restart.

`backend/.env` is gitignored. Never commit it.

## AI

| Variable | Default | Meaning |
|---|---|---|
| `AI_PROVIDER` | `auto` | `claude_code` (Claude subscription), `claude` (Claude API), `cursor`, `openai`, `none` or `auto`. **The start scripts ask and write this.** A pinned provider that isn't configured runs without AI (and logs a warning); it doesn't fall back. `auto` order: Claude API → Claude subscription (token only) → Cursor → OpenAI. |
| `CLAUDE_CODE_OAUTH_TOKEN` | none | Optional long-lived token from `claude setup-token`. Blank uses the Claude Code CLI's own login. |
| `CLAUDE_CODE_MODEL` | (blank) | Blank = your plan's default; or `opus`, `sonnet`, or a full model ID. |
| `CLAUDE_CODE_EFFORT` | `medium` | `low` … `max`; blank to omit. |
| `CLAUDE_CODE_PATH` | (blank) | Full path to `claude` when it isn't on PATH. |
| `CLAUDE_CODE_TIMEOUT` | `300` | Seconds before a subscription call is abandoned. |
| `ANTHROPIC_API_KEY` | none | Claude API key (`sk-ant-…`) from [console.anthropic.com](https://console.anthropic.com/settings/keys). |
| `ANTHROPIC_MODEL` | `claude-opus-5-5` | Any Claude model ID, e.g. `claude-sonnet-5-5` or `claude-haiku-5-5`. |
| `ANTHROPIC_EFFORT` | `medium` | `low` · `medium` · `high` · `xhigh` · `max`. Leave it blank for models that don't support effort (e.g. `claude-haiku-4-5`). |
| `CURSOR_API_KEY` | none | Cursor key (`crsr_…`) from [cursor.com/dashboard/integrations](https://cursor.com/dashboard/integrations). |
| `CURSOR_MODEL` | `composer-2.5` | Cursor agent model. |
| `OPENAI_API_KEY` | none | OpenAI key (`sk-…`). |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI chat model. |

A key only counts as configured if it looks real. Empty values, values that end in `...`, and values that contain `your_` or `replace` are ignored. This stops a placeholder from being sent to an API.

## Market data

| Variable | Default | Meaning |
|---|---|---|
| `COINGLASS_API_KEY` | none | Optional. Enriches the liquidity map with real Coinglass liquidation history. The estimated map works without it. |
| `MARKETAUX_API_TOKEN` | none | Optional. News/sentiment token used by the TradingView MCP package's tools. |
| `DEFAULT_EXCHANGE` | `BINANCE` | Default exchange label. |
| `DEFAULT_TIMEFRAME` | `1h` | Default timeframe. |

No key is needed for Binance or TradingView. Both are read from public endpoints.

## Storage

| Variable | Default | Meaning |
|---|---|---|
| `DB_PATH` | (blank) | SQLite file. Blank means `backend/data/app.db`. See [Database](database.md). |
| `BACKUP_DIR` | (blank) | Folder for the daily backup. Blank means `backups/` at the repo root. See [Scheduled jobs](scheduled-jobs.md#backup). |

## Server

| Variable | Default | Meaning |
|---|---|---|
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Extra origins allowed to call the API (the Vite dev UI). `:8000` is always allowed. |

The host and port are set on the `uvicorn` command line (`--host 127.0.0.1 --port 8000`). Keep the host at `127.0.0.1`: the API has no authentication and spends your AI credits.

## Local data files

| Path | Written by |
|---|---|
| `backend/data/journal.json` | [Trade journal](features/journal.md) |
| `backend/data/signals.json` | [Signal verification](features/signals.md) |

Both files are created on first use and are gitignored. Delete one to reset it.
