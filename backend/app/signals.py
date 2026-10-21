"""Signal archive + auto-verify against later candles (TP/SL outcome)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .binance_ta import normalize_timeframe

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SIGNALS_PATH = DATA_DIR / "signals.json"

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
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SIGNALS_PATH.exists():
        return []
    try:
        raw = json.loads(SIGNALS_PATH.read_text(encoding="utf-8"))
        return raw if isinstance(raw, list) else []
    except Exception:  # noqa: BLE001
        return []


def _save(rows: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SIGNALS_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def list_signals(limit: int = 80, symbol: str | None = None) -> list[dict[str, Any]]:
    rows = _load()
    if symbol:
        sym = symbol.upper().replace(".P", "")
        rows = [r for r in rows if (r.get("symbol") or "").replace(".P", "") == sym]
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return rows[:limit]


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

    rows = _load()
    # Deduplicate: same symbol/tf/bias/entry within 30 minutes
    now = datetime.now(timezone.utc)
    for r in rows[-15:]:
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
    rows.append(sig)
    _save(rows)
    return sig


def _fetch_klines_after(
    symbol: str,
    timeframe: str,
    after_ms: int,
    limit: int = 100,
) -> list[dict[str, float]]:
    """OHLCV bars strictly after signal time."""
    pair = symbol.upper().replace(".P", "").replace("/", "")
    interval = normalize_timeframe(timeframe)
    urls = [
        "https://api.binance.com/api/v3/klines",
        "https://fapi.binance.com/fapi/v1/klines",
    ]
    params = {
        "symbol": pair,
        "interval": interval,
        "startTime": after_ms,
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
                    # k[0]=open time ms
                    if int(k[0]) <= after_ms:
                        continue
                    out.append(
                        {
                            "t": int(k[0]),
                            "o": float(k[1]),
                            "h": float(k[2]),
                            "l": float(k[3]),
                            "c": float(k[4]),
                        }
                    )
                return out
            except Exception as exc:  # noqa: BLE001
                logger.debug("klines after failed %s: %s", url, exc)
    return []


def _resolve_outcome(
    bias: str,
    entry: float,
    sl: float,
    tp: float,
    bars: list[dict[str, float]],
) -> dict[str, Any]:
    """
    Walk bars in order. First touch of SL or TP wins.
    Same-bar both-hit → conservative: count as loss (SL assumed first).
    """
    for i, b in enumerate(bars):
        hi, lo = b["h"], b["l"]
        if bias == "Buy":
            hit_sl = lo <= sl
            hit_tp = hi >= tp
            if hit_sl and hit_tp:
                return {
                    "status": "loss",
                    "outcome": "same_bar_both (counted loss)",
                    "bars_checked": i + 1,
                    "hit_price": sl,
                    "hit_at": datetime.fromtimestamp(b["t"] / 1000, tz=timezone.utc).isoformat(),
                    "r_multiple": -1.0,
                }
            if hit_sl:
                return {
                    "status": "loss",
                    "outcome": "stop_hit",
                    "bars_checked": i + 1,
                    "hit_price": sl,
                    "hit_at": datetime.fromtimestamp(b["t"] / 1000, tz=timezone.utc).isoformat(),
                    "r_multiple": -1.0,
                }
            if hit_tp:
                risk = abs(entry - sl) or 1e-9
                r_mult = round((tp - entry) / risk, 2)
                return {
                    "status": "win",
                    "outcome": "target_hit",
                    "bars_checked": i + 1,
                    "hit_price": tp,
                    "hit_at": datetime.fromtimestamp(b["t"] / 1000, tz=timezone.utc).isoformat(),
                    "r_multiple": r_mult,
                }
        else:  # Sell
            hit_sl = hi >= sl
            hit_tp = lo <= tp
            if hit_sl and hit_tp:
                return {
                    "status": "loss",
                    "outcome": "same_bar_both (counted loss)",
                    "bars_checked": i + 1,
                    "hit_price": sl,
                    "hit_at": datetime.fromtimestamp(b["t"] / 1000, tz=timezone.utc).isoformat(),
                    "r_multiple": -1.0,
                }
            if hit_sl:
                return {
                    "status": "loss",
                    "outcome": "stop_hit",
                    "bars_checked": i + 1,
                    "hit_price": sl,
                    "hit_at": datetime.fromtimestamp(b["t"] / 1000, tz=timezone.utc).isoformat(),
                    "r_multiple": -1.0,
                }
            if hit_tp:
                risk = abs(entry - sl) or 1e-9
                r_mult = round((entry - tp) / risk, 2)
                return {
                    "status": "win",
                    "outcome": "target_hit",
                    "bars_checked": i + 1,
                    "hit_price": tp,
                    "hit_at": datetime.fromtimestamp(b["t"] / 1000, tz=timezone.utc).isoformat(),
                    "r_multiple": r_mult,
                }

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
    horizon = DEFAULT_HORIZON_BARS.get(normalize_timeframe(tf), 48)
    after_ms = int(created.timestamp() * 1000)
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
    rows = _load()
    for i, sig in enumerate(rows):
        if sig.get("id") == signal_id:
            rows[i] = verify_signal(sig, force=force)
            _save(rows)
            return rows[i]
    return None


def verify_all(
    *,
    symbol: str | None = None,
    only_open: bool = True,
    limit: int = 50,
) -> dict[str, Any]:
    rows = _load()
    updated = 0
    checked = 0
    for i, sig in enumerate(rows):
        if symbol and sig.get("symbol") != symbol.upper():
            continue
        if only_open and sig.get("status") not in ("open", None):
            continue
        if checked >= limit:
            break
        before = sig.get("status")
        rows[i] = verify_signal(sig, force=False)
        checked += 1
        if rows[i].get("status") != before:
            updated += 1
    _save(rows)
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
