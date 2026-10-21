# Binance instruments

What Binance lists beyond crypto, from the research in WL-040, corrected in WL-044. Checked against Binance's public `exchangeInfo` on 2026-10-21.

## USD-M futures

There are 796 trading contracts. 225 of them carry the `TradFi` subtype with `contractType: TRADIFI_PERPETUAL`:

| `underlyingType` | Count | Examples |
|---|---|---|
| `EQUITY` | 187 | US stocks and ETFs: TSLAUSDT, NVDAUSDT, AAPLUSDT, MSTRUSDT, COINUSDT, SPYUSDT, QQQUSDT, EWJUSDT |
| `HK_EQUITY` | 15 | Hong Kong stocks |
| `KR_EQUITY` | 8 | Korean stocks |
| `CN_EQUITY` | 2 | Chinese stocks |
| `COMMODITY` | 8 | XAU (gold), XAG (silver), XPT, XPD, copper, crude oil CL and BZ, natural gas |
| `FX` | 1 | |
| `PREMARKET` | 4 | Pre-IPO contracts |

The rest are 565 crypto perpetuals, 4 crypto quarterlies and 2 index contracts. Klines and depth use the normal futures endpoints.

## Spot

There are 1,387 trading pairs. Besides crypto, spot lists **tokenized stocks ("bStocks")** such as NVDABUSDT ("NVIDIA (bStocks)") and TSLABUSDT. WL-040 first reported "no stocks on spot"; WL-044 found the bStocks. The catalogue types them as `crypto` on the spot market, and the calendar links earnings to them.

## Names

`exchangeInfo` gives no names. They come from the sources listed under [Symbol search: instrument catalogue](features/symbol-search.md#instrument-catalogue).

## Still open

- WL-041 covers analysis of these instruments. Whale flow and the liquidation map assume crypto futures data, and must show as missing for stocks rather than as zero.
