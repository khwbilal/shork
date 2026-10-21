"""
Liquidity / liquidation map — long cascade vs short squeeze pressure.

Uses:
  1) Estimated liq clusters from price × common leverages × OI / L-S mix (always on)
  2) Order-book walls as nearby liquidity pools
  3) Optional Coinglass API if COINGLASS_API_KEY is set
  4) Brief Binance forceOrder websocket sample (live tape when quiet = empty)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Typical retail leverage mix weights (sum ~1) — heuristic, not exchange truth
_LEV_WEIGHTS = {
    5: 0.08,
    10: 0.28,
    25: 0.32,
    50: 0.22,
    100: 0.10,
}

# Maintenance-margin fudge so levels sit slightly closer than pure 1/lev
_MM_FUDGE = 0.92


def fetch_liquidity_map(
    pair: str,
    *,
    mark_price: float | None = None,
    open_interest: float | None = None,
    whale_long_pct: float | None = None,
    retail_long_pct: float | None = None,
    funding_rate: float | None = None,
    oi_change_pct: float | None = None,
    price_change_24h_pct: float | None = None,
    orderbook: dict[str, Any] | None = None,
    coinglass_api_key: str | None = None,
    sample_live: bool = False,
) -> dict[str, Any]:
    symbol = pair.upper().replace(".P", "").replace("/", "")
    out: dict[str, Any] = {
        "available": False,
        "symbol": symbol,
        "source": "estimated",
    }

    price = mark_price
    oi = open_interest
    if price is None or oi is None:
        try:
            with httpx.Client(timeout=12.0) as client:
                if price is None:
                    prem = client.get(
                        f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}"
                    )
                    if prem.status_code == 200:
                        price = float(prem.json().get("markPrice") or 0) or None
                if oi is None:
                    oi_r = client.get(
                        f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"
                    )
                    if oi_r.status_code == 200:
                        oi = float(oi_r.json().get("openInterest") or 0) or None
        except Exception as exc:  # noqa: BLE001
            out["error"] = str(exc)
            return out

    if not price or price <= 0:
        out["error"] = "no mark price"
        return out

    # Long share of OI (0..1) from whale/retail blend
    long_share = _long_share(whale_long_pct, retail_long_pct)
    short_share = 1.0 - long_share
    oi_val = float(oi or 0)

    long_clusters: list[dict[str, Any]] = []
    short_clusters: list[dict[str, Any]] = []
    for lev, w in _LEV_WEIGHTS.items():
        dist = (1.0 / lev) * _MM_FUDGE
        long_px = round(price * (1.0 - dist), 6)
        short_px = round(price * (1.0 + dist), 6)
        long_size = round(oi_val * long_share * w, 2)
        short_size = round(oi_val * short_share * w, 2)
        long_clusters.append(
            {
                "leverage": lev,
                "price": long_px,
                "side": "long_liq",
                "est_size": long_size,
                "distance_pct": round((long_px - price) / price * 100, 3),
            }
        )
        short_clusters.append(
            {
                "leverage": lev,
                "price": short_px,
                "side": "short_liq",
                "est_size": short_size,
                "distance_pct": round((short_px - price) / price * 100, 3),
            }
        )

    # Cumulative cascade if price moves X%
    cascade = _cascade_ladder(price, oi_val, long_share, short_share)

    nearest_long = max(long_clusters, key=lambda c: c["price"])  # closest below = highest long_liq
    nearest_short = min(short_clusters, key=lambda c: c["price"])  # closest above

    # Book walls as liquidity magnets
    book_walls = _book_walls(orderbook, price)

    # Live tape optional (adds latency; off by default)
    tape = (
        _sample_force_orders(symbol, listen_s=2.5)
        if sample_live
        else {
            "available": False,
            "events": 0,
            "note": "live tape off (estimated map + flow only)",
        }
    )

    # Optional Coinglass enrich
    cg = None
    if coinglass_api_key:
        cg = _fetch_coinglass(symbol, coinglass_api_key)

    squeeze = _squeeze_score(
        price=price,
        long_share=long_share,
        funding_rate=funding_rate,
        oi_change_pct=oi_change_pct,
        price_change_24h_pct=price_change_24h_pct,
        nearest_long=nearest_long,
        nearest_short=nearest_short,
        cascade=cascade,
        tape=tape,
        cg=cg,
    )

    # Confluence-friendly points (-1.5..+1.5) — positive = bullish (short squeeze bias)
    points = float(squeeze.get("points") or 0)

    out.update(
        {
            "available": True,
            "mark_price": price,
            "open_interest": oi_val,
            "long_share_pct": round(long_share * 100, 1),
            "short_share_pct": round(short_share * 100, 1),
            "long_clusters": long_clusters,
            "short_clusters": short_clusters,
            "nearest_long_liq": nearest_long,
            "nearest_short_liq": nearest_short,
            "cascade": cascade,
            "book_walls": book_walls,
            "live_liquidations": tape,
            "coinglass": cg,
            "squeeze": squeeze,
            "points": round(points, 2),
            "bias": squeeze.get("bias") or "Neutral",
            "summary": squeeze.get("summary")
            or _default_summary(nearest_long, nearest_short, squeeze),
        }
    )
    return out


def _long_share(whale_long_pct: float | None, retail_long_pct: float | None) -> float:
    vals = []
    if whale_long_pct is not None:
        vals.append(whale_long_pct / 100.0)
    if retail_long_pct is not None:
        vals.append(retail_long_pct / 100.0)
    if not vals:
        return 0.5
    # Weight whales a bit more
    if len(vals) == 2:
        return max(0.15, min(0.85, vals[0] * 0.6 + vals[1] * 0.4))
    return max(0.15, min(0.85, vals[0]))


def _cascade_ladder(
    price: float,
    oi: float,
    long_share: float,
    short_share: float,
) -> dict[str, Any]:
    """Estimated OI that would be liquidated if price moves ±X%."""
    downs: list[dict[str, Any]] = []
    ups: list[dict[str, Any]] = []
    for pct in (1.0, 2.0, 3.0, 5.0, 8.0, 10.0):
        # Longs liquidated when drop >= ~1/lev
        long_hit = 0.0
        short_hit = 0.0
        for lev, w in _LEV_WEIGHTS.items():
            thresh = (1.0 / lev) * _MM_FUDGE * 100
            if pct >= thresh:
                long_hit += oi * long_share * w
                short_hit += oi * short_share * w
        downs.append(
            {
                "move_pct": -pct,
                "est_long_liq": round(long_hit, 2),
                "price": round(price * (1 - pct / 100), 6),
            }
        )
        ups.append(
            {
                "move_pct": pct,
                "est_short_liq": round(short_hit, 2),
                "price": round(price * (1 + pct / 100), 6),
            }
        )
    # Highlight the first meaningful cascade step (>= 15% of side OI)
    long_trigger = next((d for d in downs if d["est_long_liq"] >= oi * long_share * 0.15), downs[0])
    short_trigger = next((u for u in ups if u["est_short_liq"] >= oi * short_share * 0.15), ups[0])
    return {
        "down_moves": downs,
        "up_moves": ups,
        "long_cascade_trigger": long_trigger,
        "short_squeeze_trigger": short_trigger,
    }


def _book_walls(orderbook: dict[str, Any] | None, price: float) -> dict[str, Any]:
    if not orderbook or not orderbook.get("available"):
        return {"available": False}
    return {
        "available": True,
        "bias": orderbook.get("bias"),
        "imbalance": orderbook.get("imbalance"),
        "bid_qty": orderbook.get("bid_qty"),
        "ask_qty": orderbook.get("ask_qty"),
        "spread_bps": orderbook.get("spread_bps"),
        "note": "Depth walls can absorb or accelerate liquidations into magnets",
    }


def _sample_force_orders(symbol: str, listen_s: float = 3.0) -> dict[str, Any]:
    """Listen briefly to Binance forceOrder stream for recent liquidations."""
    empty = {
        "available": False,
        "events": 0,
        "long_liq_notional": 0.0,
        "short_liq_notional": 0.0,
        "note": "no live liquidations in sample window",
    }
    try:
        import websockets  # type: ignore
    except ImportError:
        empty["note"] = "websockets package not installed"
        return empty

    async def _run() -> dict[str, Any]:
        uri = f"wss://fstream.binance.com/ws/{symbol.lower()}@forceOrder"
        long_n = 0.0  # longs liquidated = exchange sells
        short_n = 0.0  # shorts liquidated = exchange buys
        events: list[dict[str, Any]] = []
        try:
            async with websockets.connect(uri, open_timeout=5, close_timeout=2) as ws:
                deadline = asyncio.get_event_loop().time() + listen_s
                while asyncio.get_event_loop().time() < deadline:
                    timeout = max(0.1, deadline - asyncio.get_event_loop().time())
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    except asyncio.TimeoutError:
                        break
                    msg = json.loads(raw)
                    o = msg.get("o") or msg
                    side = (o.get("S") or "").upper()  # SELL = long liq, BUY = short liq
                    qty = float(o.get("z") or o.get("q") or 0)
                    px = float(o.get("ap") or o.get("p") or 0)
                    notional = qty * px
                    if side == "SELL":
                        long_n += notional
                    elif side == "BUY":
                        short_n += notional
                    events.append(
                        {
                            "side": "long_liq" if side == "SELL" else "short_liq",
                            "price": px,
                            "qty": qty,
                            "notional": round(notional, 2),
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            return {**empty, "note": f"ws: {exc}"}

        if not events:
            return empty
        bias = "Neutral"
        if short_n > long_n * 1.4:
            bias = "Short-squeeze tape"
        elif long_n > short_n * 1.4:
            bias = "Long-cascade tape"
        return {
            "available": True,
            "events": len(events),
            "long_liq_notional": round(long_n, 2),
            "short_liq_notional": round(short_n, 2),
            "bias": bias,
            "samples": events[-8:],
            "note": f"{len(events)} force orders in {listen_s:.0f}s sample",
        }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        # Already in event loop — skip live tape
        return {**empty, "note": "async loop busy; skipped live tape"}
    except Exception as exc:  # noqa: BLE001
        return {**empty, "note": str(exc)}


def _fetch_coinglass(symbol: str, api_key: str) -> dict[str, Any] | None:
    """Optional Coinglass liquidation history (needs API key)."""
    # Coinglass wants base like BTC not BTCUSDT
    base = symbol.replace("USDT", "").replace("USD", "")
    headers = {"CG-API-KEY": api_key, "accept": "application/json"}
    urls = [
        (
            "https://open-api-v4.coinglass.com/api/futures/liquidation/aggregated-history",
            {"exchange_list": "Binance", "symbol": base, "interval": "h1", "limit": 12},
        ),
        (
            "https://open-api.coinglass.com/public/v2/liquidation_history",
            {"symbol": base, "time_type": "h1"},
        ),
    ]
    try:
        with httpx.Client(timeout=12.0, headers=headers) as client:
            for url, params in urls:
                r = client.get(url, params=params)
                if r.status_code != 200:
                    continue
                data = r.json()
                if isinstance(data, dict) and data.get("success") is False:
                    continue
                return {"available": True, "raw": data, "source": url}
    except Exception as exc:  # noqa: BLE001
        logger.debug("coinglass failed: %s", exc)
    return {"available": False, "note": "Coinglass unavailable or key rejected"}


def _squeeze_score(
    *,
    price: float,
    long_share: float,
    funding_rate: float | None,
    oi_change_pct: float | None,
    price_change_24h_pct: float | None,
    nearest_long: dict[str, Any],
    nearest_short: dict[str, Any],
    cascade: dict[str, Any],
    tape: dict[str, Any],
    cg: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Positive points → short-squeeze / bullish liq pressure.
    Negative points → long-cascade / bearish liq pressure.
    """
    pts = 0.0
    reasons: list[str] = []

    # Crowding
    if long_share >= 0.62:
        pts -= 0.55
        reasons.append(f"Crowded longs ({long_share*100:.0f}%) - cascade risk on dips")
    elif long_share <= 0.38:
        pts += 0.55
        reasons.append(f"Crowded shorts ({(1-long_share)*100:.0f}%) - squeeze fuel on rallies")

    # Funding
    if funding_rate is not None:
        if funding_rate >= 0.0003:
            pts -= 0.35
            reasons.append("Positive funding - longs paying / short-squeeze less likely")
        elif funding_rate <= -0.0003:
            pts += 0.35
            reasons.append("Negative funding - shorts paying / short-squeeze fuel")

    # Price + OI
    if price_change_24h_pct is not None and oi_change_pct is not None:
        if price_change_24h_pct > 1 and oi_change_pct < -0.3 and long_share <= 0.45:
            pts += 0.4
            reasons.append("Rally + OI down with short-heavy book (cover / squeeze)")
        if price_change_24h_pct < -1 and oi_change_pct < -0.3 and long_share >= 0.55:
            pts -= 0.4
            reasons.append("Dump + OI down with long-heavy book (long unwind / cascade)")
        if price_change_24h_pct < -1 and oi_change_pct > 0.4 and long_share >= 0.55:
            pts -= 0.35
            reasons.append("Dump + OI up - new shorts + long pain")
        if price_change_24h_pct > 1 and oi_change_pct > 0.4 and long_share <= 0.45:
            pts += 0.25
            reasons.append("Rally + OI up into shorts - squeeze pressure building")

    # Distance to magnets
    long_dist = abs(float(nearest_long.get("distance_pct") or 0))
    short_dist = abs(float(nearest_short.get("distance_pct") or 0))
    if short_dist <= 2.5 and long_share <= 0.45:
        pts += 0.3
        reasons.append(f"Near short-liq magnet @{nearest_short.get('price')} ({short_dist:.1f}%)")
    if long_dist <= 2.5 and long_share >= 0.55:
        pts -= 0.3
        reasons.append(f"Near long-liq magnet @{nearest_long.get('price')} ({long_dist:.1f}%)")

    # Live tape
    if tape.get("available"):
        if tape.get("bias") == "Short-squeeze tape":
            pts += 0.5
            reasons.append("Live tape: shorts being liquidated")
        elif tape.get("bias") == "Long-cascade tape":
            pts -= 0.5
            reasons.append("Live tape: longs being liquidated")

    # Coinglass crude parse if present
    if cg and cg.get("available"):
        reasons.append("Coinglass data attached")

    pts = max(-1.5, min(1.5, pts))
    if pts >= 0.45:
        bias = "Short-squeeze bias"
        lean = "Buy"
    elif pts <= -0.45:
        bias = "Long-cascade bias"
        lean = "Sell"
    else:
        bias = "Balanced liquidity"
        lean = "Neutral"

    sq = cascade.get("short_squeeze_trigger") or {}
    lq = cascade.get("long_cascade_trigger") or {}

    summary = (
        f"{bias} ({pts:+.2f}) | "
        f"next short-liq ~{sq.get('move_pct')}%/@{sq.get('price')} | "
        f"next long-liq ~{lq.get('move_pct')}%/@{lq.get('price')} | "
        + "; ".join(reasons[:3])
    )

    return {
        "points": round(pts, 2),
        "bias": bias,
        "lean": lean,
        "reasons": reasons,
        "summary": summary,
        "nearest_long_liq_price": nearest_long.get("price"),
        "nearest_short_liq_price": nearest_short.get("price"),
    }


def _default_summary(nearest_long: dict, nearest_short: dict, squeeze: dict) -> str:
    return (
        f"{squeeze.get('bias')} | "
        f"long-liq {nearest_long.get('price')} ({nearest_long.get('distance_pct')}%) | "
        f"short-liq {nearest_short.get('price')} ({nearest_short.get('distance_pct')}%)"
    )
