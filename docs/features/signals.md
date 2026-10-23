# Signal verification

An automatic, honest track record. Every full analysis that ends as a **Buy or Sell with entry, stop and target** is archived, then checked against the candles that came afterwards.

Code: `backend/app/signals.py` · Storage: SQLite `signals` table ([database](../database.md)).

## Archiving

`record_signal` runs inside `POST /api/analyze`, after the guardrail. It skips:

- Plans made without an AI (`provider: "offline"`, i.e. no key configured).
- Neutral plans, including plans the [reward:risk guard](../ai-providers.md#what-happens-to-the-reply) turned Neutral.
- Plans missing entry, stop or target.
- **Duplicates**: same pair, timeframe, strategy, bias and entry within 30 minutes. The existing signal is returned instead.

The record stores the levels, the price at signal time, the setup, the confluence score, confidence, reasoning and `strategy_id` (WL-050; default `desk`), all with `status: "open"`. Legacy rows with a NULL strategy count as Desk in the UI.

## Verifying

**UI:** Signals → **Verify open signals**, or **Check** on a single row.
**API:** `POST /api/signals/verify?only_open=true&limit=50`, `POST /api/signals/{id}/verify`

The verifier fetches the klines after the signal was created (Binance spot, then futures) and walks them bar by bar:

| Outcome | Rule |
|---|---|
| **win** | Target touched first. `R = reward ÷ risk` |
| **loss** | Stop touched first. `R = −1` |
| **loss** (conservative) | Stop and target both touched in the same bar, so the stop is assumed to come first |
| **open** | Neither touched yet |
| **expired** | Neither touched within the horizon. R is marked to market at the last close of the horizon. |

The horizon depends on the timeframe: 15m → 48 bars (~12h), 1h → 48 (~2d), 4h → 42 (~7d), 1d → 21 (~3w).

## Stats

| Stat | Definition |
|---|---|
| Hit rate | wins ÷ (wins + losses). Expired signals don't count. |
| Average R | Mean R over closed signals, including the mark-to-market R of expired ones |
| By setup | Hit rate per setup type |

## API

| Method | Path | Returns |
|---|---|---|
| `GET` | `/api/signals?limit=80&symbol=&strategy_id=` | `{ signals, stats }` |
| `POST` | `/api/signals/verify?symbol=&only_open=true&limit=50` | `{ checked, updated, stats }` |
| `POST` | `/api/signals/{id}/verify` | `{ signal, stats }` |

The Signals page combines timeframe tabs, a strategy filter and a status filter (AND). KPIs recompute for the filtered view. See also [strategies](strategies.md).

The rail shows the number of open signals next to **Signals**.

## Signal detail page (WL-054)

Hash route `#/signals/{id}` loads `GET /api/signals/{id}`. Shows the frozen original plan, every pack from `multi_analysis_json` (when the signal came from All strategies), and live-review history. Row click on the Signals list navigates here.

## Live review (WL-052, revised levels WL-054)

Re-checks an **open** signal against the live price without changing the original plan (bias, entry, stop, target, notes stay frozen). Each run **appends** a review to `live_review_json`.

When structure moves enough (about 0.15R vs the original stop/target), the review also stores **advisory** `revised_stop_loss` / `revised_take_profit` (and optional `revised_entry`). Stance and open R still use the **original** levels. Adopting revised levels into the archived plan is out of scope.

**UI:** Signals → **Live review open**, or **Review** on a row (then opens detail). Detail page has Live review too.

**API:** `POST /api/signals/review?only_open=true&limit=50`, `POST /api/signals/{id}/review`, `GET /api/signals/{id}`

Stance (deterministic, no AI). Bands come from the signal's **strategy risk profile** (WL-053); desk defaults shown below:

| Stance | Desk default |
|---|---|
| Hold | Unrealized R roughly -0.35 to +0.7, stop not immediate |
| Caution | Within ~0.35R of stop, or choppy around entry |
| Exit early | Unrealized ≤ -0.6R, or ≥ ~85% of the way to target (bank) |

Scalping exits earlier (about -0.4R); SMC / retracement give more room (about -0.75R). See [strategies](strategies.md#risk-profile-wl-053). A verified stop hit is still `r_multiple = -1`.

Missing live price → summary `na("no live price")`, stance null. Verify (TP/SL walk) still runs first so a hit can close the signal; the review still records the mark.
