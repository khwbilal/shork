"""Binance spot/futures order-book imbalance."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

SPOT = "https://api.binance.com"
FUTURES = "https://fapi.binance.com"


def fetch_orderbook_imbalance(pair: str, limit: int = 50) -> dict[str, Any]:
    """
    Depth imbalance: (bid_qty - ask_qty) / (bid_qty + ask_qty) on top N levels.
    Positive = more bids (buy pressure). Also reports best bid/ask spread.
    """
    symbol = pair.upper().replace(".P", "").replace("/", "")
    out: dict[str, Any] = {"available": False, "symbol": symbol}

    depth = None
    source = None
    endpoints = (
        (f"{FUTURES}/fapi/v1/depth", "futures"),
        (f"{SPOT}/api/v3/depth", "spot"),
    )
    for url, label in endpoints:
        try:
            with httpx.Client(timeout=12.0) as client:
                r = client.get(url, params={"symbol": symbol, "limit": limit})
                if r.status_code == 200:
                    depth = r.json()
                    source = label
                    break
        except Exception as exc:  # noqa: BLE001
            logger.debug("depth %s failed: %s", label, exc)

    if not depth:
        out["error"] = "depth unavailable"
        return out

    bids = depth.get("bids") or []
    asks = depth.get("asks") or []
    if not bids or not asks:
        out["error"] = "empty book"
        return out

    bid_qty = sum(float(q) for _, q in bids[:limit])
    ask_qty = sum(float(q) for _, q in asks[:limit])
    total = bid_qty + ask_qty
    imbalance = (bid_qty - ask_qty) / total if total else 0.0

    best_bid = float(bids[0][0])
    best_ask = float(asks[0][0])
    mid = (best_bid + best_ask) / 2
    spread_bps = ((best_ask - best_bid) / mid) * 10_000 if mid else None

    # Top-of-book pressure (first 5 levels)
    top_b = sum(float(q) for _, q in bids[:5])
    top_a = sum(float(q) for _, q in asks[:5])
    top_total = top_b + top_a
    top_imbalance = (top_b - top_a) / top_total if top_total else 0.0

    bias = "Neutral"
    if imbalance >= 0.12:
        bias = "Bid-heavy"
    elif imbalance <= -0.12:
        bias = "Ask-heavy"

    # Confluence-friendly points (-1..+1)
    points = max(-1.0, min(1.0, imbalance * 2.5))

    out.update(
        {
            "available": True,
            "source": source,
            "limit": limit,
            "bid_qty": round(bid_qty, 4),
            "ask_qty": round(ask_qty, 4),
            "imbalance": round(imbalance, 4),
            "top5_imbalance": round(top_imbalance, 4),
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread_bps": round(spread_bps, 2) if spread_bps is not None else None,
            "bias": bias,
            "points": round(points, 2),
            "summary": (
                f"{bias} imbalance {imbalance:+.2%} | top5 {top_imbalance:+.2%} | "
                f"spread {spread_bps:.1f}bps"
                if spread_bps is not None
                else f"{bias} {imbalance:+.2%}"
            ),
        }
    )
    return out
