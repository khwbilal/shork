# Setup classifier

Labels the market as one of four setups and decides whether trading is allowed at all. A plan that ignores the setup type is usually the wrong plan: a breakout entry in chop, or a trend entry at a range extreme.

Code: `backend/app/setup_classifier.py` → `classify_setup(primary, mtf, flow)`.

## Rules (checked in this order)

### 1. Chop: trade **blocked**

Chop is called when **at least two** of these hold:

- ADX < 18 (weak trend)
- Bollinger squeeze
- MTF alignment `MIXED` with |net score| ≤ 2

Then `trade_allowed = false`, the preferred bias is Neutral, and the [confluence score](confluence-score.md) is forced to Neutral.

### 2. Breakout

No squeeze, RVOL ≥ 1.6, ADX ≥ 20, and Bollinger %B ≥ 0.85 (prefers **Buy**) or ≤ 0.15 (prefers **Sell**).

### 3. Mean revert

The tape looks like a range (ADX < 22, or MTF mixed or conflicting) and RSI is at an extreme: ≤ 32 prefers **Buy**, ≥ 68 prefers **Sell**. A trade against an aligned higher timeframe is flagged "countertrend (caution)".

### 4. Trend continuation (default)

Prefers Buy with `BULL_ALIGNED` MTF or bullish structure and net > 0, and Sell for the mirror image. Otherwise it has no preference ("wait for a clearer pullback"). A crowding note from flow is appended when present.

## Output

```json
{
  "type": "trend_continuation",
  "trade_allowed": true,
  "prefer_bias": "Buy",
  "adx": 27.05,
  "mtf_alignment": "BULL_ALIGNED",
  "reasons": ["Trend continuation with bullish structure/MTF", "Crowding note: Crowded long (top traders)"],
  "summary": "trend continuation | prefer Buy -- …"
}
```

## In the UI

The **Setup & timeframes** card shows the type, preferred side, ADX and MTF alignment, then one row per timeframe (RSI, MACD, ADX and a trend pill). A **No trade** pill appears when the chop filter blocks the setup. On the Watchlist, blocked rows carry a **chop** pill.
