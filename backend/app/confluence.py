"""Multi-timeframe pack, market regime, and confluence score for signal guardrails."""

from __future__ import annotations

import logging
from typing import Any

from .binance_ta import compute_local_analysis

logger = logging.getLogger(__name__)

MTF_FRAMES = ("15m", "1h", "4h", "1d")


def build_mtf_pack(pair: str) -> dict[str, Any]:
    """Local MTF snapshot for 15m / 1h / 4h / 1d."""
    frames: dict[str, Any] = {}
    scores: list[int] = []
    for tf in MTF_FRAMES:
        try:
            a = compute_local_analysis(pair, tf)
            row = _tf_row(a)
            frames[tf] = row
            scores.append(int(row.get("score") or 0))
        except Exception as exc:  # noqa: BLE001
            logger.warning("MTF %s failed for %s: %s", tf, pair, exc)
            frames[tf] = {"error": str(exc), "score": 0, "trend": "Unknown"}

    net = sum(scores)
    aligned = _alignment_label(scores, frames)
    return {
        "timeframes": frames,
        "net_score": net,
        "alignment": aligned,
        "summary": " | ".join(
            f"{tf}:{(frames.get(tf) or {}).get('trend', '?')}"
            f"({(frames.get(tf) or {}).get('score', 0):+d})"
            for tf in MTF_FRAMES
            if isinstance(frames.get(tf), dict) and not frames[tf].get("error")
        ),
    }


def build_regime(pair: str) -> dict[str, Any]:
    """BTC/ETH backdrop + pair relative strength."""
    out: dict[str, Any] = {"available": False}
    try:
        btc = compute_local_analysis("BTCUSDT", "1d")
        eth = compute_local_analysis("ETHUSDT", "1d")
        asset_1d = None
        base = pair.upper().replace(".P", "")
        if base not in ("BTCUSDT", "ETHUSDT"):
            try:
                asset_1d = compute_local_analysis(base, "1d")
            except Exception:  # noqa: BLE001
                asset_1d = None

        # use 24h-ish from last bar; better use multi-bar — approximate with ATR regime
        btc_trend = (btc.get("market_structure") or {}).get("trend")
        eth_trend = (eth.get("market_structure") or {}).get("trend")
        btc_atr = ((btc.get("atr") or {}).get("percent_of_price")) or 0

        rel = None
        if asset_1d:
            a_trend = (asset_1d.get("market_structure") or {}).get("trend")
            a_rsi = (asset_1d.get("rsi") or {}).get("value")
            b_rsi = (btc.get("rsi") or {}).get("value")
            if a_rsi is not None and b_rsi is not None:
                if a_rsi > b_rsi + 5:
                    rel = "Outperforming BTC (RSI)"
                elif a_rsi < b_rsi - 5:
                    rel = "Underperforming BTC (RSI)"
                else:
                    rel = "In-line with BTC"
            else:
                rel = f"Asset 1D {a_trend} vs BTC {btc_trend}"

        vol_regime = "Normal"
        if btc_atr >= 4:
            vol_regime = "High"
        elif btc_atr <= 1.5:
            vol_regime = "Quiet"

        risk = "Risk-on"
        if btc_trend == "Bearish":
            risk = "Risk-off"
        elif btc_trend == "Neutral":
            risk = "Mixed"

        out = {
            "available": True,
            "btc_trend_1d": btc_trend,
            "btc_rsi_1d": (btc.get("rsi") or {}).get("value"),
            "btc_atr_pct_1d": btc_atr,
            "eth_trend_1d": eth_trend,
            "pair_vs_btc": rel,
            "volatility_regime": vol_regime,
            "risk_mode": risk,
            "summary": (
                f"BTC:{btc_trend} RSI={(btc.get('rsi') or {}).get('value')} | "
                f"ETH:{eth_trend} | Vol:{vol_regime} | Mode:{risk}"
                + (f" | {rel}" if rel else "")
            ),
        }
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("regime failed: %s", exc)
        return {"available": False, "error": str(exc)}


def compute_confluence(
    primary: dict[str, Any] | None,
    mtf: dict[str, Any] | None,
    flow: dict[str, Any] | None,
    regime: dict[str, Any] | None,
    orderbook: dict[str, Any] | None = None,
    liquidity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Score -10..+10 → Buy / Sell / Neutral with component breakdown.
    Positive favors Buy; negative favors Sell.
    """
    components: dict[str, float] = {}
    primary = primary or {}
    mtf = mtf or {}
    flow = flow or {}
    regime = regime or {}
    orderbook = orderbook or {}
    liquidity = liquidity or {}

    # --- MTF (weight high) ---
    net = float(mtf.get("net_score") or 0)
    # net roughly -8..+8 across 4 TFs scoring -2..+2
    mtf_pts = max(-3.0, min(3.0, net / 2.5))
    components["mtf"] = round(mtf_pts, 2)

    # --- Primary TF momentum ---
    mom = 0.0
    rsi = (primary.get("rsi") or {}).get("value")
    macd_x = (primary.get("macd") or {}).get("crossover")
    stoch_sig = (primary.get("stochastic") or {}).get("signal")
    adx = (primary.get("adx") or {}).get("value")
    rvol = primary.get("relative_volume")
    bb = primary.get("bollinger") or {}

    if rsi is not None:
        if rsi >= 55:
            mom += 0.6
        elif rsi <= 45:
            mom -= 0.6
        if rsi >= 70:
            mom -= 0.4  # overbought caution
        if rsi <= 30:
            mom += 0.4  # oversold bounce bias mild
    if macd_x == "Bullish":
        mom += 0.8
    elif macd_x == "Bearish":
        mom -= 0.8
    if stoch_sig == "Oversold":
        mom += 0.3
    elif stoch_sig == "Overbought":
        mom -= 0.3
    if adx is not None and adx >= 25:
        # reinforce trend direction from structure
        trend = (primary.get("market_structure") or {}).get("trend")
        if trend == "Bullish":
            mom += 0.5
        elif trend == "Bearish":
            mom -= 0.5
    if rvol is not None and rvol >= 1.5:
        mom += 0.3 if mom >= 0 else -0.3
    if bb.get("squeeze"):
        mom *= 0.7  # chop / wait — dampen
    components["momentum"] = round(max(-2.5, min(2.5, mom)), 2)

    # --- Structure / S-R distance ---
    struct = 0.0
    trend = (primary.get("market_structure") or {}).get("trend")
    if trend == "Bullish":
        struct += 1.0
    elif trend == "Bearish":
        struct -= 1.0
    components["structure"] = round(struct, 2)

    # --- Whales / flow ---
    flow_pts = 0.0
    if flow.get("available"):
        if flow.get("whale_bias") == "Long":
            flow_pts += 1.0
        elif flow.get("whale_bias") == "Short":
            flow_pts -= 1.0
        if flow.get("taker_bias") == "Buyers":
            flow_pts += 0.5
        elif flow.get("taker_bias") == "Sellers":
            flow_pts -= 0.5
        fb = flow.get("funding_bias") or ""
        if "crowded long" in fb.lower():
            flow_pts -= 0.6
        elif "crowded short" in fb.lower():
            flow_pts += 0.6
        oi = flow.get("oi_change_pct")
        if oi is not None:
            # rising OI with whale long = stronger; rising OI with whale short = stronger short
            if oi > 0.5 and flow.get("whale_bias") == "Long":
                flow_pts += 0.4
            elif oi > 0.5 and flow.get("whale_bias") == "Short":
                flow_pts -= 0.4
            elif oi < -0.5:
                flow_pts *= 0.8  # unwinding
        if flow.get("crowding"):
            flow_pts *= 0.75
        if flow.get("oi_price_signal"):
            # string flag from flow enrichment
            sig = str(flow.get("oi_price_signal"))
            if "long build" in sig.lower():
                flow_pts += 0.4
            elif "short build" in sig.lower():
                flow_pts -= 0.4
            elif "short cover" in sig.lower():
                flow_pts += 0.2
            elif "long liquidat" in sig.lower() or "long unwind" in sig.lower():
                flow_pts -= 0.2
    components["flow"] = round(max(-2.5, min(2.5, flow_pts)), 2)

    # --- Regime ---
    reg = 0.0
    if regime.get("available"):
        if regime.get("risk_mode") == "Risk-on":
            reg += 0.8
        elif regime.get("risk_mode") == "Risk-off":
            reg -= 0.8
        rel = regime.get("pair_vs_btc") or ""
        if "Outperforming" in rel:
            reg += 0.4
        elif "Underperforming" in rel:
            reg -= 0.4
        if regime.get("volatility_regime") == "High":
            reg *= 0.7
    components["regime"] = round(max(-1.5, min(1.5, reg)), 2)

    # --- Order book ---
    book_pts = 0.0
    if orderbook.get("available"):
        book_pts = float(orderbook.get("points") or 0)
    components["orderbook"] = round(max(-1.0, min(1.0, book_pts)), 2)

    # --- Liquidity map / squeeze ---
    liq_pts = 0.0
    if liquidity.get("available"):
        liq_pts = float(liquidity.get("points") or 0)
    components["liquidity"] = round(max(-1.5, min(1.5, liq_pts)), 2)

    total = sum(components.values())
    total = max(-10.0, min(10.0, total))

    if total >= 2.5:
        bias = "Buy"
    elif total <= -2.5:
        bias = "Sell"
    else:
        bias = "Neutral"

    # Confidence from |score| and ADX
    conf = min(0.92, 0.35 + abs(total) / 12.0)
    if adx is not None and adx < 18:
        conf *= 0.85
        if bias != "Neutral" and abs(total) < 3.5:
            bias = "Neutral"
            components["note_chop"] = 1.0

    return {
        "score": round(total, 2),
        "score_max": 10,
        "bias": bias,
        "confidence": round(conf, 2),
        "components": components,
        "guardrail": (
            f"Confluence {total:+.1f}/10 → preferred bias {bias}. "
            f"AI must not flip to the opposite side unless explaining a clear exception."
        ),
        "summary": (
            f"{bias} ({total:+.1f}) · "
            + ", ".join(f"{k}={v:+.1f}" for k, v in components.items() if k != "note_chop")
        ),
    }


def _tf_row(a: dict[str, Any]) -> dict[str, Any]:
    trend = (a.get("market_structure") or {}).get("trend") or "Neutral"
    rsi = (a.get("rsi") or {}).get("value")
    macd_x = (a.get("macd") or {}).get("crossover")
    adx = (a.get("adx") or {}).get("value")
    score = 0
    if trend == "Bullish":
        score += 1
    elif trend == "Bearish":
        score -= 1
    if rsi is not None:
        if rsi >= 55:
            score += 1
        elif rsi <= 45:
            score -= 1
    if macd_x == "Bullish":
        score += 1
    elif macd_x == "Bearish":
        score -= 1
    # clamp -2..+2
    score = max(-2, min(2, score))
    return {
        "trend": trend,
        "rsi": rsi,
        "macd": macd_x,
        "adx": adx,
        "atr_pct": (a.get("atr") or {}).get("percent_of_price"),
        "bb_pct_b": (a.get("bollinger") or {}).get("percent_b"),
        "score": score,
        "price": (a.get("price_data") or {}).get("current_price"),
    }


def _alignment_label(scores: list[int], frames: dict[str, Any]) -> str:
    if not scores:
        return "UNKNOWN"
    if all(s >= 1 for s in scores):
        return "BULL_ALIGNED"
    if all(s <= -1 for s in scores):
        return "BEAR_ALIGNED"
    htf = []
    for tf in ("1d", "4h"):
        s = (frames.get(tf) or {}).get("score")
        if isinstance(s, int):
            htf.append(s)
    if htf and all(s >= 1 for s in htf) and (frames.get("1h") or {}).get("score", 0) < 0:
        return "BULL_HTF_BEAR_LTF"
    if htf and all(s <= -1 for s in htf) and (frames.get("1h") or {}).get("score", 0) > 0:
        return "BEAR_HTF_BULL_LTF"
    return "MIXED"
