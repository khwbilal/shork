"""Batch score a watchlist of pairs for setup quality."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_WATCHLIST = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "SUIUSDT",
]


def score_pair(pair: str, timeframe: str = "1h") -> dict[str, Any]:
    """Lightweight score using local TA + setup + optional depth."""
    from .binance_ta import compute_local_analysis
    from .confluence import build_mtf_pack, build_regime, compute_confluence
    from .flow import fetch_flow_snapshot
    from .orderbook import fetch_orderbook_imbalance
    from .setup_classifier import apply_setup_to_confluence, classify_setup

    pair = pair.upper().replace("/", "")
    row: dict[str, Any] = {"symbol": pair, "timeframe": timeframe}

    try:
        primary = compute_local_analysis(pair, timeframe)
        mtf = build_mtf_pack(pair)
        try:
            flow = fetch_flow_snapshot(pair, timeframe)
        except Exception:  # noqa: BLE001
            flow = {"available": False}
        regime = build_regime(pair)
        try:
            book = fetch_orderbook_imbalance(pair)
        except Exception:  # noqa: BLE001
            book = {"available": False}

        try:
            from .liquidity import fetch_liquidity_map

            liq = fetch_liquidity_map(
                pair,
                mark_price=flow.get("mark_price"),
                open_interest=flow.get("open_interest"),
                whale_long_pct=flow.get("whale_long_pct"),
                retail_long_pct=flow.get("retail_long_pct"),
                funding_rate=flow.get("funding_rate"),
                oi_change_pct=flow.get("oi_change_pct"),
                price_change_24h_pct=flow.get("price_change_24h_pct"),
                orderbook=book,
            )
        except Exception:  # noqa: BLE001
            liq = {"available": False}

        conf = compute_confluence(primary, mtf, flow, regime, book, liq)
        setup = classify_setup(primary, mtf, flow)
        conf = apply_setup_to_confluence(conf, setup)

        # Watchlist quality score 0..100
        base = 50 + float(conf.get("score") or 0) * 4
        if setup.get("trade_allowed") is False:
            base -= 25
        if setup.get("type") == "breakout":
            base += 8
        if book.get("available"):
            base += float(book.get("points") or 0) * 5
        if liq.get("available"):
            base += float(liq.get("points") or 0) * 4
        quality = max(0, min(100, round(base)))

        px = (primary.get("price_data") or {}).get("current_price")
        row.update(
            {
                "price": px,
                "bias": conf.get("bias"),
                "confluence": conf.get("score"),
                "confidence": conf.get("confidence"),
                "setup": setup.get("type"),
                "trade_allowed": setup.get("trade_allowed"),
                "mtf_alignment": mtf.get("alignment"),
                "book_bias": book.get("bias") if book.get("available") else None,
                "book_imbalance": book.get("imbalance") if book.get("available") else None,
                "liq_bias": liq.get("bias") if liq.get("available") else None,
                "liq_points": liq.get("points") if liq.get("available") else None,
                "quality": quality,
                "summary": conf.get("summary"),
            }
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("watchlist score failed for %s: %s", pair, exc)
        row.update({"error": str(exc), "quality": 0, "bias": "Neutral"})

    return row


def score_watchlist(
    symbols: list[str] | None = None,
    timeframe: str = "1h",
) -> dict[str, Any]:
    symbols = symbols or list(DEFAULT_WATCHLIST)
    rows = [score_pair(s, timeframe) for s in symbols]
    rows.sort(key=lambda r: (-(r.get("quality") or 0), r.get("symbol") or ""))
    actionable = [
        r
        for r in rows
        if r.get("trade_allowed") and r.get("bias") in ("Buy", "Sell") and (r.get("quality") or 0) >= 55
    ]
    return {
        "timeframe": timeframe,
        "count": len(rows),
        "actionable_count": len(actionable),
        "rows": rows,
        "top": rows[:5],
        "actionable": actionable[:5],
    }
