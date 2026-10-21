"""Classify market setup and apply chop / style filters."""

from __future__ import annotations

from typing import Any


def classify_setup(
    primary: dict[str, Any] | None,
    mtf: dict[str, Any] | None,
    flow: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Returns setup type:
      chop | mean_revert | breakout | trend_continuation
    Plus trade_allowed + guidance notes.
    """
    primary = primary or {}
    mtf = mtf or {}
    flow = flow or {}

    adx = (primary.get("adx") or {}).get("value")
    bb = primary.get("bollinger") or {}
    squeeze = bool(bb.get("squeeze"))
    pct_b = bb.get("percent_b")
    rvol = primary.get("relative_volume")
    rsi = (primary.get("rsi") or {}).get("value")
    trend = (primary.get("market_structure") or {}).get("trend") or "Neutral"
    alignment = mtf.get("alignment") or "MIXED"
    net = float(mtf.get("net_score") or 0)

    reasons: list[str] = []
    setup = "trend_continuation"
    trade_allowed = True
    prefer_bias: str | None = None  # optional soft preference

    # --- Chop filter (highest priority) ---
    chop_hits = 0
    if adx is not None and adx < 18:
        chop_hits += 1
        reasons.append(f"ADX {adx:.1f} < 18 (weak trend)")
    if squeeze:
        chop_hits += 1
        reasons.append("BB squeeze")
    if alignment == "MIXED" and abs(net) <= 2:
        chop_hits += 1
        reasons.append("MTF mixed / low net score")

    if chop_hits >= 2:
        setup = "chop"
        trade_allowed = False
        prefer_bias = "Neutral"
        reasons.append("Chop filter: avoid breakout/trend entries")
        return _pack(setup, trade_allowed, prefer_bias, reasons, adx, alignment)

    # --- Breakout ---
    if squeeze is False and rvol is not None and rvol >= 1.6 and adx is not None and adx >= 20:
        if pct_b is not None and (pct_b >= 0.85 or pct_b <= 0.15):
            setup = "breakout"
            reasons.append(f"Expansion + RVOL {rvol} + extreme %B {pct_b}")
            if pct_b >= 0.85:
                prefer_bias = "Buy"
            else:
                prefer_bias = "Sell"
            return _pack(setup, trade_allowed, prefer_bias, reasons, adx, alignment)

    # --- Mean revert ---
    if (
        (adx is not None and adx < 22)
        or alignment in ("MIXED", "BULL_HTF_BEAR_LTF", "BEAR_HTF_BULL_LTF")
    ) and rsi is not None and (rsi <= 32 or rsi >= 68):
        setup = "mean_revert"
        reasons.append(f"Range-ish tape + RSI {rsi:.1f}")
        prefer_bias = "Buy" if rsi <= 32 else "Sell"
        # Don't fight strong HTF too hard
        if alignment == "BEAR_ALIGNED" and prefer_bias == "Buy":
            reasons.append("HTF bear aligned — mean-revert long is countertrend (caution)")
        if alignment == "BULL_ALIGNED" and prefer_bias == "Sell":
            reasons.append("HTF bull aligned — mean-revert short is countertrend (caution)")
        return _pack(setup, trade_allowed, prefer_bias, reasons, adx, alignment)

    # --- Trend continuation (default when not chop) ---
    setup = "trend_continuation"
    if alignment in ("BULL_ALIGNED",) or (trend == "Bullish" and net > 0):
        prefer_bias = "Buy"
        reasons.append("Trend continuation with bullish structure/MTF")
    elif alignment in ("BEAR_ALIGNED",) or (trend == "Bearish" and net < 0):
        prefer_bias = "Sell"
        reasons.append("Trend continuation with bearish structure/MTF")
    else:
        prefer_bias = None
        reasons.append("Mild trend continuation / wait for clearer pullback")

    if flow.get("available") and flow.get("crowding"):
        reasons.append(f"Crowding note: {flow.get('crowding')}")

    return _pack(setup, trade_allowed, prefer_bias, reasons, adx, alignment)


def apply_setup_to_confluence(
    confluence: dict[str, Any],
    setup: dict[str, Any],
) -> dict[str, Any]:
    """Mutate/return confluence with setup filter applied."""
    out = dict(confluence)
    out["setup"] = setup
    components = dict(out.get("components") or {})

    if not setup.get("trade_allowed") or setup.get("type") == "chop":
        out["bias"] = "Neutral"
        out["score"] = round(float(out.get("score") or 0) * 0.35, 2)
        conf = float(out.get("confidence") or 0.4) * 0.7
        out["confidence"] = round(min(conf, 0.45), 2)
        components["setup_chop"] = -1.0
        out["guardrail"] = (
            f"Setup=chop → force Neutral. {setup.get('summary')}. "
            "Do not take breakout/trend entries."
        )
    else:
        pref = setup.get("prefer_bias")
        score = float(out.get("score") or 0)
        # Soft pull toward setup preference
        if pref == "Buy" and score > -1:
            components["setup"] = 0.6
            score += 0.6
        elif pref == "Sell" and score < 1:
            components["setup"] = -0.6
            score -= 0.6
        # Mean-revert: damp if confluence fights extremes too hard without RSI context
        if setup.get("type") == "mean_revert" and abs(score) > 5:
            score *= 0.85
            components["setup_mr_dampen"] = -0.3
        # Re-threshold bias
        score = max(-10.0, min(10.0, score))
        if abs(score) < 2.5:
            bias = "Neutral"
        elif score >= 2.5:
            bias = "Buy"
        else:
            bias = "Sell"
        # Don't allow opposite of strong setup preference when aligned
        if pref and bias != "Neutral" and pref != bias and abs(score) < 4:
            bias = "Neutral"
        out["score"] = round(score, 2)
        out["bias"] = bias
        out["guardrail"] = (
            f"Setup={setup.get('type')} · confluence {score:+.1f} → {bias}. "
            f"{setup.get('summary')}"
        )

    out["components"] = {k: round(v, 2) if isinstance(v, float) else v for k, v in components.items()}
    out["summary"] = (
        f"{out.get('bias')} ({out.get('score'):+}) · setup={setup.get('type')} · "
        + ", ".join(
            f"{k}={v:+.1f}"
            for k, v in out["components"].items()
            if isinstance(v, (int, float)) and not str(k).startswith("note")
        )
    )
    return out


def _pack(
    setup: str,
    trade_allowed: bool,
    prefer_bias: str | None,
    reasons: list[str],
    adx: float | None,
    alignment: str,
) -> dict[str, Any]:
    return {
        "type": setup,
        "trade_allowed": trade_allowed,
        "prefer_bias": prefer_bias,
        "adx": adx,
        "mtf_alignment": alignment,
        "reasons": reasons,
        "summary": f"{setup.replace('_', ' ')}"
        + ("" if trade_allowed else " (no trade)")
        + (f" | prefer {prefer_bias}" if prefer_bias else "")
        + " -- "
        + "; ".join(reasons[:3]),
    }
