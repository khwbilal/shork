"""Pull live technical context — TradingView first, Binance local fallback."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from .binance_ta import (
    apply_strategy_risk_to_analysis,
    coin_analysis_usable,
    compute_local_analysis,
    normalize_timeframe,
    pick_indicator_blocks,
)
from .config import Settings
from .strategies import get_strategy, needed_timeframes, resolve_timeframes, risk_public, strategy_public

logger = logging.getLogger(__name__)


def normalize_pair(symbol: str) -> str:
    """Bare spot-style pair for TA APIs (strips .P)."""
    from .symbols import analysis_symbol

    return analysis_symbol(symbol)


def tv_symbol(symbol: str, exchange: str) -> str:
    from .symbols import chart_tv_symbol

    return chart_tv_symbol(symbol, exchange)


def yahoo_symbol(symbol: str) -> str:
    pair = normalize_pair(symbol)
    for quote in ("USDT", "USDC", "BUSD", "USD"):
        if pair.endswith(quote):
            base = pair[: -len(quote)]
            return f"{base}-USD"
    return f"{pair}-USD"


def _safe_call(fn, *args, **kwargs) -> Any:
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Market call failed: %s — %s", getattr(fn, "__name__", fn), exc)
        return {"error": str(exc), "ok": False}


def _to_dict(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list, str, int, float, bool)):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    try:
        return json.loads(json.dumps(value, default=str))
    except Exception:  # noqa: BLE001
        return {"raw": str(value)}


def _attach_strategy_meta(
    context: dict[str, Any],
    *,
    strategy_id: str,
    primary_tf: str,
    context_tfs: list[str],
    overridden: bool,
    desk_tf: str,
) -> None:
    strategy = get_strategy(strategy_id)
    context["strategy_id"] = strategy.id
    context["strategy"] = strategy_public(strategy)
    context["strategy_tf"] = {
        "desk_tf": normalize_timeframe(desk_tf),
        "primary_tf": primary_tf,
        "context_tfs": context_tfs,
        "overridden": overridden,
    }
    if strategy.prompt_rules:
        context["strategy_rules"] = strategy.prompt_rules
    context["strategy_risk"] = risk_public(strategy.risk)


def _apply_risk_to_coin(coin: dict[str, Any] | None, strategy) -> dict[str, Any] | None:
    if not isinstance(coin, dict):
        return coin
    r = strategy.risk
    return apply_strategy_risk_to_analysis(
        coin,
        stop_atr_min=r.stop_atr_min,
        stop_atr_max=r.stop_atr_max,
        target_r_min=r.target_r_min,
    )


def _build_named_strategy_pack(
    pair: str,
    exchange: str,
    desk_tf: str,
    settings: Settings,
    strategy_id: str,
) -> dict[str, Any]:
    """Fetch only the TFs and indicators the named strategy needs."""
    strategy = get_strategy(strategy_id)
    primary_tf, context_tfs, overridden = resolve_timeframes(strategy, desk_tf)
    context: dict[str, Any] = {
        "symbol": pair,
        "exchange": exchange.upper(),
        "timeframe": primary_tf,
        "tv_symbol": tv_symbol(pair, exchange),
        "yahoo_symbol": yahoo_symbol(pair),
        "data_source": "binance_local",
    }
    _attach_strategy_meta(
        context,
        strategy_id=strategy.id,
        primary_tf=primary_tf,
        context_tfs=context_tfs,
        overridden=overridden,
        desk_tf=desk_tf,
    )

    # Fetch a full indicator pack for every required TF (primary + all context).
    needed = needed_timeframes(strategy, desk_tf)
    frames: dict[str, Any] = {}
    primary: dict[str, Any] = {"ok": False}
    risk = strategy.risk
    for tf in needed:
        try:
            analysis = compute_local_analysis(
                pair,
                tf,
                stop_atr_min=risk.stop_atr_min,
                stop_atr_max=risk.stop_atr_max,
                target_r_min=risk.target_r_min,
            )
            frames[tf] = pick_indicator_blocks(analysis, strategy.indicators)
            if tf == primary_tf:
                primary = analysis
        except Exception as exc:  # noqa: BLE001
            logger.warning("strategy TA failed for %s %s: %s", pair, tf, exc)
            frames[tf] = {"error": str(exc), "available": False}
            if tf == primary_tf:
                primary = {"error": str(exc), "ok": False}
    context["coin_analysis"] = _apply_risk_to_coin(
        primary if isinstance(primary, dict) else None, strategy
    ) or primary
    context["strategy_pack"] = {
        "id": strategy.id,
        "label": strategy.label,
        "indicators": list(strategy.indicators),
        "needed_tfs": needed,
        "timeframes": frames,
    }

    # Light MTF alignment from pack frames (structure / EMA trend).
    mtf_notes = []
    for tf_key, block in frames.items():
        if not isinstance(block, dict) or block.get("error"):
            continue
        struct = block.get("structure") or {}
        ema = block.get("ema") or {}
        mtf_notes.append(
            {
                "tf": tf_key,
                "structure_bias": struct.get("bias"),
                "bos": struct.get("bos"),
                "choch": struct.get("choch"),
                "ema20": ema.get("ema20"),
                "ema50": ema.get("ema50"),
            }
        )
    context["mtf_local"] = {
        "alignment": "strategy_pack",
        "timeframes": {n["tf"]: n for n in mtf_notes},
    }

    if strategy.needs_orderbook:
        try:
            from .orderbook import fetch_orderbook_imbalance

            context["orderbook"] = fetch_orderbook_imbalance(pair)
        except Exception as exc:  # noqa: BLE001
            context["orderbook"] = {"available": False, "error": str(exc)}

    if strategy.needs_liquidity:
        try:
            from .flow import fetch_flow_snapshot
            from .liquidity import fetch_liquidity_map

            flow = fetch_flow_snapshot(pair, primary_tf)
            context["flow"] = flow
            book = context.get("orderbook") if isinstance(context.get("orderbook"), dict) else {}
            context["liquidity"] = fetch_liquidity_map(
                pair,
                mark_price=flow.get("mark_price"),
                open_interest=flow.get("open_interest"),
                whale_long_pct=flow.get("whale_long_pct"),
                retail_long_pct=flow.get("retail_long_pct"),
                funding_rate=flow.get("funding_rate"),
                oi_change_pct=flow.get("oi_change_pct"),
                price_change_24h_pct=flow.get("price_change_24h_pct"),
                orderbook=book,
                coinglass_api_key=getattr(settings, "coinglass_api_key", None),
            )
        except Exception as exc:  # noqa: BLE001
            context["liquidity"] = {"available": False, "error": str(exc)}
            context.setdefault("flow", {"available": False})

    # Soft fit score from primary structure / ADX / squeeze so the model has a bias hint
    # without desk chop / confluence hard Neutral.
    fit = _strategy_fit(strategy.id, primary if isinstance(primary, dict) else {})
    context["strategy_fit"] = fit
    context["setup"] = {
        "type": strategy.id,
        "trade_allowed": fit.get("trade_allowed", True),
        "prefer_bias": fit.get("bias", "Neutral"),
        "summary": fit.get("summary", strategy.summary),
    }
    context["confluence"] = {
        "score": fit.get("score", 0),
        "bias": fit.get("bias", "Neutral"),
        "confidence": fit.get("confidence"),
        "summary": fit.get("summary"),
        "guardrail": "strategy_pack",
    }

    if isinstance(primary, dict):
        px = (primary.get("price_data") or {}).get("current_price")
        if px:
            context["yahoo_price"] = {"price": px, "source": "binance_local"}

    return context


def _strategy_fit(strategy_id: str, primary: dict[str, Any]) -> dict[str, Any]:
    """Lightweight bias hint for named strategies (not the desk confluence engine)."""
    struct = primary.get("structure") if isinstance(primary.get("structure"), dict) else {}
    adx = primary.get("adx") if isinstance(primary.get("adx"), dict) else {}
    squeeze = primary.get("squeeze") if isinstance(primary.get("squeeze"), dict) else {}
    rvol = primary.get("relative_volume")
    bias = struct.get("bias") or "Neutral"
    score = 0.0
    if bias == "Bullish":
        score += 2.5
    elif bias == "Bearish":
        score -= 2.5
    if struct.get("bos"):
        score += 1.5 if struct.get("bos") == "bullish" else -1.5
    if struct.get("choch"):
        score += 1.0 if struct.get("choch") == "bullish" else -1.0
    adx_val = adx.get("value")
    if isinstance(adx_val, (int, float)) and adx_val >= 20:
        score *= 1.15
    if strategy_id == "ema_volatility" and squeeze.get("active"):
        score *= 0.5  # wait for expansion
    if strategy_id == "breakout" and isinstance(rvol, (int, float)) and rvol < 1.0:
        score *= 0.6
    score = round(max(-8.0, min(8.0, score)), 2)
    out_bias = "Neutral"
    if score >= 2.5:
        out_bias = "Buy"
    elif score <= -2.5:
        out_bias = "Sell"
    trade_allowed = abs(score) >= 2.0
    return {
        "score": score,
        "bias": out_bias,
        "confidence": round(min(0.85, 0.35 + abs(score) / 12), 2),
        "trade_allowed": trade_allowed,
        "summary": (
            f"{strategy_id} fit {score:+.1f}; structure={struct.get('note') or bias}; "
            f"trade_ok={trade_allowed}"
        ),
    }


def fetch_coin_context(
    symbol: str,
    exchange: str,
    timeframe: str,
    settings: Settings,
    strategy_id: str | None = None,
) -> dict[str, Any]:
    """Aggregate single-coin TA; fall back to Binance klines when TV cliffs."""
    pair = normalize_pair(symbol)
    exchange = exchange.upper()
    strategy = get_strategy(strategy_id)
    if not strategy.uses_desk_pipeline:
        return _build_named_strategy_pack(pair, exchange, timeframe, settings, strategy.id)

    tf = normalize_timeframe(timeframe)
    context: dict[str, Any] = {
        "symbol": pair,
        "exchange": exchange,
        "timeframe": tf,
        "tv_symbol": tv_symbol(symbol, exchange),
        "yahoo_symbol": yahoo_symbol(pair),
    }
    _attach_strategy_meta(
        context,
        strategy_id=strategy.id,
        primary_tf=tf,
        context_tfs=[],
        overridden=False,
        desk_tf=timeframe,
    )

    coin: dict[str, Any] | None = None
    tv_ok = False

    try:
        from tradingview_mcp.core.services import screener_service

        analyze = getattr(screener_service, "analyze_coin", None)
        if analyze:
            coin = _to_dict(_safe_call(analyze, pair, exchange, tf))
            tv_ok = coin_analysis_usable(coin)
    except Exception as exc:  # noqa: BLE001
        logger.warning("TradingView analyze unavailable: %s", exc)
        coin = {"error": str(exc), "ok": False}

    risk = strategy.risk
    if not tv_ok:
        logger.info("Using Binance local TA fallback for %s %s", pair, tf)
        try:
            local = compute_local_analysis(
                pair,
                tf,
                stop_atr_min=risk.stop_atr_min,
                stop_atr_max=risk.stop_atr_max,
                target_r_min=risk.target_r_min,
            )
            # Keep TV error note but prefer local indicators
            if isinstance(coin, dict) and coin.get("error"):
                local["tv_error"] = coin.get("error")
            coin = local
            context["data_source"] = "binance_local"
        except Exception as exc:  # noqa: BLE001
            logger.exception("Binance fallback failed")
            context["data_source"] = "failed"
            coin = coin or {"error": str(exc), "ok": False}
    else:
        context["data_source"] = "tradingview"
        # Still enrich with local MACD/Stoch/RVOL when TV snapshot is thin
        try:
            local = compute_local_analysis(
                pair,
                tf,
                stop_atr_min=risk.stop_atr_min,
                stop_atr_max=risk.stop_atr_max,
                target_r_min=risk.target_r_min,
            )
            if isinstance(coin, dict):
                for key in (
                    "macd",
                    "stochastic",
                    "relative_volume",
                    "atr",
                    "ema",
                    "adx",
                    "bollinger",
                    "vwap",
                    "pivots",
                ):
                    if not coin.get(key) and local.get(key) is not None:
                        coin[key] = local[key]
                if not coin.get("support_resistance") and local.get("support_resistance"):
                    coin["support_resistance"] = local["support_resistance"]
                if not coin.get("suggested_levels") and local.get("suggested_levels"):
                    coin["suggested_levels"] = local["suggested_levels"]
                if not coin.get("market_structure") and local.get("market_structure"):
                    coin["market_structure"] = local["market_structure"]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Local enrich skipped: %s", exc)

    context["coin_analysis"] = _apply_risk_to_coin(coin, strategy) or coin

    # Skip MTF when TV is already cliffing — it burns retries and empties the snapshot
    if tv_ok:
        try:
            from tradingview_mcp.core.services import screener_service

            mtf = getattr(screener_service, "run_multi_timeframe_analysis", None)
            if mtf:
                qualified = f"{exchange}:{pair}"
                context["multi_timeframe"] = _to_dict(_safe_call(mtf, qualified, exchange))
        except Exception as exc:  # noqa: BLE001
            context["multi_timeframe"] = {"error": str(exc)}
    else:
        # Lightweight local bias from same TF only
        sug = (coin or {}).get("suggested_levels") if isinstance(coin, dict) else None
        context["multi_timeframe"] = {
            "analysis_type": "Local single-TF (TV MTF skipped — upstream rate limit)",
            "alignment": {
                "status": (coin or {}).get("market_structure", {}).get("trend", "MIXED")
                if isinstance(coin, dict)
                else "MIXED",
                "confidence": "Medium" if tv_ok else "Local",
            },
            "recommendation": {
                "action": f"Use local {tf} plan"
                + (f" bias_hint={(sug or {}).get('bias_hint')}" if sug else "")
            },
        }

    try:
        from tradingview_mcp.core.services import yahoo_finance_service

        get_price = getattr(yahoo_finance_service, "get_price", None)
        if get_price:
            context["yahoo_price"] = _to_dict(_safe_call(get_price, yahoo_symbol(pair)))
    except Exception as exc:  # noqa: BLE001
        context["yahoo_price"] = {"error": str(exc)}

    # Ensure price present even if Yahoo fails
    if isinstance(coin, dict):
        px = (coin.get("price_data") or {}).get("current_price")
        if px and not (context.get("yahoo_price") or {}).get("price"):
            context["yahoo_price"] = {"price": px, "source": context.get("data_source")}

    # Whale / positioning / funding / OI (Binance futures public)
    try:
        from .flow import fetch_flow_snapshot

        context["flow"] = fetch_flow_snapshot(pair, tf)
    except Exception as exc:  # noqa: BLE001
        context["flow"] = {"available": False, "error": str(exc)}

    # Order-book imbalance (spot/futures depth)
    try:
        from .orderbook import fetch_orderbook_imbalance

        context["orderbook"] = fetch_orderbook_imbalance(pair)
    except Exception as exc:  # noqa: BLE001
        context["orderbook"] = {"available": False, "error": str(exc)}

    # Liquidity map — long cascade vs short squeeze magnets
    try:
        from .liquidity import fetch_liquidity_map

        flow = context.get("flow") if isinstance(context.get("flow"), dict) else {}
        book = context.get("orderbook") if isinstance(context.get("orderbook"), dict) else {}
        context["liquidity"] = fetch_liquidity_map(
            pair,
            mark_price=flow.get("mark_price"),
            open_interest=flow.get("open_interest"),
            whale_long_pct=flow.get("whale_long_pct"),
            retail_long_pct=flow.get("retail_long_pct"),
            funding_rate=flow.get("funding_rate"),
            oi_change_pct=flow.get("oi_change_pct"),
            price_change_24h_pct=flow.get("price_change_24h_pct"),
            orderbook=book,
            coinglass_api_key=getattr(settings, "coinglass_api_key", None),
        )
    except Exception as exc:  # noqa: BLE001
        context["liquidity"] = {"available": False, "error": str(exc)}

    # Local MTF + BTC/ETH regime + confluence + setup classifier
    try:
        from .confluence import build_mtf_pack, build_regime, compute_confluence
        from .setup_classifier import apply_setup_to_confluence, classify_setup

        mtf_local = build_mtf_pack(pair)
        regime = build_regime(pair)
        flow = context.get("flow") if isinstance(context.get("flow"), dict) else None
        book = context.get("orderbook") if isinstance(context.get("orderbook"), dict) else None
        liq = context.get("liquidity") if isinstance(context.get("liquidity"), dict) else None
        context["mtf_local"] = mtf_local
        context["regime"] = regime
        conf = compute_confluence(
            coin if isinstance(coin, dict) else None,
            mtf_local,
            flow,
            regime,
            book,
            liq,
        )
        setup = classify_setup(
            coin if isinstance(coin, dict) else None,
            mtf_local,
            flow,
        )
        context["setup"] = setup
        context["confluence"] = apply_setup_to_confluence(conf, setup)
    except Exception as exc:  # noqa: BLE001
        logger.warning("confluence pack failed: %s", exc)
        context["confluence"] = {"error": str(exc), "bias": "Neutral", "score": 0}

    # High-impact macro events in the next 24 hours, from the stored calendar (WL-039)
    try:
        from .calendar_feed import upcoming_high_impact

        context["upcoming_events"] = upcoming_high_impact()
    except Exception as exc:  # noqa: BLE001
        logger.warning("calendar read failed: %s", exc)
        context["upcoming_events"] = []

    # Correlation and beta to BTC and ETH (WL-036); the original symbol keeps a .P suffix
    try:
        from .correlation import compute_correlation

        context["correlation"] = compute_correlation(symbol)
    except Exception as exc:  # noqa: BLE001
        logger.warning("correlation failed: %s", exc)
        context["correlation"] = {"available": False, "error": str(exc)}

    return context


async def fetch_coin_context_async(
    symbol: str,
    exchange: str,
    timeframe: str,
    settings: Settings,
    strategy_id: str | None = None,
) -> dict[str, Any]:
    return await asyncio.to_thread(
        fetch_coin_context, symbol, exchange, timeframe, settings, strategy_id
    )


def condense_market_context(context: dict[str, Any]) -> dict[str, Any]:
    """Compact snapshot for the LLM."""
    coin = context.get("coin_analysis") or {}
    if not isinstance(coin, dict):
        coin = {}
    mtf = context.get("multi_timeframe") or {}
    if not isinstance(mtf, dict):
        mtf = {}
    yahoo = context.get("yahoo_price") or {}
    if not isinstance(yahoo, dict):
        yahoo = {}

    price = coin.get("price_data") or {}
    rsi = coin.get("rsi") or {}
    macd = coin.get("macd") or {}
    ema = coin.get("ema") or {}
    sma = coin.get("sma") or {}
    bb = coin.get("bollinger_bands") or {}
    atr = coin.get("atr") or {}
    structure = coin.get("market_structure") or {}
    sentiment = coin.get("market_sentiment") or {}
    sr = coin.get("support_resistance") or {}
    sug = coin.get("suggested_levels") or {}
    stoch = coin.get("stochastic") or {}
    alignment = mtf.get("alignment") or {}
    recommendation = mtf.get("recommendation") or {}
    flow = context.get("flow") or {}
    if not isinstance(flow, dict):
        flow = {}

    return {
        "pair": context.get("tv_symbol"),
        "timeframe": context.get("timeframe"),
        "data_source": context.get("data_source"),
        "price": price.get("current_price") or yahoo.get("price"),
        "change_percent": price.get("change_percent") or yahoo.get("change_pct"),
        "rsi": rsi.get("value"),
        "rsi_signal": rsi.get("signal"),
        "macd_crossover": macd.get("crossover"),
        "macd_histogram": macd.get("histogram"),
        "stoch_k": stoch.get("k"),
        "stoch_signal": stoch.get("signal"),
        "relative_volume": coin.get("relative_volume"),
        "ema20": ema.get("ema20"),
        "ema50": ema.get("ema50"),
        "ema200": ema.get("ema200"),
        "sma50": sma.get("sma50"),
        "sma200": sma.get("sma200"),
        "bb_position": bb.get("position"),
        # Repeated key merged: the bollinger value used to win, the first position stays.
        "bb_squeeze": (coin.get("bollinger") or {}).get("squeeze")
        if coin.get("bollinger")
        else bb.get("squeeze"),
        "atr": atr.get("value"),
        "atr_pct": atr.get("percent_of_price"),
        "trend": structure.get("trend"),
        "trend_strength": structure.get("trend_strength"),
        "buy_sell_signal": sentiment.get("buy_sell_signal"),
        "nearest_support": sr.get("nearest_support") or sug.get("support"),
        "nearest_resistance": sr.get("nearest_resistance") or sug.get("resistance"),
        "support_2": sr.get("support_2") or sug.get("support_2"),
        "resistance_2": sr.get("resistance_2") or sug.get("resistance_2"),
        "trend_line": structure.get("trend_line") or sug.get("trend_line"),
        "level_hints": sug or None,
        "mtf_alignment": alignment.get("status"),
        "mtf_confidence": alignment.get("confidence"),
        "mtf_action": recommendation.get("action")
        if isinstance(recommendation, dict)
        else recommendation,
        # Whale / derivatives positioning
        "adx": (coin.get("adx") or {}).get("value"),
        "adx_strength": (coin.get("adx") or {}).get("trend_strength"),
        "di_signal": (coin.get("adx") or {}).get("di_signal"),
        "bb_percent_b": (coin.get("bollinger") or {}).get("percent_b"),
        "vwap": (coin.get("vwap") or {}).get("value"),
        "vwap_side": (coin.get("vwap") or {}).get("side"),
        "pivots": coin.get("pivots"),
        "whales": {
            "available": flow.get("available"),
            "summary": flow.get("summary"),
            "whale_bias": flow.get("whale_bias"),
            "whale_long_pct": flow.get("whale_long_pct"),
            "whale_ls_ratio": flow.get("whale_long_short_ratio"),
            "retail_bias": flow.get("retail_bias"),
            "retail_long_pct": flow.get("retail_long_pct"),
            "divergence": flow.get("positioning_divergence"),
            "crowding": flow.get("crowding"),
            "funding_rate": flow.get("funding_rate"),
            "funding_bias": flow.get("funding_bias"),
            "basis_pct": flow.get("basis_pct"),
            "oi_price_signal": flow.get("oi_price_signal"),
            "open_interest": flow.get("open_interest"),
            "oi_change_pct": flow.get("oi_change_pct"),
            "taker_bias": flow.get("taker_bias"),
            "taker_buy_sell_ratio": flow.get("taker_buy_sell_ratio"),
            "price_change_24h_pct": flow.get("price_change_24h_pct"),
        }
        if flow.get("available")
        else {"available": False, "note": flow.get("note") or flow.get("error")},
        "mtf": {
            "alignment": (context.get("mtf_local") or {}).get("alignment"),
            "net_score": (context.get("mtf_local") or {}).get("net_score"),
            "summary": (context.get("mtf_local") or {}).get("summary"),
            "timeframes": {
                tf: {
                    "trend": (row or {}).get("trend"),
                    "score": (row or {}).get("score"),
                    "rsi": (row or {}).get("rsi"),
                    "macd": (row or {}).get("macd"),
                    "adx": (row or {}).get("adx"),
                }
                for tf, row in ((context.get("mtf_local") or {}).get("timeframes") or {}).items()
            },
        },
        "regime": {
            "available": (context.get("regime") or {}).get("available"),
            "summary": (context.get("regime") or {}).get("summary"),
            "risk_mode": (context.get("regime") or {}).get("risk_mode"),
            "btc_trend_1d": (context.get("regime") or {}).get("btc_trend_1d"),
            "pair_vs_btc": (context.get("regime") or {}).get("pair_vs_btc"),
            "volatility_regime": (context.get("regime") or {}).get("volatility_regime"),
        },
        "orderbook": {
            "available": (context.get("orderbook") or {}).get("available"),
            "summary": (context.get("orderbook") or {}).get("summary"),
            "bias": (context.get("orderbook") or {}).get("bias"),
            "imbalance": (context.get("orderbook") or {}).get("imbalance"),
            "spread_bps": (context.get("orderbook") or {}).get("spread_bps"),
        }
        if (context.get("orderbook") or {}).get("available")
        else {"available": False},
        "liquidity": {
            "available": (context.get("liquidity") or {}).get("available"),
            "bias": (context.get("liquidity") or {}).get("bias"),
            "summary": (context.get("liquidity") or {}).get("summary"),
            "points": (context.get("liquidity") or {}).get("points"),
            "long_share_pct": (context.get("liquidity") or {}).get("long_share_pct"),
            "short_share_pct": (context.get("liquidity") or {}).get("short_share_pct"),
            "nearest_long_liq": (context.get("liquidity") or {}).get("nearest_long_liq"),
            "nearest_short_liq": (context.get("liquidity") or {}).get("nearest_short_liq"),
            "cascade": {
                "long_cascade_trigger": ((context.get("liquidity") or {}).get("cascade") or {}).get(
                    "long_cascade_trigger"
                ),
                "short_squeeze_trigger": ((context.get("liquidity") or {}).get("cascade") or {}).get(
                    "short_squeeze_trigger"
                ),
            },
            "squeeze": (context.get("liquidity") or {}).get("squeeze"),
        }
        if (context.get("liquidity") or {}).get("available")
        else {"available": False},
        "setup": {
            "type": (context.get("setup") or {}).get("type"),
            "trade_allowed": (context.get("setup") or {}).get("trade_allowed"),
            "prefer_bias": (context.get("setup") or {}).get("prefer_bias"),
            "summary": (context.get("setup") or {}).get("summary"),
        },
        "confluence": context.get("confluence"),
        "strategy_id": context.get("strategy_id"),
        "strategy": context.get("strategy"),
        "strategy_tf": context.get("strategy_tf"),
        "strategy_rules": context.get("strategy_rules"),
        "strategy_risk": context.get("strategy_risk"),
        "strategy_fit": context.get("strategy_fit"),
        "strategy_pack": _condensed_strategy_pack(context.get("strategy_pack")),
        "upcoming_events": context.get("upcoming_events"),
        # After the decision fields; reordering in context_to_prompt_block keeps them first.
        "correlation": _condensed_correlation(context.get("correlation")),
    }


def _condensed_strategy_pack(pack: Any) -> dict[str, Any] | None:
    if not isinstance(pack, dict):
        return None
    frames = pack.get("timeframes") if isinstance(pack.get("timeframes"), dict) else {}
    slim: dict[str, Any] = {}
    for tf, block in frames.items():
        if not isinstance(block, dict):
            continue
        slim[tf] = {
            k: block.get(k)
            for k in (
                "price_data",
                "ema",
                "rsi",
                "atr",
                "adx",
                "bollinger",
                "vwap",
                "stochastic",
                "relative_volume",
                "swings",
                "equal_levels",
                "structure",
                "fibonacci",
                "squeeze",
                "suggested_levels",
                "support_resistance",
                "error",
            )
            if k in block
        }
    return {
        "id": pack.get("id"),
        "label": pack.get("label"),
        "indicators": pack.get("indicators"),
        "needed_tfs": pack.get("needed_tfs"),
        "timeframes": slim,
    }


def _condensed_correlation(corr: Any) -> dict[str, Any]:
    from .correlation import condensed

    return condensed(corr)


# Sections the guardrails depend on go first so trimming can never reach them.
_PROMPT_FIRST = (
    "pair",
    "timeframe",
    "price",
    "setup",
    "confluence",
    "strategy_id",
    "strategy_rules",
    "strategy_risk",
    "strategy_fit",
    "strategy_pack",
)
# Dropped whole, in this order, when the block is still over budget.
_PROMPT_DROP_ORDER = (
    "pivots",
    "level_hints",
    "sma50",
    "sma200",
    "macd_histogram",
    "trend_line",
    "regime",
    "correlation",
    "strategy_tf",
    "upcoming_events",
    "orderbook",
    # strategy_pack stays until late so multi-TF frames survive trimming
    "flow",
    "liquidity",
    "strategy_pack",
)
_TRUNC_MARKER = " …[truncated]"


def _prune(value: Any) -> Any:
    """Drop None / empty values recursively — they cost tokens and say nothing."""
    if isinstance(value, dict):
        out = {k: _prune(v) for k, v in value.items()}
        return {k: v for k, v in out.items() if v not in (None, "", [], {})}
    if isinstance(value, list):
        return [_prune(v) for v in value]
    return value


def context_to_prompt_block(context: dict[str, Any], max_chars: int = 8000) -> str:
    compact = condense_market_context(context)
    conf = compact.get("confluence")
    if isinstance(conf, dict):
        # apply_setup_to_confluence embeds the whole setup; it is already its own section
        compact["confluence"] = {k: v for k, v in conf.items() if k != "setup"}
    ordered = {k: compact[k] for k in _PROMPT_FIRST if k in compact}
    ordered.update({k: v for k, v in compact.items() if k not in ordered})
    ordered = _prune(ordered)

    def dump(obj: dict[str, Any]) -> str:
        return json.dumps(obj, separators=(",", ":"), default=str, ensure_ascii=False)

    blob = dump(ordered)
    for key in _PROMPT_DROP_ORDER:
        if len(blob) <= max_chars:
            break
        ordered.pop(key, None)
        blob = dump(ordered)
    if len(blob) > max_chars:
        # The marker counts against the budget, so the result never exceeds max_chars.
        marker = _TRUNC_MARKER
        blob = (blob[: max(0, max_chars - len(marker))] + marker)[:max_chars]
    return blob
