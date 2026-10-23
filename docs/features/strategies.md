# Strategy-based analysis (WL-050)

GPTChart-style strategy packs on the Desk. Pick a strategy; the backend fetches the timeframes and indicators that pack needs and steers the AI with a short playbook.

Code: [`backend/app/strategies.py`](../../backend/app/strategies.py) · packs in [`market.py`](../../backend/app/market.py) · structure helpers in [`binance_ta.py`](../../backend/app/binance_ta.py).

## Catalog

| Id | Label | Notes |
|---|---|---|
| `desk` | Desk (default) | Today's full confluence, setup, MTF, book, liquidity and flow. Unchanged. |
| `smc` | Smart Money Concepts | Swings, BOS/CHoCH, equal levels, liquidity |
| `liquidity_sweep` | Liquidity Sweep | Equal H/L sweeps, book, liq map |
| `breakout` | Breakout | Range break, RVOL, ADX |
| `pullback` | Pullback | EMA pullback in trend |
| `retracement` | Retracement | Fib levels from the last swing |
| `scalping` | Scalping | 5m + 15m, VWAP, RSI, Stoch |
| `ema_volatility` | EMA Volatility | EMA + Bollinger squeeze / ATR |

Named strategies **always** own their `primary_tf` (WL-051). The desk timeframe select only drives the Desk pipeline; for packs the chart follows the pack primary and every declared timeframe gets a full indicator pack:

- Scalping: 5m + 15m
- SMC: 15m + 1h + 4h
- Breakout / pullback / retracement: 1h + 4h
- Liquidity sweep / EMA volatility: 15m + 1h

The Desk shows `Pack data: …` listing all of those TFs. All frames land in `market.strategy_pack.timeframes` for the prompt.

Named strategies skip the desk confluence / chop Neutral guard ([decision 0003](../decisions/0003-guards-decide-the-bias.md) still applies to `desk` only). The reward:risk guard still applies to every strategy (hard floor 1:1).

## Risk profile (WL-053)

Each strategy owns a `RiskProfile` in [`strategies.py`](../../backend/app/strategies.py):

| Field | Used for |
|---|---|
| `stop_atr_min` / `stop_atr_max` | Clamp on suggested stop distance; AI RISK line |
| `min_reward_risk` | Prompt ask (else Neutral); hard guard stays 1:1 |
| `target_r_min` | Suggested target at least this many R |
| `review_*` | Live-review Hold / Caution / Exit early bands |

Examples: scalping stops 0.5 to 1 ATR with early exit near -0.4R; SMC stops 1 to 3 ATR with exit near -0.75R. A full stop-out is still **-1R** by definition of R.

`GET /api/strategies` includes `risk` on every row. The analyze snapshot exposes `strategy_risk`.

Performance of archived signals by strategy: [Dashboard](dashboard.md).

## All strategies + optimization (WL-054)

Desk can run **All strategies**. Then an **Optimization** select appears:

| Mode | Behaviour | Cost |
|---|---|---|
| `local_score` | Local pack levels + fit/R:R score; optional short AI brief on the winner | Low |
| `majority_vote` | Vote Buy/Sell/Neutral across packs; highest-scoring agreeing pack supplies levels | Low |
| `ai_ensemble` | AI on every pack, then one synthesis pass | High (N+1 AI calls) |

The archived signal's `strategy_id` is the **winner**. Every pack's initial result is stored in `multi_analysis_json` and shown on `#/signals/{id}`.

## API

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/strategies` | `{ strategies, default: "desk" }` (each row includes `risk`) |
| `POST` | `/api/analyze` | `strategy_id` (default `desk`, or `all`); when `all`, pass `optimize_mode`. Response may include `packs`, `optimize_mode`, `final_strategy_id` |
| `POST` | `/api/chat` | same `strategy_id` (not `all`) |
| `GET` | `/api/signals?strategy_id=` | optional filter; `desk` includes legacy rows with NULL |
| `GET` | `/api/signals/{id}` | full signal including `multi_analysis_json` and `live_review_json` |

Signals store `strategy_id` (migration 005) and optional `multi_analysis_json` (migration 007). The Signals page filters by strategy and scopes the KPI strip to the filtered rows.

## UI

- Desk: Strategy select (includes All strategies) next to Full analysis; Optimization when All is selected.
- Signals: Strategy filter beside Status; row click opens `#/signals/{id}`.
