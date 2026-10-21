"""Symbol search for autocomplete (spot + perps)."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_CACHE: dict[str, Any] = {"ts": 0.0, "items": []}
_CACHE_TTL = 60 * 30  # 30 minutes


def normalize_user_symbol(symbol: str) -> str:
    """Keep dots for perps (BTWUSDT.P); strip junk only."""
    s = symbol.strip().upper().replace(" ", "")
    if ":" in s:
        s = s.split(":")[-1]
    s = s.replace("/", "").replace("-", "").replace("_", "")
    # BTWUSDTPERP / BTW-PERP style → .P
    if s.endswith("PERP"):
        s = s[:-4] + ".P"
    return s


def analysis_symbol(symbol: str) -> str:
    """Bare pair for TradingView-TA / coin APIs (no .P)."""
    s = normalize_user_symbol(symbol)
    if s.endswith(".P"):
        s = s[:-2]
    return s


def chart_tv_symbol(symbol: str, exchange: str) -> str:
    """TradingView widget symbol — keep .P for perps."""
    s = normalize_user_symbol(symbol)
    return f"{exchange.upper()}:{s}"


def _load_coinlist_items() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    try:
        from tradingview_mcp.core.services.coinlist import load_symbols
        from pathlib import Path
        import tradingview_mcp

        coin_dir = Path(tradingview_mcp.__file__).parent / "coinlist"
        exchanges = [p.stem.upper() for p in coin_dir.glob("*.txt")]
        for ex in exchanges:
            for sym in load_symbols(ex):
                bare = sym.split(":")[-1] if ":" in sym else sym
                items.append(
                    {
                        "symbol": bare,
                        "exchange": ex,
                        "tv_symbol": f"{ex}:{bare}",
                        "kind": "spot",
                        "label": f"{bare} · {ex} spot",
                    }
                )
    except Exception:  # noqa: BLE001
        logger.exception("coinlist load failed")
    return items


def _fetch_binance_universe() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    timeout = httpx.Timeout(20.0)
    try:
        with httpx.Client(timeout=timeout) as client:
            spot = client.get("https://api.binance.com/api/v3/exchangeInfo").json()
            for s in spot.get("symbols", []):
                if s.get("status") != "TRADING":
                    continue
                if s.get("quoteAsset") not in ("USDT", "USDC", "BTC", "ETH", "FDUSD"):
                    continue
                bare = s["symbol"]
                items.append(
                    {
                        "symbol": bare,
                        "exchange": "BINANCE",
                        "tv_symbol": f"BINANCE:{bare}",
                        "kind": "spot",
                        "label": f"{bare} · BINANCE spot",
                    }
                )

            fut = client.get("https://fapi.binance.com/fapi/v1/exchangeInfo").json()
            for s in fut.get("symbols", []):
                if s.get("status") != "TRADING":
                    continue
                if s.get("contractType") not in ("PERPETUAL", "CURRENT_QUARTER", "NEXT_QUARTER"):
                    continue
                bare = s["symbol"]
                # TradingView crypto perps commonly use SYMBOL.P
                tv_sym = f"{bare}.P"
                items.append(
                    {
                        "symbol": tv_sym,
                        "exchange": "BINANCE",
                        "tv_symbol": f"BINANCE:{tv_sym}",
                        "kind": "perp",
                        "label": f"{tv_sym} · BINANCE perp",
                        "aliases": bare,
                    }
                )
    except Exception:  # noqa: BLE001
        logger.exception("binance universe fetch failed")
    return items


def get_universe() -> list[dict[str, str]]:
    now = time.time()
    if _CACHE["items"] and now - float(_CACHE["ts"]) < _CACHE_TTL:
        return _CACHE["items"]  # type: ignore[return-value]

    merged: dict[str, dict[str, str]] = {}
    for it in _load_coinlist_items() + _fetch_binance_universe():
        key = f"{it['exchange']}:{it['symbol']}:{it['kind']}"
        merged[key] = it
    items = list(merged.values())
    _CACHE["items"] = items
    _CACHE["ts"] = now
    return items


def search_symbols(query: str, exchange: str | None = None, limit: int = 25) -> list[dict[str, str]]:
    q = normalize_user_symbol(query)
    if len(q) < 1:
        return []
    ex = exchange.upper() if exchange else None
    scored: list[tuple[int, dict[str, str]]] = []
    for it in get_universe():
        if ex and it["exchange"] != ex and ex != "ALL":
            # still allow BINANCE when user typed another exchange but leave soft
            pass
        sym = it["symbol"].upper()
        label = it["label"].upper()
        alias = str(it.get("aliases") or "").upper()
        tv = it["tv_symbol"].upper()
        if q not in sym and q not in label and q not in tv and q not in alias:
            continue
        score = 0
        if sym == q or alias == q:
            score = 100
        elif sym.startswith(q) or alias.startswith(q):
            score = 80
        elif q in sym or q in alias:
            score = 50
        else:
            score = 20
        if ex and it["exchange"] == ex:
            score += 10
        if it["kind"] == "perp" and (q.endswith(".P") or "PERP" in q):
            score += 15
        scored.append((score, it))

    scored.sort(key=lambda x: (-x[0], x[1]["symbol"]))
    # de-dupe by tv_symbol preferring higher score
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for _, it in scored:
        if it["tv_symbol"] in seen:
            continue
        seen.add(it["tv_symbol"])
        out.append(it)
        if len(out) >= limit:
            break
    return out
