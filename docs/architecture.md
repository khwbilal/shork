# Architecture

```
 Browser (built-in UI, /static)                     FastAPI  (backend/app/main.py)
 ┌─────────────────────────────┐    /api/*     ┌──────────────────────────────────────────┐
 │ TradingView widget (tv.js)  │──────────────▶│ /api/analyze, /api/chat                  │
 │ Desk · Watchlist · Journal  │               │   │                                      │
 │ Signals · Ctrl K palette    │◀──────────────│   ├─ market.fetch_coin_context  ──────┐  │
 └─────────────────────────────┘     JSON      │   │    (threadpool)                   │  │
                                               │   ├─ ai.build_*_prompt                │  │
                                               │   ├─ ai.generate_text ──▶ Claude /    │  │
                                               │   │                       OpenAI      │  │
                                               │   ├─ extract → fill → guardrail       │  │
                                               │   └─ signals.record_signal            │  │
                                               │ /api/watchlist, /journal, /signals    │  │
                                               └───────────────────────────────────────┼──┘
                                                                                       ▼
            tradingview-mcp-server (Python pkg) · Binance spot + futures REST · Yahoo · Coinglass*
```

## Backend modules (`backend/app/`)

| Module | Responsibility |
|---|---|
| `main.py` | FastAPI app, routes, bias guardrail, level back-fill, static UI |
| `config.py` | `.env` settings, provider resolution |
| `ai.py` | System prompt, prompt builders, provider calls, reply parsing and formatting |
| `schemas.py` | Pydantic request and response models |
| `market.py` | Builds one market snapshot per request ([pipeline](analysis-pipeline.md)) and condenses it into the prompt block |
| `binance_ta.py` | Local indicators from Binance klines: EMA, RSI, ATR, MACD, Stochastic, Bollinger, ADX, VWAP, pivots, S/R, suggested levels |
| `confluence.py` | 15m/1h/4h/1d MTF pack, BTC/ETH regime, [confluence score](features/confluence-score.md) |
| `setup_classifier.py` | [Setup type and chop filter](features/setup-classifier.md) |
| `flow.py` | Binance Futures positioning: top traders, accounts, taker ratio, OI, funding, basis |
| `orderbook.py` | Depth imbalance (top 50 / top 5 levels) |
| `liquidity.py` | Estimated liquidation clusters and squeeze/cascade score |
| `watchlist.py` | [Batch scoring](features/watchlist.md) |
| `journal.py` | [Trade journal](features/journal.md) (SQLite) |
| `signals.py` | [Signal archive and TP/SL verification](features/signals.md) (SQLite) |
| `db.py`, `migrations/` | [Database](database.md): connection, migrations, JSON import |
| `instruments.py` | [Instrument catalogue](features/symbol-search.md#instrument-catalogue) refresh |
| `calendar_feed.py` | [Calendar](features/calendar.md) sources and refresh |
| `jobs/` | [Scheduled jobs](scheduled-jobs.md): `python -m app.jobs <job>` |
| `symbols.py` | [Pair universe and search](features/symbol-search.md) |
| `static/` | The built-in UI: `index.html`, `app.css` (shared with the React UI), `app.js`. No build step. |

## Frontends

- **Built-in UI** (`backend/app/static/`), served at `/`. Full featured. Plain HTML, CSS and JS, so there's no Node dependency. See [User interface](ui.md).
- **React UI** (`frontend/`): Vite + React 19 + TypeScript port of the same four pages, dev server on `:5173` with `/api` proxied to `:8000`. It imports `backend/app/static/app.css`, so both UIs share one stylesheet.

## Concurrency

Market collection is blocking I/O (httpx and the TradingView package), so it runs in `asyncio.to_thread`. Claude and OpenAI calls use the async SDK clients.

## State and persistence

- **SQLite** at `backend/data/app.db` (gitignored): journal, signals, job runs, the instrument catalogue and the calendar. See [Database](database.md).
- **Daily backups** in `backups/` at the repo root. See [Scheduled jobs](scheduled-jobs.md).
- An in-memory 30-minute cache of the TradingView coin list (other venues in search).
- Chat history, which lives in the browser. The UI sends the last 8 messages with each chat request, and the backend uses the last 6.

Browser `localStorage` holds UI preferences only: theme, folded rail, timeframe, recent pairs.

## Failure behaviour

Each data source is optional, and a failure is recorded in the snapshot instead of failing the request:

- TradingView rate-limited or unusable → **Binance local TA** (`data_source: "binance_local"`).
- Pair not listed on Binance Futures → `flow`, `liquidity` and the futures order book come back with `available: false`.
- Confluence pack error → `confluence: {bias: "Neutral", score: 0, error}`.
- AI error → HTTP 502 with a readable `detail`. The UI shows it in the chat.
