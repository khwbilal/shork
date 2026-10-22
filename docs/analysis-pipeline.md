# Analysis pipeline

`market.fetch_coin_context(symbol, exchange, timeframe)` builds the snapshot that drives a full analysis, a chat turn, and the debug endpoint `GET /api/market/{symbol}`. It runs in a worker thread and takes about 5 to 15 seconds, depending on how quickly TradingView and Binance respond.

## Steps

1. **Normalise the pair.** `SOLUSDT.P` → `SOLUSDT` for TA, keeping `BINANCE:SOLUSDT.P` for the chart.
2. **Primary-timeframe TA from TradingView.** Calls `tradingview_mcp.core.services.screener_service.analyze_coin`.
   - **Usable** → `data_source: "tradingview"`. Any missing fields (MACD, Stochastic, RVOL, ATR, EMA, ADX, Bollinger, VWAP, pivots, S/R, suggested levels, market structure) are filled from local Binance TA.
   - **Rate-limited or empty** → `data_source: "binance_local"`. Everything comes from `binance_ta.compute_local_analysis`, using 220 klines from Binance spot, then futures.
3. **Multi-timeframe from TradingView** (`run_multi_timeframe_analysis`), only when step 2 succeeded, because it burns retries while TradingView is rate-limiting. Otherwise a local single-timeframe note is used.
4. **Price.** Yahoo Finance via the TradingView package, falling back to the last kline close.
5. **Flow** (`flow.py`): Binance Futures funding, OI and its change, top-trader long/short (whales), global account long/short (retail), taker buy/sell ratio, basis, 24h change. Derived fields include `whale_bias`, `funding_bias`, `oi_price_signal` and `crowding`.
6. **Order book** (`orderbook.py`): imbalance across the top 50 levels, plus the top 5.
7. **Liquidity map** (`liquidity.py`): estimated liquidation prices at 5/10/25/50/100× leverage, weighted by OI and the long/short mix, a cascade ladder, book walls, and an optional Coinglass history. These produce a squeeze score.
8. **Local MTF pack and regime** (`confluence.py`): 15m, 1h, 4h and 1d local TA, plus BTC and ETH daily trend, BTC volatility, and the pair's strength against BTC.
9. **Setup classifier**: see [Setup classifier](features/setup-classifier.md).
10. **Confluence score**, with the setup filter applied: see [Confluence score](features/confluence-score.md).

## Snapshot shape (top-level keys)

```
symbol, exchange, timeframe, tv_symbol, yahoo_symbol, data_source,
coin_analysis, multi_timeframe, yahoo_price,
flow, orderbook, liquidity, mtf_local, regime, setup, confluence,
upcoming_events,     # high-impact macro events in the next 24 h (WL-039)
correlation,         # vs BTC and ETH, see api-reference.md (WL-036)
recorded_signal_id   # only on /api/analyze when a signal was archived
```

## From snapshot to prompt

`context_to_prompt_block` condenses the snapshot (`condense_market_context`) into compact JSON with empty values removed, and caps it at **8,000 characters** (a typical snapshot is about 4,500). `setup` and `confluence` come first, right after pair and price, because the guardrails depend on them. `upcoming_events` and a short form of `correlation` come last. If the block is still over budget, low-value sections (pivots, level hints, SMAs, …, and correlation last of all) are dropped whole, never cut mid-field. As a final resort the block is cut and ends with a truncation marker; the result, marker included, never exceeds the budget (WL-027). Run this to see exactly what the model receives:

```bash
curl -s "http://127.0.0.1:8000/api/market/SOLUSDT?timeframe=1h" | python -m json.tool
```

`/api/market` returns the full snapshot. The prompt block is the condensed subset.
