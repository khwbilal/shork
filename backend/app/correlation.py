"""Correlation and beta of a symbol to BTC and ETH (WL-036).

Pearson correlation of log returns and beta (cov / var of the benchmark) over two
windows: 30 days of 1h candles and 90 days of 1d candles. Candles are aligned on
open time; a window needs at least 60% of its expected candles in common, else that
benchmark is `available: false` with an error. Only closed candles are used.

Klines come from Binance spot, or USD-M futures for symbols that only trade there
(`.P` suffix or a usdm-only row in the `instruments` table). They are cached in
memory for 15 minutes per (market, symbol, interval). Nothing here raises to the
caller: every failure becomes `available: false` with an `error`.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

import httpx

logger = logging.getLogger(__name__)

BENCHMARKS = {"btc": "BTCUSDT", "eth": "ETHUSDT"}
# window key -> (interval, days, interval length in ms)
WINDOWS: dict[str, tuple[str, int, int]] = {
    "30d_1h": ("1h", 30, 3_600_000),
    "90d_1d": ("1d", 90, 86_400_000),
}
MIN_OVERLAP = 0.6
MIN_RETURNS = 10
CACHE_TTL = 15 * 60
HTTP_TIMEOUT = 10.0

_URLS = {
    "spot": "https://api.binance.com/api/v3/klines",
    "usdm": "https://fapi.binance.com/fapi/v1/klines",
}

_cache: dict[tuple[str, str, str], tuple[float, list[list[Any]]]] = {}
_cache_lock = threading.Lock()


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def resolve_market(symbol: str) -> tuple[str, str]:
    """(bare symbol, market) where market is spot or usdm, or "auto" when the catalogue does not know it."""
    from .symbols import normalize_user_symbol

    s = normalize_user_symbol(symbol)
    if s.endswith(".P"):
        return s[:-2], "usdm"
    try:
        from . import db

        with db.connect() as conn:
            rows = conn.execute(
                "SELECT market FROM instruments WHERE symbol = ? AND status = 'trading'", (s,)
            ).fetchall()
        markets = {r["market"] for r in rows}
    except Exception as exc:  # noqa: BLE001
        logger.warning("instrument lookup failed for %s: %s", s, exc)
        markets = set()
    if "spot" in markets:
        return s, "spot"
    if "usdm" in markets:
        return s, "usdm"
    return s, "auto"


def _http_klines(market: str, symbol: str, interval: str, limit: int) -> list[list[Any]]:
    with httpx.Client(timeout=HTTP_TIMEOUT) as client:
        r = client.get(_URLS[market], params={"symbol": symbol, "interval": interval, "limit": limit})
        if r.status_code != 200:
            raise RuntimeError(f"Binance {market} klines {symbol} {interval}: HTTP {r.status_code}")
        data = r.json()
    if not isinstance(data, list) or not data:
        raise RuntimeError(f"Binance {market} klines {symbol} {interval}: empty")
    return data


def fetch_klines(market: str, symbol: str, interval: str, limit: int) -> list[list[Any]]:
    """Cached klines; market "auto" tries spot, then USD-M futures."""
    key = (market, symbol, interval)
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CACHE_TTL:
            return hit[1]
    if market == "auto":
        try:
            data = _http_klines("spot", symbol, interval, limit)
        except Exception:  # noqa: BLE001
            data = _http_klines("usdm", symbol, interval, limit)
    else:
        data = _http_klines(market, symbol, interval, limit)
    with _cache_lock:
        _cache[key] = (now, data)
    return data


def _closes_by_time(klines: list[list[Any]], interval_ms: int, now_ms: int | None = None) -> dict[int, float]:
    """open time -> close, closed candles only."""
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    out: dict[int, float] = {}
    for k in klines:
        try:
            t, close = int(k[0]), float(k[4])
        except (TypeError, ValueError, IndexError):
            continue
        if t + interval_ms <= now_ms and close > 0:
            out[t] = close
    return out


def _pearson_beta(xs: list[float], ys: list[float]) -> tuple[float | None, float | None]:
    """(correlation of xs to ys, beta of xs to ys) where ys is the benchmark."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
    vx = sum((x - mx) ** 2 for x in xs) / n
    vy = sum((y - my) ** 2 for y in ys) / n
    if vy <= 0:
        return None, None
    beta = cov / vy
    corr = cov / math.sqrt(vx * vy) if vx > 0 else None
    if corr is not None:
        corr = max(-1.0, min(1.0, corr))
    return corr, beta


def pair_stats(
    sym_klines: list[list[Any]],
    bench_klines: list[list[Any]],
    interval_ms: int,
    expected: int,
    now_ms: int | None = None,
) -> dict[str, Any]:
    """Correlation and beta of log returns over aligned open times."""
    a = _closes_by_time(sym_klines, interval_ms, now_ms)
    b = _closes_by_time(bench_klines, interval_ms, now_ms)
    common = sorted(set(a) & set(b))[-expected:]
    overlap = len(common) / expected if expected else 0.0
    if overlap < MIN_OVERLAP:
        return {
            "available": False,
            "overlap_pct": round(overlap * 100, 1),
            "error": f"only {len(common)} of {expected} candles overlap (need {int(MIN_OVERLAP * 100)}%)",
        }
    xs: list[float] = []
    ys: list[float] = []
    for t0, t1 in zip(common, common[1:]):
        if t1 - t0 != interval_ms:
            continue  # a gap: never span it with one return
        xs.append(math.log(a[t1] / a[t0]))
        ys.append(math.log(b[t1] / b[t0]))
    if len(xs) < MIN_RETURNS:
        return {"available": False, "overlap_pct": round(overlap * 100, 1),
                "error": f"only {len(xs)} consecutive returns"}
    corr, beta = _pearson_beta(xs, ys)
    if corr is None or beta is None:
        return {"available": False, "overlap_pct": round(overlap * 100, 1),
                "error": "flat series, no variance"}
    return {
        "available": True,
        "correlation": round(corr, 3),
        "beta": round(beta, 3),
        "overlap_pct": round(overlap * 100, 1),
        "samples": len(xs),
    }


def compute_correlation(
    symbol: str,
    fetch: Callable[[str, str, str, int], list[list[Any]]] | None = None,
    now_ms: int | None = None,
) -> dict[str, Any]:
    """Correlation and beta to BTC and ETH for both windows. Never raises."""
    fetch = fetch or fetch_klines
    try:
        bare, market = resolve_market(symbol)
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "symbol": symbol, "error": str(exc)}
    bench_market = "usdm" if market == "usdm" else "spot"

    jobs: dict[tuple[str, str], tuple[str, str, str, int]] = {}
    for wkey, (interval, days, interval_ms) in WINDOWS.items():
        limit = days * 86_400_000 // interval_ms + 1  # one extra for the open candle
        jobs[(wkey, "sym")] = (market, bare, interval, limit)
        for name, bench in BENCHMARKS.items():
            jobs[(wkey, name)] = (bench_market, bench, interval, limit)

    def run(args: tuple[str, str, str, int]) -> tuple[list[list[Any]] | None, str | None]:
        try:
            return fetch(*args), None
        except Exception as exc:  # noqa: BLE001
            return None, str(exc)

    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        results = dict(zip(jobs, pool.map(run, jobs.values())))

    windows: dict[str, Any] = {}
    for wkey, (interval, days, interval_ms) in WINDOWS.items():
        expected = days * 86_400_000 // interval_ms
        win: dict[str, Any] = {"interval": interval, "days": days, "candles": expected}
        sym_k, sym_err = results[(wkey, "sym")]
        for name in BENCHMARKS:
            bench_k, bench_err = results[(wkey, name)]
            if sym_k is None or bench_k is None:
                win[name] = {"available": False, "error": sym_err or bench_err}
            else:
                try:
                    win[name] = pair_stats(sym_k, bench_k, interval_ms, expected, now_ms)
                except Exception as exc:  # noqa: BLE001
                    win[name] = {"available": False, "error": str(exc)}
        windows[wkey] = win

    available = any(w[n].get("available") for w in windows.values() for n in BENCHMARKS)
    out: dict[str, Any] = {
        "available": available,
        "symbol": bare,
        "market": market if market != "auto" else "spot_or_usdm",
        "windows": windows,
    }
    if available:
        out["summary"] = _summary(windows)
    else:
        errors = [w[n].get("error") for w in windows.values() for n in BENCHMARKS if w[n].get("error")]
        out["error"] = errors[0] if errors else "no data"
    return out


def _summary(windows: dict[str, Any]) -> str:
    parts = []
    for wkey, win in windows.items():
        bits = [
            f"{name.upper()} corr {win[name]['correlation']:+.2f} beta {win[name]['beta']:.2f}"
            for name in BENCHMARKS
            if win[name].get("available")
        ]
        if bits:
            parts.append(f"{wkey}: " + ", ".join(bits))
    return "; ".join(parts)


def condensed(corr: Any) -> dict[str, Any]:
    """Short form for the prompt block: per window, corr and beta per benchmark."""
    if not isinstance(corr, dict) or not corr.get("available"):
        return {"available": False}
    out: dict[str, Any] = {}
    for wkey, win in (corr.get("windows") or {}).items():
        row = {}
        for name in BENCHMARKS:
            stat = win.get(name) or {}
            if stat.get("available"):
                row[f"{name}_corr"] = stat.get("correlation")
                row[f"{name}_beta"] = stat.get("beta")
        if row:
            out[wkey] = row
    return out
