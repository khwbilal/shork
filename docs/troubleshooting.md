# Troubleshooting

Start with:

```bash
curl -s http://127.0.0.1:8000/api/health
```

## No AI

`ai_provider: "none"`, the rail reads **No AI**, and analyses come back with `provider: "offline"`.

- Restart with `start.ps1` / `start.sh` and pick a provider. The menu shows what each one is missing. The server log also prints `AI_PROVIDER=… is selected but not configured`.
- **Claude subscription:** `claude --version` must work in the same terminal, and `claude auth status` must show `"loggedIn": true`. If `claude` isn't on PATH, set `CLAUDE_CODE_PATH`.
- The key must be in **`backend/.env`**, not in a `.env` at the project root.
- `ANTHROPIC_API_KEY=sk-ant-…`: no quotes, no spaces, nothing after it on the line.
- Placeholder-looking values are ignored on purpose: anything empty, ending in `...`, or containing `your_` or `replace`.
- If `AI_PROVIDER` is pinned (e.g. `openai`), that provider's key is the one that has to be set. Use `auto` to take whichever key is present.
- The `.env` is re-read on every request, so no restart is needed. If you started the server with environment variables exported in the shell, those take precedence over `.env`.

## `502 AI error: …`

The provider was called and failed. The message tells you why. See [AI providers → errors](ai-providers.md#errors-you-might-see). Common causes: for the Claude API, a revoked key, no credit on the workspace, or an `ANTHROPIC_MODEL` typo; for the Claude subscription, *not logged in* (run `claude auth login`), the plan's usage limit being reached, or a timeout (raise `CLAUDE_CODE_TIMEOUT`).

## Analysis is slow or thin

- The first analysis after a start takes 10 to 20 seconds: TradingView, Binance spot and futures, the MTF pack and the regime are all fetched.
- TradingView's public TA rate-limits. The app then switches to **Binance local TA** automatically (the Desk card shows "Data: Binance (local TA)"). This is normal.
- **Whales & derivatives** and **Liquidity** show "No futures data" for pairs that aren't on Binance Futures.

## Chart doesn't load

The chart is TradingView's hosted widget (`s3.tradingview.com/tv.js`). Ad blockers, corporate proxies, or being offline can block it. The rest of the app keeps working.

## Search shows nothing

The first search loads the Binance pair universe (a few seconds). After that it's cached for 30 minutes. If it stays empty, the backend can't reach `api.binance.com`. Check your network or region.

## `uv: command not found` / start script exits

Install uv (see [Getting started](getting-started.md#1-install-uv)) and open a **new** terminal. `start.ps1` adds `%USERPROFILE%\.local\bin` to PATH for that session.

In a VS Code terminal, "new" means a new VS Code window: VS Code copies PATH when it starts, so its terminals miss a PATH change made after that (seen 2026-10-21, after uv was installed with VS Code open). Close and reopen VS Code, or run the full path `"$env:USERPROFILE\.local\bin\uv.exe"`.

## Port 8000 in use

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

## Reset local data

Delete `backend/data/journal.json` and/or `backend/data/signals.json`. Clear UI preferences by clearing site data for `127.0.0.1:8000` in the browser.
