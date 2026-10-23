# Performance dashboard (WL-051)

Cards and charts over the [signal archive](signals.md), so you can see which [strategies](strategies.md) are working.

**UI:** rail → **Dashboard** (`#/dashboard`) on the React portal (`:5173`).
**API:** `GET /api/signals/dashboard`

## KPI strip

Hit rate, average R, open count, decided sample, best strategy, weakest strategy.

Best / weakest only appear when a strategy has at least **5** decided (win or loss) trades (`reliable`). Otherwise the UI shows `Na` with a short reason.

## Charts

1. Hit rate by strategy (horizontal bar; grey = small sample)
2. Average R by strategy
3. Cumulative R over time (overall plus per-strategy lines)
4. Outcomes by strategy (stacked win / loss / expired)
5. Signals per day (last 30 days)
6. Sample size vs hit rate (scatter; bubble size = decided count)

## Empty state

With no archived signals, the page shows an empty state pointing you to run a full analysis.
