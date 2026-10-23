# API reference

Base URL: `http://127.0.0.1:8000`. Interactive docs (Swagger) are at **`/docs`**. Everything is JSON, and there is no authentication, so keep the server on localhost.

Errors use FastAPI's shape, `{"detail": "…"}`: `400` for bad input, `404` when something is not found, `502` when the AI provider fails.

## Core

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | `{status, app, ai_provider, ai_model, tradingview_ready}`. `ai_provider` is `claude_code`, `claude`, `cursor`, `openai` or `none`. |
| `POST` | `/api/analyze` | Full analysis → plan + levels + snapshot. [Details](features/analysis-and-chat.md#full-analysis) |
| `POST` | `/api/chat` | Follow-up question with a fresh snapshot. [Details](features/analysis-and-chat.md#chat) |
| `GET` | `/api/strategies` | Strategy catalog (desk + GPTChart-style packs), each with a `risk` profile (stop ATR bands + live-review thresholds). [Details](features/strategies.md) |
| `GET` | `/api/signals/{id}` | One signal with `multi_analysis_json` and `live_review_json` (WL-054) |
| `GET` | `/api/market/{symbol}?exchange=BINANCE&timeframe=1h` | Raw snapshot, for debugging. [Shape](analysis-pipeline.md#snapshot-shape-top-level-keys) |
| `GET` | `/api/symbols/search?q=&exchange=BINANCE&limit=25` | Search by symbol or name. Each result adds `type`, `name` and `market`. [Details](features/symbol-search.md) |
| `GET` | `/api/calendar?days=7&kind=` | Upcoming events and the status of each source. [Details](features/calendar.md) |
| `GET` | `/api/pulse` | BTC and ETH: price, 24h change, and per timeframe (1M, 1w, 1d, 1h, 15m) trend, RSI and bias. Cached 20 s. [Details](#get-apipulse) |
| `GET` | `/api/correlation/{symbol}` | Correlation and beta against BTC and ETH, 30 days of 1h and 90 days of 1d. Cached 15 min. [Details](#get-apicorrelationsymbol) |
| `GET` | `/api/jobs` | Last run and next run of each scheduled job. [Details](scheduled-jobs.md#seeing-runs) |

### `POST /api/analyze`

| Field | Type | Default |
|---|---|---|
| `symbol` | string | required: `SOLUSDT`, `BTCUSDT.P`, … |
| `exchange` | string | `BINANCE` |
| `timeframe` | string | `1h` (`15m`, `1h`, `4h`, `1D`) |
| `strategy_id` | string | `desk` (or `all` for every pack; see [strategies](features/strategies.md)) |
| `optimize_mode` | string | `local_score` (also `majority_vote`, `ai_ensemble`); used when `strategy_id` is `all` |
| `custom_prompt` | string \| null | Extra trader notes appended to the prompt |

Returns `symbol, exchange, timeframe, tv_symbol, strategy_id, strategy_label, market, levels, analysis, provider`, and when multi: `optimize_mode`, `final_strategy_id`, `packs`. `market.correlation` and `market.upcoming_events` are described in the [analysis pipeline](analysis-pipeline.md#snapshot-shape-top-level-keys). `provider` is `claude_code`, `claude`, `cursor`, `openai`, `offline`, or `local_score`.

### `POST /api/chat`

| Field | Type | Default |
|---|---|---|
| `symbol`, `exchange`, `timeframe`, `strategy_id` | as above | |
| `message` | string | required |
| `history` | `[{role, content}]` | `[]`. The last 6 are used. |

Returns `symbol, reply, provider, strategy_id, market_snapshot (null)`.

### `GET /api/pulse`

Added in WL-035. `{symbols: PulseSymbol[], timeframes: ["1M","1w","1d","1h","15m"], rule, generated_at}`.

- `PulseSymbol`: `{symbol, available, price, change_24h_pct, error, timeframes: PulseCell[]}`. `available` refers to the 24h ticker; the cells stand on their own.
- `PulseCell`: `{tf, available, price, trend: up|down|flat, rsi, ema20, ema50, price_vs_ema20: above|below, change_pct, bias: Buy|Sell|Neutral, candle_open, error}`.
- **Rule** (also returned in `rule`): trend is up when EMA20 > EMA50 and price > EMA20, down when EMA20 < EMA50 and price < EMA20, otherwise flat. Bias is Buy when the trend is up and RSI < 70, Sell when the trend is down and RSI > 30, otherwise Neutral. The last candle is the live one.
- Binance spot klines (120 per cell) and the 24h ticker, all fetched concurrently with a 5 s timeout. Every result, failures included, is cached for 20 s, so the UI can poll every 20 s.

### `GET /api/correlation/{symbol}`

Added in WL-036. `{available, symbol, market: spot|usdm|spot_or_usdm, windows: {"30d_1h", "90d_1d"}, summary, error}`.

- Each window is `{interval, days, candles, btc: Stat, eth: Stat}`, and each `Stat` is `{available, correlation, beta, overlap_pct, samples, error}`.
- **Method:** Pearson correlation of log returns of closed candles aligned on open time, and beta = cov / var of the benchmark. Less than 60% overlap, fewer than 10 returns, or a flat benchmark gives `available: false`, so a coin listed recently has no 30-day value yet.
- **Market:** a `.P` symbol uses USD-M; otherwise the instrument catalogue decides, and the benchmarks use the same market. Klines are cached for 15 minutes.
- The same object is in the snapshot as `market.correlation`.

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
| `GET` | `/api/signals?limit=80&symbol=&strategy_id=` | Archived signals + stats (optional strategy filter) |
| `GET` | `/api/signals/dashboard` | Strategy performance cards and chart series. [Details](features/dashboard.md) |
| `POST` | `/api/signals/verify?symbol=&only_open=true&limit=50` | Verify many |
| `POST` | `/api/signals/review?only_open=true&limit=50` | Live review open signals (append stance history). [Details](features/signals.md#live-review-wl-052) |
| `POST` | `/api/signals/{id}/review` | Live review one open signal |
| `POST` | `/api/signals/{id}/verify` | Re-check one (forced) |

[Details](features/signals.md)

## Static

| Path | Serves |
|---|---|
| `/` | `backend/app/static/index.html` |
| `/static/*` | `app.css`, `app.js` |
