# Trade journal

A local log of the plans you actually took, with hit rate and R-multiples.

Code: `backend/app/journal.py` · Storage: `backend/data/journal.json`

## Workflow

1. Run **Full analysis** on the Desk.
2. Click **Log to journal**. This saves the pair, timeframe, side (Sell when the bias is Sell, otherwise Buy), setup type, entry, stop, target, confluence score, and the reasoning as notes.
3. Later, on the **Journal** page, close the trade with **Win**, **Loss**, **BE** (breakeven) or **×** (skipped). Win, Loss and BE ask for an optional exit price.
4. Closed entries can be deleted (you are asked to confirm).

## R-multiple

When an exit price is given and the entry ≠ the stop:

```
risk = |entry − stop|
R    = (exit − entry) / risk        # Buy
R    = (entry − exit) / risk        # Sell
```

## Stats

| Stat | Definition |
|---|---|
| Hit rate | wins ÷ (wins + losses + breakevens) |
| Average R | Mean R of closed trades that have an exit price |
| By setup | Count and hit rate per setup type (in the API response) |

Skipped trades are excluded from every stat.

## API

| Method | Path | Body / notes |
|---|---|---|
| `GET` | `/api/journal?limit=100` | `{ entries, stats }` |
| `GET` | `/api/journal/stats` | stats only |
| `POST` | `/api/journal` | `{ symbol, timeframe, side, setup, entry, stop_loss, take_profit, confluence, notes }` |
| `POST` | `/api/journal/{id}/close` | `{ status: "win"\|"loss"\|"be"\|"skipped", exit_price? }` |
| `DELETE` | `/api/journal/{id}` | 404 if the entry is not found |

The journal is manual. For automatic tracking of every plan the AI makes, see [Signal verification](signals.md).
