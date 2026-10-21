# Symbol search

Find any Binance spot pair, USDⓈ-M perpetual, stock, ETF or commodity by typing part of its symbol or name.

**UI:** **Ctrl K** / **⌘K**, the search box, or the pair button in the top bar.
**API:** `GET /api/symbols/search?q=zec&exchange=BINANCE&limit=25` (max 40)

Code: `backend/app/symbols.py`

## How it works

- **Universe:** Binance pairs come from the local [instrument catalogue](#instrument-catalogue). Other venues (KuCoin, Gate.io, NASDAQ and so on) come from the coin list bundled in the TradingView package, cached in memory for 30 minutes. If the catalogue is still empty (first start), search falls back to fetching `exchangeInfo` live.
- **Names:** an FTS5 word-prefix match on the name also finds a pair: "gold" finds XAUUSDT and "crude oil" finds CLUSDT. A name-only match scores below a symbol match, so `<q>USDT` still wins.
- **Ranking:** an exact match first, then `<query>USDT` (spot ahead of the perp), then other pairs that start with the query. Pairs on the exchange selected in the top bar always rank above the same pair on other exchanges.
- **Perpetuals** carry a `.P` suffix (`BTWUSDT.P`). Input like `BTW-PERP`, `BTWUSDTPERP`, `BINANCE:BTWUSDT` or `btw/usdt` is normalised.
- **Analysis vs chart symbol:** analysis strips `.P` (TA runs on the base pair), while the chart keeps the exact TradingView symbol you picked.

## Result

```json
{ "results": [
  { "symbol": "ZECUSDT", "exchange": "BINANCE", "tv_symbol": "BINANCE:ZECUSDT", "kind": "spot", "label": "ZECUSDT · BINANCE spot", "type": "crypto", "name": "Zcash", "market": "spot" },
  { "symbol": "ZECUSDT.P", "exchange": "BINANCE", "tv_symbol": "BINANCE:ZECUSDT.P", "kind": "perp", "label": "ZECUSDT.P · BINANCE perp", "aliases": "ZECUSDT", "type": "crypto", "name": "Zcash", "market": "usdm" }
] }
```

## Instrument catalogue

Added in WL-044. Table `instruments` (see [Database](../database.md)) holds every TRADING Binance instrument with its name.

- **Refresh:** `instruments.refresh()` runs from the `instruments` [job](../scheduled-jobs.md) daily at 15:30, and once at startup when the table is empty. It reads spot and USD-M `exchangeInfo` and upserts the rows. Rows missing from the response are marked `delisted` and never deleted. A market whose fetch failed is skipped, so it never delists anything.
- **Count on 2026-10-21:** 2,183 instruments (1,387 spot, 796 USD-M). By type: crypto 1,956, stock 180, ETF 32, commodity 8, pre-IPO 4, index 2, FX 1. See [Binance instruments](../binance-instruments.md).
- **Type:** spot pairs are `crypto`, including tokenized "bStocks" such as NVDABUSDT. For USD-M, `underlyingType` decides: COIN is crypto; EQUITY, HK_EQUITY, KR_EQUITY and CN_EQUITY are stock, or ETF when the ticker is in the bundled ETF list; COMMODITY, FX, INDEX and PREMARKET map to their own type.
- **Names, first match wins:**
  1. Curated names in `backend/app/data/instrument_names.json`.
  2. For crypto: Binance's public asset list.
  3. For US stocks: the SEC `company_tickers.json` file (generic User-Agent, no personal data), or a bundled snapshot when SEC is down.
  4. Otherwise the ticker.

  154 names fell back to the ticker on 2026-10-21: 140 small coins and 14 unusual stock tickers. Add the missing ones to the JSON file.

## Palette behaviour

- **Before typing:** *Recent* (your last 6 pairs, stored in the browser) and *Go to* (the four pages).
- **While typing:** live results. ↑ and ↓ move, Enter opens, Esc closes. Enter with no match tries the text exactly as typed.
- Picking a pair updates the chart, the top bar and the chat placeholder, and clears the previous plan.
