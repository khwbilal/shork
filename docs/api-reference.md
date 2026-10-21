# API reference

Base URL: `http://127.0.0.1:8000`. Interactive docs (Swagger) are at **`/docs`**. Everything is JSON, and there is no authentication, so keep the server on localhost.

Errors use FastAPI's shape, `{"detail": "…"}`: `400` for bad input, `404` when something is not found, `502` when the AI provider fails.

## Core

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | `{status, app, ai_provider, ai_model, tradingview_ready}`. `ai_provider` is `claude_code`, `claude`, `cursor`, `openai` or `none`. |
| `POST` | `/api/analyze` | Full analysis → plan + levels + snapshot. [Details](features/analysis-and-chat.md#full-analysis) |
| `POST` | `/api/chat` | Follow-up question with a fresh snapshot. [Details](features/analysis-and-chat.md#chat) |
| `GET` | `/api/market/{symbol}?exchange=BINANCE&timeframe=1h` | Raw snapshot, for debugging. [Shape](analysis-pipeline.md#snapshot-shape-top-level-keys) |
| `GET` | `/api/symbols/search?q=&exchange=BINANCE&limit=25` | Search by symbol or name. Each result adds `type`, `name` and `market`. [Details](features/symbol-search.md) |
| `GET` | `/api/calendar?days=7&kind=` | Upcoming events and the status of each source. [Details](features/calendar.md) |
| `GET` | `/api/jobs` | Last run and next run of each scheduled job. [Details](scheduled-jobs.md#seeing-runs) |

### `POST /api/analyze`

| Field | Type | Default |
|---|---|---|
| `symbol` | string | required: `SOLUSDT`, `BTWUSDT.P`, … |
| `exchange` | string | `BINANCE` |
| `timeframe` | string | `1h` (`15m`, `1h`, `4h`, `1D`) |
| `custom_prompt` | string \| null | Extra trader notes appended to the prompt |

Returns `symbol, exchange, timeframe, tv_symbol, market, levels, analysis, provider, disclaimer`. `provider` is `claude_code`, `claude`, `cursor`, `openai` or `offline`.

### `POST /api/chat`

| Field | Type | Default |
|---|---|---|
| `symbol`, `exchange`, `timeframe` | as above | |
| `message` | string | required |
| `history` | `[{role, content}]` | `[]`. The last 6 are used. |

Returns `symbol, reply, provider, market_snapshot (null), disclaimer`.

## Watchlist

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/watchlist/score?timeframe=1h&symbols=A,B` | Score a list (the default list if `symbols` is empty) |
| `POST` | `/api/watchlist/score` | Body `{symbols?: string[], timeframe}` |

[Details](features/watchlist.md)

## Journal

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/journal?limit=100` | Entries + stats |
| `GET` | `/api/journal/stats` | Stats only |
| `POST` | `/api/journal` | Add an entry |
| `POST` | `/api/journal/{id}/close` | Close as win / loss / be / skipped |
| `DELETE` | `/api/journal/{id}` | Delete |

[Details](features/journal.md)

## Signals

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/signals?limit=80&symbol=` | Archived signals + stats |
| `POST` | `/api/signals/verify?symbol=&only_open=true&limit=50` | Verify many |
| `POST` | `/api/signals/{id}/verify` | Re-check one (forced) |

[Details](features/signals.md)

## Static

| Path | Serves |
|---|---|
| `/` | `backend/app/static/index.html` |
| `/static/*` | `app.css`, `app.js` |
