"""Run every strategy pack on one coin and pick a final plan (WL-054)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

from .ai import (
    build_analysis_prompt,
    extract_levels,
    format_clear_brief,
    generate_text,
)
from .config import Settings
from .market import context_to_prompt_block, fetch_coin_context_async
from .schemas import TradeLevels
from .strategies import get_strategy, list_strategies

logger = logging.getLogger(__name__)

OptimizeMode = Literal["local_score", "ai_ensemble", "majority_vote"]
OPTIMIZE_MODES: tuple[str, ...] = ("local_score", "ai_ensemble", "majority_vote")


def normalize_optimize_mode(raw: str | None) -> OptimizeMode:
    m = (raw or "local_score").strip().lower()
    if m in OPTIMIZE_MODES:
        return m  # type: ignore[return-value]
    return "local_score"


def catalog_strategy_ids() -> list[str]:
    return [s["id"] for s in list_strategies()]


def _fit_score(market: dict[str, Any]) -> float:
    fit = market.get("strategy_fit") if isinstance(market.get("strategy_fit"), dict) else {}
    conf = market.get("confluence") if isinstance(market.get("confluence"), dict) else {}
    if fit.get("score") is not None:
        return float(fit["score"])
    if conf.get("score") is not None:
        return float(conf["score"])
    return 0.0


def _trade_allowed(market: dict[str, Any]) -> bool:
    fit = market.get("strategy_fit") if isinstance(market.get("strategy_fit"), dict) else {}
    setup = market.get("setup") if isinstance(market.get("setup"), dict) else {}
    if "trade_allowed" in fit:
        return bool(fit.get("trade_allowed"))
    if "trade_allowed" in setup:
        return bool(setup.get("trade_allowed"))
    return True


def _prefer_bias(market: dict[str, Any]) -> str:
    fit = market.get("strategy_fit") if isinstance(market.get("strategy_fit"), dict) else {}
    conf = market.get("confluence") if isinstance(market.get("confluence"), dict) else {}
    sug = ((market.get("coin_analysis") or {}).get("suggested_levels") or {}) if isinstance(
        market.get("coin_analysis"), dict
    ) else {}
    for src in (fit.get("bias"), conf.get("bias"), sug.get("bias_hint")):
        if src in ("Buy", "Sell", "Neutral"):
            return str(src)
    return "Neutral"


def levels_from_market(market: dict[str, Any]) -> TradeLevels:
    """Deterministic plan from suggested levels + fit/confluence (local_score packs)."""
    coin = market.get("coin_analysis") if isinstance(market.get("coin_analysis"), dict) else {}
    sug = coin.get("suggested_levels") if isinstance(coin.get("suggested_levels"), dict) else {}
    bias = _prefer_bias(market)
    if not _trade_allowed(market):
        bias = "Neutral"
    conf = market.get("confluence") if isinstance(market.get("confluence"), dict) else {}
    fit = market.get("strategy_fit") if isinstance(market.get("strategy_fit"), dict) else {}
    confidence = fit.get("confidence")
    if confidence is None:
        confidence = conf.get("confidence")
    reason = fit.get("summary") or conf.get("summary") or "local pack levels"
    return TradeLevels(
        bias=bias,  # type: ignore[arg-type]
        entry=sug.get("entry"),
        stop_loss=sug.get("stop_loss"),
        take_profit=sug.get("take_profit"),
        support=sug.get("support"),
        resistance=sug.get("resistance"),
        support_2=sug.get("support_2"),
        resistance_2=sug.get("resistance_2"),
        trend=sug.get("trend"),
        trend_line=sug.get("trend_line"),
        ema20=sug.get("ema20"),
        ema50=sug.get("ema50"),
        confidence=float(confidence) if confidence is not None else None,
        reasoning=str(reason)[:400],
    )


def _reward_risk(levels: TradeLevels) -> float:
    if levels.entry is None or levels.stop_loss is None or levels.take_profit is None:
        return 0.0
    risk = abs(levels.entry - levels.stop_loss)
    if risk <= 0:
        return 0.0
    return abs(levels.take_profit - levels.entry) / risk


def pack_score(levels: TradeLevels, market: dict[str, Any]) -> float:
    """Higher is better. Neutrals score very low."""
    if levels.bias not in ("Buy", "Sell"):
        return -100.0
    fit = abs(_fit_score(market))
    rr = _reward_risk(levels)
    conf = float(levels.confidence or 0)
    allowed = 1.0 if _trade_allowed(market) else -5.0
    # Prefer bias aligned with fit sign
    fs = _fit_score(market)
    align = 0.0
    if levels.bias == "Buy" and fs > 0:
        align = 1.0
    elif levels.bias == "Sell" and fs < 0:
        align = 1.0
    elif abs(fs) < 0.5:
        align = 0.25
    return fit + rr + conf * 2.0 + allowed + align


def pack_public(
    *,
    strategy_id: str,
    strategy_label: str,
    timeframe: str,
    levels: TradeLevels,
    market: dict[str, Any],
    analysis: str,
    score: float,
) -> dict[str, Any]:
    return {
        "strategy_id": strategy_id,
        "strategy_label": strategy_label,
        "timeframe": timeframe,
        "bias": levels.bias,
        "entry": levels.entry,
        "stop_loss": levels.stop_loss,
        "take_profit": levels.take_profit,
        "confidence": levels.confidence,
        "reasoning": levels.reasoning,
        "fit_score": _fit_score(market),
        "trade_allowed": _trade_allowed(market),
        "pack_score": round(score, 3),
        "analysis": (analysis or "")[:1200],
    }


def pick_local_score(packs: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    ranked = sorted(packs, key=lambda p: float(p.get("pack_score") or -999), reverse=True)
    if not ranked:
        return None, "no packs"
    best = ranked[0]
    if best.get("bias") not in ("Buy", "Sell"):
        # Fall back to first directional if any
        for p in ranked:
            if p.get("bias") in ("Buy", "Sell"):
                return p, f"local_score: best directional {p['strategy_id']} (score {p['pack_score']})"
        return best, "local_score: all Neutral; kept top pack"
    return best, f"local_score: {best['strategy_id']} score {best['pack_score']}"


def pick_majority_vote(packs: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    votes: dict[str, int] = {"Buy": 0, "Sell": 0, "Neutral": 0}
    for p in packs:
        b = p.get("bias") or "Neutral"
        if b not in votes:
            b = "Neutral"
        votes[b] += 1
    # Prefer directional majority; Neutral wins only if it strictly leads
    side = max(("Buy", "Sell", "Neutral"), key=lambda k: (votes[k], 1 if k != "Neutral" else 0))
    if votes["Buy"] == votes["Sell"] and votes["Buy"] > 0 and votes["Buy"] >= votes["Neutral"]:
        # Tie Buy/Sell: highest pack_score among directional
        directional = [p for p in packs if p.get("bias") in ("Buy", "Sell")]
        if directional:
            best = max(directional, key=lambda p: float(p.get("pack_score") or -999))
            return best, (
                f"majority_vote: Buy/Sell tie ({votes['Buy']}-{votes['Sell']}); "
                f"highest score {best['strategy_id']}"
            )
    agreeing = [p for p in packs if (p.get("bias") or "Neutral") == side]
    if not agreeing:
        return pick_local_score(packs)[0], "majority_vote: empty; fell back to local_score"
    best = max(agreeing, key=lambda p: float(p.get("pack_score") or -999))
    return best, (
        f"majority_vote: {side} ({votes['Buy']}B/{votes['Sell']}S/{votes['Neutral']}N); "
        f"levels from {best['strategy_id']}"
    )


async def _analyze_pack_ai(
    *,
    pair: str,
    exchange: str,
    desk_tf: str,
    settings: Settings,
    strategy_id: str,
    custom_prompt: str | None,
    fill_levels,
    apply_confluence,
    apply_rr,
) -> tuple[TradeLevels, dict[str, Any], str, str]:
    strategy = get_strategy(strategy_id)
    market = await fetch_coin_context_async(pair, exchange, desk_tf, settings, strategy.id)
    effective_tf = str(market.get("timeframe") or desk_tf)
    risk = strategy.risk
    prompt = build_analysis_prompt(
        pair,
        exchange.upper(),
        effective_tf,
        context_to_prompt_block(market),
        custom_prompt,
        strategy_id=strategy.id,
        strategy_label=strategy.label,
        strategy_rules=strategy.prompt_rules or None,
        uses_desk_pipeline=strategy.uses_desk_pipeline,
        stop_atr_min=risk.stop_atr_min,
        stop_atr_max=risk.stop_atr_max,
        min_reward_risk=risk.min_reward_risk,
    )
    text, provider = await generate_text(prompt, settings)
    levels = extract_levels(text)
    levels = fill_levels(levels, market)
    if strategy.uses_desk_pipeline:
        levels = apply_confluence(levels, market)
    levels = apply_rr(levels)
    analysis = format_clear_brief(pair, exchange.upper(), effective_tf, levels, text)
    market = {**market, "timeframe": effective_tf}
    return levels, market, analysis, provider


async def _analyze_pack_local(
    *,
    pair: str,
    exchange: str,
    desk_tf: str,
    settings: Settings,
    strategy_id: str,
    fill_levels,
    apply_confluence,
    apply_rr,
) -> tuple[TradeLevels, dict[str, Any], str, str]:
    strategy = get_strategy(strategy_id)
    market = await fetch_coin_context_async(pair, exchange, desk_tf, settings, strategy.id)
    effective_tf = str(market.get("timeframe") or desk_tf)
    levels = levels_from_market(market)
    levels = fill_levels(levels, market)
    if strategy.uses_desk_pipeline:
        levels = apply_confluence(levels, market)
    levels = apply_rr(levels)
    analysis = (
        f"LOCAL PACK {strategy.label}: bias {levels.bias}; "
        f"fit {_fit_score(market):+.1f}; R:R {_reward_risk(levels):.2f}"
    )
    market = {**market, "timeframe": effective_tf}
    return levels, market, analysis, "local_score"


async def run_multi_analyze(
    *,
    pair: str,
    exchange: str,
    desk_tf: str,
    settings: Settings,
    optimize_mode: OptimizeMode,
    custom_prompt: str | None,
    fill_levels,
    apply_confluence,
    apply_rr,
) -> dict[str, Any]:
    """Return final levels, packs, winner market, analysis text, provider meta."""
    ids = catalog_strategy_ids()
    use_ai = optimize_mode == "ai_ensemble"
    # majority_vote and local_score use local packs (cheap); ensemble uses AI per pack.

    async def one(sid: str) -> dict[str, Any]:
        strategy = get_strategy(sid)
        if use_ai:
            levels, market, analysis, provider = await _analyze_pack_ai(
                pair=pair,
                exchange=exchange,
                desk_tf=desk_tf,
                settings=settings,
                strategy_id=sid,
                custom_prompt=custom_prompt,
                fill_levels=fill_levels,
                apply_confluence=apply_confluence,
                apply_rr=apply_rr,
            )
        else:
            levels, market, analysis, provider = await _analyze_pack_local(
                pair=pair,
                exchange=exchange,
                desk_tf=desk_tf,
                settings=settings,
                strategy_id=sid,
                fill_levels=fill_levels,
                apply_confluence=apply_confluence,
                apply_rr=apply_rr,
            )
        score = pack_score(levels, market)
        pub = pack_public(
            strategy_id=strategy.id,
            strategy_label=strategy.label,
            timeframe=str(market.get("timeframe") or desk_tf),
            levels=levels,
            market=market,
            analysis=analysis,
            score=score,
        )
        return {
            "public": pub,
            "levels": levels,
            "market": market,
            "analysis": analysis,
            "provider": provider,
        }

    # Parallel market/AI work (gather). AI ensemble may hit rate limits; still gather.
    raw = await asyncio.gather(*[one(sid) for sid in ids], return_exceptions=True)
    results: list[dict[str, Any]] = []
    for sid, item in zip(ids, raw, strict=True):
        if isinstance(item, Exception):
            logger.warning("pack %s failed: %s", sid, item)
            strategy = get_strategy(sid)
            results.append(
                {
                    "public": {
                        "strategy_id": strategy.id,
                        "strategy_label": strategy.label,
                        "timeframe": desk_tf,
                        "bias": "Neutral",
                        "entry": None,
                        "stop_loss": None,
                        "take_profit": None,
                        "confidence": None,
                        "reasoning": f"pack error: {item}",
                        "fit_score": 0.0,
                        "trade_allowed": False,
                        "pack_score": -100.0,
                        "analysis": "",
                        "error": str(item),
                    },
                    "levels": TradeLevels(bias="Neutral", reasoning=str(item)),
                    "market": {},
                    "analysis": "",
                    "provider": "error",
                }
            )
        else:
            results.append(item)

    packs = [r["public"] for r in results]
    by_id = {r["public"]["strategy_id"]: r for r in results}

    if optimize_mode == "majority_vote":
        winner_pub, reason = pick_majority_vote(packs)
    else:
        # local_score and default pick; ai_ensemble also starts from local_score then may synthesize
        winner_pub, reason = pick_local_score(packs)

    provider = "local_score"
    analysis = ""
    final_levels: TradeLevels
    final_market: dict[str, Any]
    final_sid = "desk"

    if optimize_mode == "ai_ensemble":
        provider = "ai_ensemble"
        # Synthesis: ask model to pick among packs
        summary_lines = []
        for p in packs:
            summary_lines.append(
                f"- {p['strategy_id']}: bias={p['bias']} entry={p['entry']} "
                f"sl={p['stop_loss']} tp={p['take_profit']} fit={p['fit_score']} "
                f"score={p['pack_score']} | {(p.get('reasoning') or '')[:120]}"
            )
        syn_prompt = (
            f"Multi-strategy synthesis for {exchange}:{pair}. "
            f"Desk TF {desk_tf}. Pick ONE best strategy_id from the list and give "
            f"Buy|Sell|Neutral with entry, stop_loss, take_profit JSON.\n"
            f"Packs:\n" + "\n".join(summary_lines) + "\n"
            "Reply briefly then JSON fence with bias, entry, stop_loss, take_profit, "
            "confidence, reasoning, and strategy_id of the winner."
        )
        try:
            text, provider = await generate_text(syn_prompt, settings)
            syn_levels = extract_levels(text)
            # Prefer explicit strategy_id in JSON if present
            import json
            import re

            m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
            picked_sid = None
            if m:
                try:
                    data = json.loads(m.group(1))
                    picked_sid = (data.get("strategy_id") or "").strip().lower() or None
                except Exception:  # noqa: BLE001
                    picked_sid = None
            if picked_sid and picked_sid in by_id:
                base = by_id[picked_sid]
                final_levels = fill_levels(syn_levels, base["market"]) if base["market"] else syn_levels
                if not final_levels.entry:
                    final_levels = base["levels"]
                final_market = base["market"] or {}
                final_sid = picked_sid
                reason = f"ai_ensemble: model picked {picked_sid}"
            elif winner_pub and winner_pub["strategy_id"] in by_id:
                base = by_id[winner_pub["strategy_id"]]
                final_levels = fill_levels(syn_levels, base["market"]) if base["market"] else syn_levels
                if final_levels.bias == "Neutral" and base["levels"].bias in ("Buy", "Sell"):
                    final_levels = base["levels"]
                final_market = base["market"] or {}
                final_sid = winner_pub["strategy_id"]
                reason = f"ai_ensemble: synthesis with fallback pack {final_sid}"
            else:
                final_levels = syn_levels
                final_market = {}
                final_sid = "desk"
                reason = "ai_ensemble: synthesis only"
            final_levels = apply_rr(final_levels)
            analysis = format_clear_brief(
                pair, exchange.upper(), str(final_market.get("timeframe") or desk_tf), final_levels, text
            )
            analysis = f"OPTIMIZE: {reason}\n\n{analysis}"
        except Exception as exc:  # noqa: BLE001
            logger.warning("ai_ensemble synthesis failed: %s", exc)
            if not winner_pub:
                raise
            base = by_id[winner_pub["strategy_id"]]
            final_levels = base["levels"]
            final_market = base["market"]
            final_sid = winner_pub["strategy_id"]
            provider = base["provider"]
            analysis = f"OPTIMIZE: ai_ensemble failed ({exc}); used {final_sid}\n\n{base['analysis']}"
            reason = f"ai_ensemble fallback: {final_sid}"
    else:
        if not winner_pub:
            final_levels = TradeLevels(bias="Neutral", reasoning="no packs")
            final_market = {}
            final_sid = "desk"
            analysis = "No strategy packs produced a plan."
            provider = "local_score"
        else:
            base = by_id[winner_pub["strategy_id"]]
            final_levels = base["levels"]
            final_market = base["market"]
            final_sid = winner_pub["strategy_id"]
            provider = base["provider"]
            analysis = f"OPTIMIZE: {reason}\n\n{base['analysis']}"
            # Optional short AI brief on winner for local_score only (skip if offline)
            from .config import resolve_provider

            if optimize_mode == "local_score" and resolve_provider(settings) != "none":
                try:
                    brief_prompt = (
                        f"One short paragraph on why {final_sid} is the best pack for "
                        f"{exchange}:{pair} given bias {final_levels.bias}. No JSON."
                    )
                    brief, provider = await generate_text(brief_prompt, settings)
                    analysis = f"OPTIMIZE: {reason}\n\n{brief.strip()}\n\n{base['analysis']}"
                except Exception as exc:  # noqa: BLE001
                    logger.debug("winner brief skipped: %s", exc)

    strategy = get_strategy(final_sid)
    multi = {
        "optimize_mode": optimize_mode,
        "reason": reason,
        "final_strategy_id": final_sid,
        "packs": packs,
    }
    return {
        "levels": final_levels,
        "market": final_market,
        "analysis": analysis,
        "provider": provider,
        "strategy_id": final_sid,
        "strategy_label": strategy.label,
        "timeframe": str(final_market.get("timeframe") or desk_tf),
        "optimize_mode": optimize_mode,
        "packs": packs,
        "multi_analysis": multi,
        "reason": reason,
    }
