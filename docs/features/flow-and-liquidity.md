# Flow, order book & liquidity

Three derivatives-market views, all from **public Binance endpoints** (no key needed). They only exist for pairs listed on Binance USDⓈ-M Futures. For spot-only pairs they come back with `available: false`, and the UI says so.

## Flow (`flow.py`)

Sampled at the analysis timeframe (15m … 1d):

| Field | Source | Meaning |
|---|---|---|
| `whale_long_pct`, `whale_bias` | `topLongShortPositionRatio` | Positioning of the top traders by size ("whales") |
| `retail_long_pct`, `retail_bias` | `globalLongShortAccountRatio` | Positioning of all accounts |
| `taker_buy_sell_ratio`, `taker_bias` | `takerlongshortRatio` | Aggressive buyers vs sellers |
| `open_interest`, `oi_change_pct` | `openInterest`, `openInterestHist` | Leverage building or unwinding |
| `funding_rate`, `funding_apr_est`, `funding_bias` | `premiumIndex` | Crowded long or crowded short |
| `basis_pct` | mark vs index | Futures premium |
| `oi_price_signal` | 24h price change × OI change | *Long build* (price↑ OI↑), *Short build* (price↓ OI↑), *Short cover*, *Long liquidation* |
| `crowding` | derived from the rows above | Set when one side is clearly crowded. Damps the flow score. |

## Order book (`orderbook.py`)

`imbalance = (bid_qty − ask_qty) / (bid_qty + ask_qty)` over the top 50 levels, using futures depth first and spot depth second. The top-5 imbalance and the spread in basis points are reported too.

| Imbalance | Bias |
|---|---|
| ≥ +12% | Bid-heavy |
| ≤ −12% | Ask-heavy |
| otherwise | Neutral |

Confluence points: `clamp(imbalance × 2.5, ±1)`.

## Liquidity map

`liquidity.py` estimates where leveraged positions would be liquidated, without an exchange-wide liquidation feed:

1. **Clusters.** For each of 5×, 10×, 25×, 50× and 100× leverage (weighted 8 / 28 / 32 / 22 / 10%), it computes the long-liquidation price below the mark and the short-liquidation price above it. Sizes come from OI × the long/short share, the share being a blend of whale and retail positioning.
2. **Cascade ladder.** How much size would be forced out if price moved X% down (long cascade) or up (short squeeze), and the price where that triggers.
3. **Book walls**, used as nearby liquidity pools.
4. **Coinglass history**, if `COINGLASS_API_KEY` is set.

The **squeeze score** (±1.5, positive = bullish) combines:

- Crowding: long share ≥ 62% → −0.55; ≤ 38% → +0.55.
- Funding extremes: ±0.35.
- Price/OI patterns, such as a rally on falling OI with shorts crowded.
- Proximity to the nearest cluster on the crowded side (within 2.5%).

| Points | Bias |
|---|---|
| ≥ +0.45 | Short-squeeze bias |
| ≤ −0.45 | Long-cascade bias |
| otherwise | Balanced liquidity |

> These are **estimates** from leverage assumptions, not exchange liquidation data. Treat the levels as likely magnets, not guarantees.

## In the UI

- **Whales & derivatives** card: whale and retail pills with % long, funding with estimated APR, OI Δ, taker flow, OI·price signal, basis, and 24h change.
- **Liquidity & order book** card: liquidity bias, long/short share, nearest long-liq and short-liq with their distance, cascade and squeeze triggers, book bias and imbalance.
