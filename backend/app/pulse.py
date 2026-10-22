"""BTC and ETH pulse per timeframe (WL-035, backend).

For BTCUSDT and ETHUSDT: last price and 24h change from the Binance spot 24h
ticker, and per timeframe (1M, 1w, 1d, 1h, 15m) a trend, RSI 14, the change over
the last candle and a bias. The last candle is the live one, so values move
between polls.

Rules (stated in the response as `rule`):
- trend up when EMA20 > EMA50 and price > EMA20; down when EMA20 < EMA50 and
  price < EMA20; flat otherwise.
- bias Buy when the trend is up and RSI < 70; Sell when the trend is down and
  RSI > 30; Neutral otherwise (no trend, or stretched).

Every (symbol, tf) result and every ticker is cached for 20 seconds, so a UI can
poll every 15 to 30 seconds. All calls run concurrently with a short timeout, and
a failed cell is `available: false` on its own.
"""

from __future__ import annotations

import asyncio
import threading
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from .binance_ta import _ema, _rsi

SYMBOLS = ("BTCUSDT", "ETHUSDT")
TIMEFRAMES = ("1M", "1w", "1d", "1h", "15m")
KLINE_LIMIT = 120
CACHE_TTL = 20.0
HTTP_TIMEOUT = 5.0
RULE = (
    "trend up: EMA20 > EMA50 and price > EMA20; down: EMA20 < EMA50 and price < EMA20; else flat. "
    "bias Buy: trend up and RSI < 70; Sell: trend down and RSI > 30; else Neutral."
)

KLINES_URL = "https://api.binance.com/api/v3/klines"
TICKER_URL = "https://api.binance.com/api/v3/ticker/24hr"

_cache: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
_cache_lock = threading.Lock()


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def _cached(key: tuple[str, str]) -> dict[str, Any] | None:
    with _cache_lock:
        hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_TTL:
        return hit[1]
    return None


def _store(key: tuple[str, str], value: dict[str, Any]) -> dict[str, Any]:
    with _cache_lock:
        _cache[key] = (time.monotonic(), value)
    return value


async def _fetch_klines(client: httpx.AsyncClient, symbol: str, tf: str) -> list[list[Any]]:
    r = await client.get(KLINES_URL, params={"symbol": symbol, "interval": tf, "limit": KLINE_LIMIT})
    if r.status_code != 200:
        raise RuntimeError(f"klines {symbol} {tf}: HTTP {r.status_code}")
    data = r.json()
    if not isinstance(data, list) or not data:
        raise RuntimeError(f"klines {symbol} {tf}: empty")
    return data


async def _fetch_ticker(client: httpx.AsyncClient, symbol: str) -> dict[str, Any]:
    r = await client.get(TICKER_URL, params={"symbol": symbol})
    if r.status_code != 200:
        raise RuntimeError(f"ticker {symbol}: HTTP {r.status_code}")
    return r.json()


def trend_of(price: float, ema20: float, ema50: float) -> str:
    if ema20 > ema50 and price > ema20:
        return "up"
    if ema20 < ema50 and price < ema20:
        return "down"
    return "flat"


def bias_of(trend: str, rsi: float | None) -> str:
    if rsi is None:
        return "Neutral"
    if trend == "up" and rsi < 70:
        return "Buy"
    if trend == "down" and rsi > 30:
        return "Sell"
    return "Neutral"


def cell_from_klines(tf: str, klines: list[list[Any]]) -> dict[str, Any]:
    closes = [float(k[4]) for k in klines]
    if len(closes) < 51:
        return {"tf": tf, "available": False, "error": f"only {len(closes)} candles, need 51"}
    price = closes[-1]
    ema20 = _ema(closes, 20)[-1]
    ema50 = _ema(closes, 50)[-1]
    rsi = _rsi(closes, 14)
    if ema20 is None or ema50 is None:
        return {"tf": tf, "available": False, "error": "EMA not ready"}
    trend = trend_of(price, ema20, ema50)
    prev = closes[-2]
    return {
        "tf": tf,
        "available": True,
        "price": price,
        "trend": trend,
        "rsi": round(rsi, 1) if rsi is not None else None,
        "ema20": round(ema20, 8),
        "ema50": round(ema50, 8),
        "price_vs_ema20": "above" if price >= ema20 else "below",
        "change_pct": round((price - prev) / prev * 100, 2) if prev else None,
        "bias": bias_of(trend, rsi),
        "candle_open": datetime.fromtimestamp(int(klines[-1][0]) / 1000, tz=timezone.utc).isoformat(),
    }


async def _cell(client: httpx.AsyncClient, symbol: str, tf: str) -> dict[str, Any]:
    key = (symbol, tf)
    hit = _cached(key)
    if hit is not None:
        return hit
    try:
        cell = cell_from_klines(tf, await _fetch_klines(client, symbol, tf))
    except Exception as exc:  # noqa: BLE001
        cell = {"tf": tf, "available": False, "error": str(exc) or type(exc).__name__}
    return _store(key, cell)


async def _ticker(client: httpx.AsyncClient, symbol: str) -> dict[str, Any]:
    key = (symbol, "ticker")
    hit = _cached(key)
    if hit is not None:
        return hit
    try:
        t = await _fetch_ticker(client, symbol)
        out = {
            "available": True,
            "price": float(t["lastPrice"]),
            "change_24h_pct": round(float(t["priceChangePercent"]), 2),
        }
    except Exception as exc:  # noqa: BLE001
        out = {"available": False, "error": str(exc) or type(exc).__name__}
    return _store(key, out)


async def build_pulse() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        tickers = [_ticker(client, s) for s in SYMBOLS]
        cells = [_cell(client, s, tf) for s in SYMBOLS for tf in TIMEFRAMES]
        results = await asyncio.gather(*tickers, *cells)
    ticks = results[: len(SYMBOLS)]
    grid = results[len(SYMBOLS):]
    symbols = []
    for i, sym in enumerate(SYMBOLS):
        t = ticks[i]
        row = grid[i * len(TIMEFRAMES): (i + 1) * len(TIMEFRAMES)]
        symbols.append({
            "symbol": sym,
            "available": bool(t.get("available")),
            "price": t.get("price"),
            "change_24h_pct": t.get("change_24h_pct"),
            "error": t.get("error"),
            "timeframes": row,
        })
    return {
        "symbols": symbols,
        "timeframes": list(TIMEFRAMES),
        "rule": RULE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
