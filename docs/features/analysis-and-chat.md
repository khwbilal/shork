# Analysis & chat

The Desk page has two ways to ask the AI: **Full analysis** gives a structured trade plan, and the **Analyst** chat answers follow-up questions.

## Full analysis

**UI:** Desk → **Full analysis** · **API:** `POST /api/analyze`

```json
{ "symbol": "SOLUSDT", "exchange": "BINANCE", "timeframe": "1h", "custom_prompt": "optional trader notes" }
```

1. Builds the [market snapshot](../analysis-pipeline.md).
2. Sends it to the [AI provider](../ai-providers.md) with the desk-analyst prompt, which asks for a fixed card: BIAS, SETUP, SCORE, TREND, MTF, BOOK, LIQ, FLOW, REGIME, ENTRY, STOP, TARGET, SUPPORT, RESISTANCE, R:R, CONFIDENCE, WHY, PLAN, followed by a JSON block with the levels.
3. Parses the levels, fills gaps from local TA, and applies the [confluence and reward:risk guards](../ai-providers.md#what-happens-to-the-reply).
4. If an AI made the call and the result is a Buy or Sell with entry, stop and target, it is archived as a [signal](signals.md).

**Response** (abridged):

```json
{
  "symbol": "SOLUSDT", "exchange": "BINANCE", "timeframe": "1h",
  "tv_symbol": "BINANCE:SOLUSDT",
  "provider": "claude",
  "levels": {
    "bias": "Buy", "entry": 107.25, "stop_loss": 103.39, "take_profit": 108.53,
    "support": 103.67, "resistance": 108.25, "support_2": 105.8, "resistance_2": 108.25,
    "trend": "Bullish", "trend_line": "…", "ema20": 106.46, "ema50": 105.8,
    "confidence": 0.57, "reasoning": "…"
  },
  "analysis": "BIAS: Buy\nSETUP: trend_continuation — trade ok? yes\n…",
  "market": { "...": "full snapshot, see analysis-pipeline.md" }
}
```

### What the UI does with it

- **KPI strip:** bias, confluence, setup, entry (with SL and TP), reward:risk with confidence, price with 24h change.
- **Structure levels:** every returned level plus the last price, sorted from high to low, each with its own colour.
- **Insight cards:** confluence breakdown, setup and timeframes, whales and derivatives, liquidity and order book.
- **Analyst panel:** a trade card followed by the formatted reply.
- **Log to journal** becomes available.

Changing the pair or the timeframe clears these, so a plan is never shown against a pair or timeframe it wasn't made for.

## Chat

**UI:** the Analyst composer (Enter sends, Shift+Enter adds a new line). The suggestion chips send common questions.
**API:** `POST /api/chat`

```json
{
  "symbol": "SOLUSDT", "exchange": "BINANCE", "timeframe": "1h",
  "message": "Where is the invalidation?",
  "history": [{ "role": "user", "content": "…" }, { "role": "assistant", "content": "…" }]
}
```

Every chat turn fetches a **fresh** snapshot, so answers reflect the current tape. The prompt includes the last 6 history messages and asks for a reply under 120 words that leads with Bias / Entry / Stop / Target when relevant. Chat replies are not archived as signals.

**Clear** in the panel header resets the conversation. History lives only in the browser tab.
