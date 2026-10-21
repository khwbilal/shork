# Watchlist scorer

Scores a list of pairs for **setup quality** so you know where to look first. No AI call is made, so it is free to run.

**UI:** Watchlist → **Score watchlist** (uses the timeframe in the top bar). Takes about 20 to 40 seconds.
**API:** `GET /api/watchlist/score?timeframe=1h&symbols=BTCUSDT,ETHUSDT` or `POST /api/watchlist/score` with `{"symbols": [...], "timeframe": "1h"}`

Code: `backend/app/watchlist.py`.

## Default list

`BTCUSDT ETHUSDT SOLUSDT BNBUSDT XRPUSDT DOGEUSDT ADAUSDT AVAXUSDT LINKUSDT SUIUSDT`

Pass `symbols` to score your own list.

## Quality (0 to 100)

For each pair: local TA, the MTF pack, flow, regime, order book, liquidity, then the [confluence score](confluence-score.md) and the [setup](setup-classifier.md).

```
quality = 50 + confluence × 4
          − 25  if the setup is blocked (chop)
          + 8   if the setup is a breakout
          + book points × 5
          + liquidity points × 4
clamped to 0…100
```

A row is **actionable** when the trade is allowed, the bias is Buy or Sell, and quality ≥ 55. Rows are sorted by quality.

## Response

```json
{
  "timeframe": "1h", "count": 10, "actionable_count": 5,
  "rows": [{ "symbol": "BTCUSDT", "quality": 81, "bias": "Buy", "confluence": 6.9, "confidence": 0.9,
             "setup": "breakout", "trade_allowed": true, "mtf_alignment": "BULL_ALIGNED",
             "book_bias": "Ask-heavy", "liq_bias": "Balanced liquidity", "price": 84092.84, "summary": "…" }],
  "top": [/* best 5 */], "actionable": [/* best 5 actionable */]
}
```

## In the UI

A KPI strip (pairs scored, actionable count, top pick, timeframe) above a table with a quality bar, bias pill, confluence, setup chip (plus a chop pill when blocked), MTF, book, liquidity and price. **Open** loads the pair on the Desk.
