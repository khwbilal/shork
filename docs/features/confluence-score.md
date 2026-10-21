# Confluence score

A deterministic score from **−10 (strong Sell) to +10 (strong Buy)**, built from seven components. It is the backbone of every analysis: the AI is told to respect it, and the backend enforces it afterwards (see the [guardrail](../ai-providers.md#what-happens-to-the-reply)).

Code: `backend/app/confluence.py` → `compute_confluence`, then `setup_classifier.apply_setup_to_confluence`.

## Components

| Component | Range | Built from |
|---|---|---|
| `mtf` | ±3.0 | Net trend score across 15m/1h/4h/1d (each −2…+2) ÷ 2.5 |
| `momentum` | ±2.5 | RSI zones (≥55 / ≤45, with overbought/oversold caution), MACD crossover, Stochastic, ADX ≥ 25 trend reinforcement, RVOL ≥ 1.5. Damped ×0.7 in a Bollinger squeeze. |
| `structure` | ±1.0 | Market-structure trend (Bullish / Bearish) |
| `flow` | ±2.5 | Whale bias ±1, taker bias ±0.5, crowded funding ∓0.6, OI change with whale side ±0.4, OI/price signal (long build, short build, short cover, long liquidation). Damped when crowded or unwinding. |
| `regime` | ±1.5 | BTC risk-on/off ±0.8, pair vs BTC ±0.4. Damped ×0.7 in high volatility. |
| `orderbook` | ±1.0 | Depth imbalance × 2.5 |
| `liquidity` | ±1.5 | Squeeze score from the [liquidity map](flow-and-liquidity.md#liquidity-map) |

The components are summed and clamped to ±10.

## Bias and confidence

| Score | Bias |
|---|---|
| ≥ +2.5 | Buy |
| −2.5 … +2.5 | **Neutral** (the dashed band on the gauge) |
| ≤ −2.5 | Sell |

Confidence = `min(0.92, 0.35 + |score| / 12)`. When ADX < 18 it is multiplied by 0.85, and a weak Buy or Sell (|score| < 3.5) is pushed back to Neutral.

## Setup adjustment

After the raw score, the [setup classifier](setup-classifier.md) adjusts it:

- **Chop / trade not allowed:** bias is forced to **Neutral** and the score is multiplied by 0.35 (`setup_chop` component).
- **Setup prefers Buy or Sell:** a ±0.6 nudge toward that side (`setup` component).
- **Mean-revert with |score| > 5:** damped ×0.85.
- A weak opposite bias (|score| < 4) does not override a clear setup preference.

## In the UI

The **Confluence** card on the Desk shows the score, a diverging gauge with the Neutral band dashed, and one bar per component (green for positive, red for negative). The KPI strip shows the score and the bias it prefers.
