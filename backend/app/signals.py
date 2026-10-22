"""Signal archive + auto-verify against later candles (TP/SL outcome).

Stored in the SQLite table `signals` (see db.py).
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from .binance_ta import normalize_timeframe
from .db import SIGNAL_COLUMNS, connect, from_db, insert_row, update_row

logger = logging.getLogger(__name__)

_TABLE = "signals"
_ORDER = "ORDER BY COALESCE(created_at, '') DESC, seq ASC"

# How many bars after signal to wait before marking expired
DEFAULT_HORIZON_BARS = {
    "15m": 48,  # ~12h
    "1h": 48,  # ~2d
    "4h": 42,  # ~7d
    "1d": 21,  # ~3w
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_ts(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None


def _load() -> list[dict[str, Any]]:
    """All rows in insertion order."""
    with connect() as conn:
        rows = conn.execute(f"SELECT * FROM {_TABLE} ORDER BY seq").fetchall()  # noqa: S608
    return [from_db(_TABLE, r) for r in rows]


def _save(rows: list[dict[str, Any]]) -> None:
    """Write back rows that already exist (verify results)."""
    with connect() as conn:
        for row in rows:
            update_row(conn, _TABLE, SIGNAL_COLUMNS, row)


def list_signals(limit: int = 80, symbol: str | None = None) -> list[dict[str, Any]]:
    # Newest first; equal timestamps keep insertion order (as the old stable sort did).
    where, params = "", []
    if symbol:
        sym = symbol.upper().replace(".P", "")
        where = "WHERE REPLACE(COALESCE(symbol, ''), '.P', '') = ?"
        params.append(sym)
    sql = f"SELECT * FROM {_TABLE} {where} {_ORDER}"  # noqa: S608
    with connect() as conn:
        if limit >= 0:
            rows = conn.execute(f"{sql} LIMIT ?", [*params, limit]).fetchall()
        else:
            rows = conn.execute(sql, params).fetchall()[:limit]
    return [from_db(_TABLE, r) for r in rows]


def record_signal(
    *,
    symbol: str,
    timeframe: str,
    levels: dict[str, Any],
    market: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Persist a Full-analysis call for later verification.
    Skips Neutral / missing entry-SL-TP (nothing to verify).
    """
    bias = levels.get("bias") or "Neutral"
    if bias not in ("Buy", "Sell"):
        return None
    entry = levels.get("entry")
    sl = levels.get("stop_loss")
    tp = levels.get("take_profit")
    if entry is None or sl is None or tp is None:
        return None

    market = market or {}
    coin = market.get("coin_analysis") if isinstance(market.get("coin_analysis"), dict) else {}
    price = ((coin.get("price_data") or {}).get("current_price")) or entry
    setup = market.get("setup") if isinstance(market.get("setup"), dict) else {}
    conf = market.get("confluence") if isinstance(market.get("confluence"), dict) else {}

    with connect() as conn:
        recent = conn.execute(
            f"SELECT * FROM {_TABLE} ORDER BY seq DESC LIMIT 15"  # noqa: S608
        ).fetchall()
    recent = [from_db(_TABLE, r) for r in reversed(recent)]
    # Deduplicate: same symbol/tf/bias/entry within 30 minutes
    now = datetime.now(timezone.utc)
    for r in recent:
        if (
            r.get("symbol") == symbol.upper()
            and r.get("timeframe") == timeframe
            and r.get("bias") == bias
            and r.get("entry") == entry
        ):
            created = _parse_ts(r.get("created_at"))
            if created and (now - created).total_seconds() < 1800:
                return r

    sig = {
        "id": str(uuid.uuid4())[:8],
        "created_at": _now(),
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "bias": bias,
        "entry": float(entry),
        "stop_loss": float(sl),
        "take_profit": float(tp),
        "price_at_signal": float(price) if price is not None else None,
        "setup": setup.get("type"),
        "trade_allowed": setup.get("trade_allowed"),
        "confluence": conf.get("score"),
        "confidence": levels.get("confidence") or conf.get("confidence"),
        "status": "open",  # open | win | loss | expired | invalid
        "outcome": None,
        "verified_at": None,
        "bars_checked": 0,
        "hit_price": None,
        "hit_at": None,
        "r_multiple": None,
        "notes": levels.get("reasoning") or "",
    }
    with connect() as conn:
        for _ in range(5):
            try:
                insert_row(conn, _TABLE, SIGNAL_COLUMNS, sig)
                break
            except sqlite3.IntegrityError:
                sig["id"] = str(uuid.uuid4())[:8]  # 8-char id collision, try another
        else:
            raise RuntimeError("could not allocate a signal id")
    return sig


def _interval_ms(interval: str) -> int:
    return {
        "1m": 60_000,
        "5m": 300_000,
        "15m": 900_000,
        "30m": 1_800_000,
        "1h": 3_600_000,
        "2h": 7_200_000,
        "4h": 14_400_000,
        "1d": 86_400_000,
        "1w": 604_800_000,
    }.get(interval, 3_600_000)


def _fetch_klines_after(
    symbol: str,
    timeframe: str,
    after_ms: int,
    limit: int = 100,
) -> list[dict[str, float]]:
    """OHLCV bars that overlap or start after the signal time.

    Includes the in-progress bar that contains the signal (needed for 1D / 4h
    plans opened mid-candle). Futures is tried first — many pairs are USDT-M only.
    """
    pair = symbol.upper().replace(".P", "").replace("/", "")
    interval = normalize_timeframe(timeframe)
    iv = _interval_ms(interval)
    # Pull one interval earlier so Binance returns the candle that was open at signal time.
    start_ms = max(0, after_ms - iv)
    urls = [
        "https://fapi.binance.com/fapi/v1/klines",
        "https://api.binance.com/api/v3/klines",
    ]
    params = {
        "symbol": pair,
        "interval": interval,
        "startTime": start_ms,
        "limit": min(limit, 500),
    }
    with httpx.Client(timeout=20.0) as client:
        for url in urls:
            try:
                r = client.get(url, params=params)
                if r.status_code != 200:
                    continue
                raw = r.json()
                out = []
                for k in raw:
                    open_t = int(k[0])
                    close_t = open_t + iv
                    # Skip bars that fully closed before the signal.
                    if close_t <= after_ms:
                        continue
                    out.append(
                        {
                            "t": open_t,
                            "o": float(k[1]),
                            "h": float(k[2]),
                            "l": float(k[3]),
                            "c": float(k[4]),
                        }
                    )
                if out:
                    return out
            except Exception as exc:  # noqa: BLE001
                logger.debug("klines after failed %s: %s", url, exc)
    return []


def _verify_timeframe(timeframe: str) -> tuple[str, int]:
    """Finer tape for TP/SL order + how many of those bars to walk."""
    tf = normalize_timeframe(timeframe)
    # (interval, max bars) — keep under Binance's 1500 cap
    return {
        "1w": ("4h", 84),
        "1d": ("1m", 1500),   # ~1 day of 1m is enough for most; more if still open
        "4h": ("1m", 1000),
        "2h": ("1m", 800),
        "1h": ("1m", 500),
        "30m": ("1m", 400),
        "15m": ("1m", 300),
        "5m": ("1m", 200),
    }.get(tf, (tf, DEFAULT_HORIZON_BARS.get(tf, 48)))


def _same_bar_bias(bias: str, open_px: float, hi: float, lo: float, sl: float, tp: float) -> str:
    """When one bar touches both levels, guess order from the open (closer extreme first)."""
    if bias == "Buy":
        # Dip distance vs rally distance from the open
        if (open_px - lo) <= (hi - open_px):
            return "sl"
        return "tp"
    if (hi - open_px) <= (open_px - lo):
        return "sl"
    return "tp"


def _resolve_outcome(
    bias: str,
    entry: float,
    sl: float,
    tp: float,
    bars: list[dict[str, float]],
) -> dict[str, Any]:
    """
    Walk bars in order. First touch of SL or TP wins.
    Same-bar both-hit → open-distance heuristic (not always loss).
    """
    risk = abs(entry - sl) or 1e-9

    def _hit_at(b: dict[str, float]) -> str:
        return datetime.fromtimestamp(b["t"] / 1000, tz=timezone.utc).isoformat()

    def _win(i: int, b: dict[str, float], note: str = "target_hit") -> dict[str, Any]:
        r_mult = round(((tp - entry) if bias == "Buy" else (entry - tp)) / risk, 2)
        return {
            "status": "win",
            "outcome": note,
            "bars_checked": i + 1,
            "hit_price": tp,
            "hit_at": _hit_at(b),
            "r_multiple": r_mult,
        }

    def _loss(i: int, b: dict[str, float], note: str = "stop_hit") -> dict[str, Any]:
        return {
            "status": "loss",
            "outcome": note,
            "bars_checked": i + 1,
            "hit_price": sl,
            "hit_at": _hit_at(b),
            "r_multiple": -1.0,
        }

    for i, b in enumerate(bars):
        hi, lo = b["h"], b["l"]
        open_px = float(b.get("o") or entry)
        if bias == "Buy":
            hit_sl = lo <= sl
            hit_tp = hi >= tp
        else:
            hit_sl = hi >= sl
            hit_tp = lo <= tp

        if hit_sl and hit_tp:
            first = _same_bar_bias(bias, open_px, hi, lo, sl, tp)
            if first == "tp":
                return _win(i, b, "same_bar_both (open heuristic → target)")
            return _loss(i, b, "same_bar_both (open heuristic → stop)")
        if hit_sl:
            return _loss(i, b)
        if hit_tp:
            return _win(i, b)

    return {
        "status": "open",
        "outcome": "neither_hit_yet",
        "bars_checked": len(bars),
        "hit_price": None,
        "hit_at": None,
        "r_multiple": None,
    }


def verify_signal(sig: dict[str, Any], force: bool = False) -> dict[str, Any]:
    """Update one signal's outcome from live candles."""
    if not force and sig.get("status") in ("win", "loss", "expired", "invalid"):
        return sig

    created = _parse_ts(sig.get("created_at"))
    if not created:
        sig["status"] = "invalid"
        sig["outcome"] = "bad_timestamp"
        return sig

    bias = sig.get("bias")
    entry = sig.get("entry")
    sl = sig.get("stop_loss")
    tp = sig.get("take_profit")
    if bias not in ("Buy", "Sell") or entry is None or sl is None or tp is None:
        sig["status"] = "invalid"
        sig["outcome"] = "incomplete_levels"
        return sig

    tf = sig.get("timeframe") or "1h"
    walk_tf, horizon = _verify_timeframe(tf)
    after_ms = int(created.timestamp() * 1000)
    bars = _fetch_klines_after(sig["symbol"], walk_tf, after_ms, limit=min(horizon + 5, 1500))
    # Fallback to the signal's own timeframe if the fine tape is empty
    if not bars and walk_tf != normalize_timeframe(tf):
        horizon = DEFAULT_HORIZON_BARS.get(normalize_timeframe(tf), 48)
        bars = _fetch_klines_after(sig["symbol"], tf, after_ms, limit=horizon + 5)

    if not bars:
        sig["verified_at"] = _now()
        sig["bars_checked"] = 0
        sig["outcome"] = "waiting_for_bars"
        return sig

    result = _resolve_outcome(bias, float(entry), float(sl), float(tp), bars[:horizon])
    sig.update(result)
    sig["verified_at"] = _now()

    if sig["status"] == "open" and len(bars) >= horizon:
        # Mark expired; mark-to-market R from last close
        last = bars[min(horizon, len(bars)) - 1]
        risk = abs(float(entry) - float(sl)) or 1e-9
        if bias == "Buy":
            pnl = last["c"] - float(entry)
        else:
            pnl = float(entry) - last["c"]
        sig["status"] = "expired"
        sig["outcome"] = "horizon_reached_no_tp_sl"
        sig["hit_price"] = last["c"]
        sig["r_multiple"] = round(pnl / risk, 2)

    return sig


def verify_one(signal_id: str, force: bool = True) -> dict[str, Any] | None:
    with connect() as conn:
        sig = from_db(_TABLE, conn.execute(
            f"SELECT * FROM {_TABLE} WHERE id = ?", (signal_id,)  # noqa: S608
        ).fetchone())
    if sig is None:
        return None
    # The candle fetch runs outside any open connection.
    sig = verify_signal(sig, force=force)
    _save([sig])
    return sig


def verify_all(
    *,
    symbol: str | None = None,
    only_open: bool = True,
    limit: int = 50,
) -> dict[str, Any]:
    rows = _load()
    updated = 0
    checked = 0
    touched: list[dict[str, Any]] = []
    for i, sig in enumerate(rows):
        if symbol and sig.get("symbol") != symbol.upper():
            continue
        if only_open and sig.get("status") not in ("open", None):
            continue
        if checked >= limit:
            break
        before = sig.get("status")
        rows[i] = verify_signal(sig, force=False)
        touched.append(rows[i])
        checked += 1
        if rows[i].get("status") != before:
            updated += 1
    _save(touched)  # only the verified rows; the rest are unchanged
    return {"checked": checked, "updated": updated, "stats": signal_stats()}


def signal_stats() -> dict[str, Any]:
    rows = _load()
    closed = [r for r in rows if r.get("status") in ("win", "loss", "expired")]
    wins = [r for r in closed if r.get("status") == "win"]
    losses = [r for r in closed if r.get("status") == "loss"]
    expired = [r for r in closed if r.get("status") == "expired"]
    open_n = sum(1 for r in rows if r.get("status") == "open")

    decided = wins + losses  # strict TP/SL
    hit = (len(wins) / len(decided)) if decided else None
    rs = [float(r["r_multiple"]) for r in closed if r.get("r_multiple") is not None]
    avg_r = round(sum(rs) / len(rs), 2) if rs else None

    by_setup: dict[str, dict[str, Any]] = {}
    for r in decided:
        key = r.get("setup") or "unknown"
        b = by_setup.setdefault(key, {"n": 0, "wins": 0})
        b["n"] += 1
        if r.get("status") == "win":
            b["wins"] += 1
    for v in by_setup.values():
        v["hit_rate"] = round(v["wins"] / v["n"], 2) if v["n"] else None

    return {
        "total": len(rows),
        "open": open_n,
        "wins": len(wins),
        "losses": len(losses),
        "expired": len(expired),
        "hit_rate": round(hit, 3) if hit is not None else None,
        "avg_r": avg_r,
        "by_setup": by_setup,
    }
