# Crypto Chart AI

A local crypto analysis desk: a live TradingView chart next to an AI analyst. The backend gathers real market context (TradingView TA, multi-timeframe trend, whale positioning, order book, liquidation map), scores it, and has an AI (**your Claude subscription**, the Claude API, Cursor or OpenAI; you pick at startup) write a trade plan that has to respect that score.

## What it does

1. Pick any pair (`SOLUSDT`, `BTCUSDT`, `BTWUSDT.P`, …) with **Ctrl K**, and choose a timeframe.
2. The backend pulls TA through [`tradingview-mcp-server`](https://github.com/atilaahmettaner/tradingview-mcp) (the official Python package, **not** npm), falling back to Binance. It adds futures flow, order-book imbalance and an estimated liquidation map.
3. A deterministic **confluence score** (−10…+10) and a **setup classifier** (chop / mean-revert / breakout / trend) set the allowed bias.
4. The AI writes the plan (bias, entry, stop, target, R:R), and the backend enforces the score on it.
5. Every Buy/Sell plan is archived and later **checked against real candles**. A watchlist scorer and a trade journal round it out.

## Quick start

**Windows** → `.\start.ps1`  ·  **macOS / Linux** → `./start.sh`

The script installs the dependencies, creates `backend/.env`, and **asks which AI to use**:

```
  1) Claude subscription  your Claude Code login (Pro / Max plan)      [ready ] logged in (pro)
  2) Claude API           ANTHROPIC_API_KEY, billed per token          [setup ] needs key
  3) Cursor               CURSOR_API_KEY, Cursor agents                [setup ] needs key
  4) OpenAI               OPENAI_API_KEY                               [setup ] needs key
  5) No AI                market data and the deterministic plan only  [ready ] always available
```

Pick one. If it needs a key or a Claude sign-in, the script asks for it and saves it to `backend/.env`. Then open **http://127.0.0.1:8000**. The bottom of the left rail shows the active AI. Skip the menu with `-Provider claude_code` / `--provider claude_code`, or `-Keep` / `--keep`.

You need [uv](https://docs.astral.sh/uv/); Node is not needed. Full steps: [docs/getting-started.md](docs/getting-started.md) · Mac from scratch: [docs/mac-setup.md](docs/mac-setup.md)

## AI providers

| `AI_PROVIDER` | Uses | Credentials in `backend/.env` |
|---|---|---|
| `claude_code` | **Your Claude subscription** via the local Claude Code CLI | none (`claude auth login`), or `CLAUDE_CODE_OAUTH_TOKEN` |
| `claude` | Claude API, billed per token | `ANTHROPIC_API_KEY` |
| `cursor` | Cursor agents | `CURSOR_API_KEY` |
| `openai` | OpenAI | `OPENAI_API_KEY` |

The start scripts set `AI_PROVIDER` for you. You can also edit it in `.env` at any time (no restart needed). Models are configurable per provider. See [docs/ai-providers.md](docs/ai-providers.md).

## Documentation

Everything is in **[docs/](docs/README.md)**: architecture, the analysis pipeline, each feature (confluence, setup classifier, flow and liquidity, watchlist, journal, signals, search), the API reference, the UI design system, MCP setup for Claude Code, and troubleshooting.

## API at a glance

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Active AI provider + model, TradingView package status |
| `POST /api/analyze` | Full analysis + structured levels |
| `POST /api/chat` | Follow-up Q&A with fresh market context |
| `GET /api/market/{symbol}` | Raw market snapshot (debug) |
| `GET /api/watchlist/score` · `/api/journal` · `/api/signals` | Watchlist, journal, signal verification |

Full list: [docs/api-reference.md](docs/api-reference.md), plus Swagger at `/docs`.

## Security note

Do **not** use `npx @atilaahmettaner/tradingview-mcp`. The official project is Python-only; fake npm copies have shipped malware. Keep the server on `127.0.0.1`: the API has no auth and spends your AI credits.

## Disclaimer

Not financial advice. Market data may be delayed or incomplete. You are solely responsible for trading decisions.
