# Signal verification

An automatic, honest track record. Every full analysis that ends as a **Buy or Sell with entry, stop and target** is archived, then checked against the candles that came afterwards.

Code: `backend/app/signals.py` · Storage: `backend/data/signals.json`

## Archiving

`record_signal` runs inside `POST /api/analyze`, after the guardrail. It skips:

- Plans made without an AI (`provider: "offline"`, i.e. no key configured).
- Neutral plans, including plans the [reward:risk guard](../ai-providers.md#what-happens-to-the-reply) turned Neutral.
- Plans missing entry, stop or target.
- **Duplicates**: same pair, timeframe, bias and entry within 30 minutes. The existing signal is returned instead.

The record stores the levels, the price at signal time, the setup, the confluence score, confidence and reasoning, all with `status: "open"`.

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
| `GET` | `/api/signals?limit=80&symbol=` | `{ signals, stats }` |
| `POST` | `/api/signals/verify?symbol=&only_open=true&limit=50` | `{ checked, updated, stats }` |
| `POST` | `/api/signals/{id}/verify` | `{ signal, stats }` |

The rail shows the number of open signals next to **Signals**.
