"""FastAPI entry — analyze + chat endpoints for Crypto Chart AI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .ai import (
    build_analysis_prompt,
    build_chat_prompt,
    extract_levels,
    format_clear_brief,
    generate_text,
    strip_json_fence,
)
from .config import get_settings, provider_model, resolve_provider
from .db import init_db
from .market import (
    context_to_prompt_block,
    fetch_coin_context_async,
    normalize_pair,
    tv_symbol,
)
from .schemas import (
    AnalyzeRequest,
    CalendarResponse,
    AnalyzeResponse,
    ChatRequest,
    ChatResponse,
    CorrelationResponse,
    HealthResponse,
    JobsResponse,
    JournalClose,
    JournalCreate,
    PulseResponse,
    StrategiesResponse,
    TradeLevels,
    WatchlistRequest,
)
from .strategies import get_strategy


def _apply_confluence_guardrail(levels: TradeLevels, market: dict) -> TradeLevels:
    """Keep AI bias aligned with deterministic confluence score."""
    conf = market.get("confluence") if isinstance(market, dict) else None
    setup = market.get("setup") if isinstance(market, dict) else None
    if not isinstance(conf, dict) or conf.get("bias") not in ("Buy", "Sell", "Neutral"):
        return levels
    preferred = conf["bias"]
    score = float(conf.get("score") or 0)
    bias = levels.bias
    # Chop / no-trade setup → force Neutral
    if isinstance(setup, dict) and setup.get("trade_allowed") is False:
        bias = "Neutral"
    # Soft zone → force Neutral
    elif abs(score) < 2.5:
        bias = "Neutral"
    # Never allow opposite of strong confluence
    elif preferred == "Buy" and bias == "Sell":
        bias = "Buy"
    elif preferred == "Sell" and bias == "Buy":
        bias = "Sell"
    elif preferred != "Neutral" and bias == "Neutral" and abs(score) >= 3.5:
        bias = preferred

    conf_val = levels.confidence
    if conf.get("confidence") is not None:
        # blend
        c2 = float(conf["confidence"])
        conf_val = c2 if conf_val is None else round((conf_val + c2) / 2, 2)
    if isinstance(setup, dict) and setup.get("trade_allowed") is False:
        # A missing confidence defaults to the cap; a real 0.0 stays 0.0 (WL-026).
        conf_val = 0.4 if conf_val is None else min(conf_val, 0.4)

    reason = levels.reasoning or ""
    guard = conf.get("summary") or conf.get("guardrail") or ""
    if isinstance(setup, dict) and setup.get("summary"):
        guard = f"{setup['summary']} | {guard}".strip(" |")
    if guard and guard not in reason:
        reason = f"{reason} | {guard}".strip(" |")

    return levels.model_copy(
        update={"bias": bias, "confidence": conf_val, "reasoning": reason}
    )


MIN_REWARD_RISK = 1.0


def _apply_reward_risk_guard(levels: TradeLevels) -> TradeLevels:
    """A directional plan must have levels on the right sides and pay at least 1:1."""
    if levels.bias not in ("Buy", "Sell"):
        return levels
    entry, stop, target = levels.entry, levels.stop_loss, levels.take_profit
    if entry is None or stop is None or target is None:
        return levels

    if levels.bias == "Buy":
        wrong_side = not (stop < entry < target)
    else:
        wrong_side = not (target < entry < stop)
    risk = abs(entry - stop)
    reward_risk = abs(target - entry) / risk if risk else 0.0

    if wrong_side:
        note = "Levels on the wrong side of entry → Neutral"
    elif reward_risk < MIN_REWARD_RISK:
        note = f"R:R {reward_risk:.2f} below {MIN_REWARD_RISK:.0f}:1 → Neutral"
    else:
        return levels
    reason = f"{levels.reasoning} | {note}".strip(" |")
    return levels.model_copy(update={"bias": "Neutral", "reasoning": reason})


def _fill_levels_from_market(levels: TradeLevels, market: dict) -> TradeLevels:
    """Fill blank trade/structure levels from market snapshot."""
    coin = market.get("coin_analysis") if isinstance(market, dict) else None
    if not isinstance(coin, dict):
        return levels
    sug = coin.get("suggested_levels") if isinstance(coin.get("suggested_levels"), dict) else {}
    sr = coin.get("support_resistance") if isinstance(coin.get("support_resistance"), dict) else {}
    structure = coin.get("market_structure") if isinstance(coin.get("market_structure"), dict) else {}
    ema = coin.get("ema") if isinstance(coin.get("ema"), dict) else {}

    def pick(*vals):
        for v in vals:
            if v is not None:
                return v
        return None

    return TradeLevels(
        bias=levels.bias,
        entry=pick(levels.entry, sug.get("entry")),
        stop_loss=pick(levels.stop_loss, sug.get("stop_loss")),
        take_profit=pick(levels.take_profit, sug.get("take_profit")),
        support=pick(levels.support, sug.get("support"), sr.get("nearest_support")),
        resistance=pick(
            levels.resistance, sug.get("resistance"), sr.get("nearest_resistance")
        ),
        support_2=pick(levels.support_2, sug.get("support_2"), sr.get("support_2"), ema.get("ema50")),
        resistance_2=pick(
            levels.resistance_2, sug.get("resistance_2"), sr.get("resistance_2"), ema.get("ema20")
        ),
        trend=levels.trend or sug.get("trend") or structure.get("trend"),
        trend_line=levels.trend_line
        or sug.get("trend_line")
        or structure.get("trend_line"),
        ema20=pick(levels.ema20, sug.get("ema20"), ema.get("ema20")),
        ema50=pick(levels.ema50, sug.get("ema50"), ema.get("ema50")),
        confidence=levels.confidence if levels.confidence not in (None, 0) else 0.45,
        reasoning=levels.reasoning
        or f"Filled from local {market.get('data_source')} structure hints.",
    )

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
_boot = get_settings()


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    # Migrate the SQLite db and import any old journal.json / signals.json once.
    init_db()
    # First start: fill the instrument catalogue in a background thread (WL-044).
    from .instruments import refresh_in_background_if_empty

    refresh_in_background_if_empty()
    # Same for the calendar when nothing is stored from today onward (WL-039).
    from .calendar_feed import refresh_in_background_if_empty as calendar_if_empty

    calendar_if_empty()
    yield


app = FastAPI(title=_boot.app_name, version="0.1.0", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_boot.origins + ["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    tv_ready = False
    try:
        import tradingview_mcp  # noqa: F401

        tv_ready = True
    except ImportError:
        tv_ready = False
    provider = resolve_provider(settings)
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        ai_provider=provider,
        ai_model=provider_model(settings, provider),
        tradingview_ready=tv_ready,
    )


@app.get("/api/strategies", response_model=StrategiesResponse)
async def strategies_list() -> StrategiesResponse:
    from .strategies import list_strategies

    return StrategiesResponse(strategies=list_strategies(), default="desk")


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    settings = get_settings()
    pair = normalize_pair(req.symbol)
    if not pair:
        raise HTTPException(400, "Invalid symbol")

    # WL-054: all strategies + optimization
    if (req.strategy_id or "").strip().lower() == "all":
        from .multi_analyze import normalize_optimize_mode, run_multi_analyze

        mode = normalize_optimize_mode(req.optimize_mode)
        try:
            multi = await run_multi_analyze(
                pair=pair,
                exchange=req.exchange,
                desk_tf=req.timeframe,
                settings=settings,
                optimize_mode=mode,
                custom_prompt=req.custom_prompt,
                fill_levels=_fill_levels_from_market,
                apply_confluence=_apply_confluence_guardrail,
                apply_rr=_apply_reward_risk_guard,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("multi analyze failed")
            detail = str(exc).strip() or type(exc).__name__
            raise HTTPException(status_code=502, detail=f"AI error: {detail}") from exc

        levels: TradeLevels = multi["levels"]
        market = multi["market"] or {}
        analysis = multi["analysis"]
        provider = multi["provider"]
        effective_tf = str(multi.get("timeframe") or req.timeframe)
        final_sid = multi["strategy_id"]
        strategy_label = multi["strategy_label"]
        packs = multi.get("packs")
        multi_blob = multi.get("multi_analysis")

        logger.info(
            "analyze %s %s strategy=all mode=%s -> %s (%s)",
            pair,
            effective_tf,
            mode,
            levels.bias,
            final_sid,
        )

        # Archive directional multi plans (including local_score packs) so the
        # detail page keeps every pack's initial result in multi_analysis_json.
        archive_ok = (
            levels.bias in ("Buy", "Sell")
            and levels.entry is not None
            and levels.stop_loss is not None
            and levels.take_profit is not None
        )
        if archive_ok:
            try:
                from .signals import record_signal

                sig = record_signal(
                    symbol=pair,
                    timeframe=effective_tf,
                    levels=levels.model_dump(),
                    market=market,
                    strategy_id=final_sid,
                    multi_analysis=multi_blob,
                )
                if sig:
                    market = {**market, "recorded_signal_id": sig.get("id")}
            except Exception as exc:  # noqa: BLE001
                logger.warning("signal archive failed: %s", exc)

        return AnalyzeResponse(
            symbol=pair,
            exchange=req.exchange.upper(),
            timeframe=effective_tf,
            tv_symbol=tv_symbol(pair, req.exchange),
            strategy_id=final_sid,
            strategy_label=strategy_label,
            market=market,
            levels=levels,
            analysis=analysis,
            provider=provider,
            optimize_mode=mode,
            final_strategy_id=final_sid,
            packs=packs,
        )

    strategy = get_strategy(req.strategy_id)
    market = await fetch_coin_context_async(
        pair, req.exchange, req.timeframe, settings, strategy.id
    )
    # Effective TF may come from the strategy pack when desk TF was overridden.
    effective_tf = str(market.get("timeframe") or req.timeframe)
    risk = strategy.risk
    prompt = build_analysis_prompt(
        pair,
        req.exchange.upper(),
        effective_tf,
        context_to_prompt_block(market),
        req.custom_prompt,
        strategy_id=strategy.id,
        strategy_label=strategy.label,
        strategy_rules=strategy.prompt_rules or None,
        uses_desk_pipeline=strategy.uses_desk_pipeline,
        stop_atr_min=risk.stop_atr_min,
        stop_atr_max=risk.stop_atr_max,
        min_reward_risk=risk.min_reward_risk,
    )
    try:
        text, provider = await generate_text(prompt, settings)
    except Exception as exc:  # noqa: BLE001
        logger.exception("AI generate failed")
        detail = str(exc).strip() or f"{type(exc).__name__}"
        raise HTTPException(status_code=502, detail=f"AI error: {detail}") from exc
    levels = extract_levels(text)
    model_bias = levels.bias
    levels = _fill_levels_from_market(levels, market)
    # Snapshot for the signal archive before desk guards can force Neutral.
    levels_for_signal = levels.model_dump()
    # Desk pipeline only: confluence / chop guards decide the bias (decision 0003).
    if strategy.uses_desk_pipeline:
        levels = _apply_confluence_guardrail(levels, market)
    levels = _apply_reward_risk_guard(levels)
    analysis = format_clear_brief(
        pair, req.exchange.upper(), effective_tf, levels, text
    )
    if provider != "offline" and levels.bias != model_bias and strategy.uses_desk_pipeline:
        # The card below is the model's own; say why the plan's bias differs from it.
        conf = market.get("confluence") if isinstance(market.get("confluence"), dict) else {}
        analysis = (
            f"DESK OVERRIDE: the analyst said {model_bias}; the plan is {levels.bias} "
            f"(confluence {float(conf.get('score') or 0):+.1f}/10 and the R:R guard decide the bias).\n\n"
            + analysis
        )
    logger.info(
        "analyze %s %s strategy=%s via %s -> %s",
        pair,
        effective_tf,
        strategy.id,
        provider,
        levels.bias,
    )

    # Archive Buy/Sell plans for later TP/SL verification. Offline plans are
    # never archived — the track record is for calls an AI actually made.
    # Use the pre-guard bias so a desk Neutral override still leaves a trackable plan
    # when the model (or filled levels) had a real entry / stop / target.
    if provider != "offline":
        try:
            from .signals import record_signal

            archive = dict(levels_for_signal)
            if archive.get("bias") not in ("Buy", "Sell") and model_bias in ("Buy", "Sell"):
                archive["bias"] = model_bias
            if levels.bias == "Neutral" and archive.get("bias") in ("Buy", "Sell"):
                note = (archive.get("reasoning") or "").strip()
                override = f"Desk plan Neutral (guards); archived as {archive['bias']}"
                archive["reasoning"] = f"{note} | {override}".strip(" |")
            sig = record_signal(
                symbol=pair,
                timeframe=effective_tf,
                levels=archive,
                market=market,
                strategy_id=strategy.id,
            )
            if sig:
                market = {**market, "recorded_signal_id": sig.get("id")}
        except Exception as exc:  # noqa: BLE001
            logger.warning("signal archive failed: %s", exc)

    return AnalyzeResponse(
        symbol=pair,
        exchange=req.exchange.upper(),
        timeframe=effective_tf,
        tv_symbol=tv_symbol(pair, req.exchange),
        strategy_id=strategy.id,
        strategy_label=strategy.label,
        market=market,
        levels=levels,
        analysis=analysis,
        provider=provider,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    settings = get_settings()
    pair = normalize_pair(req.symbol)
    if not pair or not req.message.strip():
        raise HTTPException(400, "symbol and message are required")

    strategy = get_strategy(req.strategy_id)
    market = await fetch_coin_context_async(
        pair, req.exchange, req.timeframe, settings, strategy.id
    )
    effective_tf = str(market.get("timeframe") or req.timeframe)
    prompt = build_chat_prompt(
        pair,
        req.exchange.upper(),
        effective_tf,
        context_to_prompt_block(market),
        req.message.strip(),
        req.history,
        strategy_id=strategy.id,
        strategy_label=strategy.label,
    )
    try:
        text, provider = await generate_text(prompt, settings)
    except Exception as exc:  # noqa: BLE001
        logger.exception("AI generate failed")
        detail = str(exc).strip() or f"{type(exc).__name__}"
        raise HTTPException(status_code=502, detail=f"AI error: {detail}") from exc
    return ChatResponse(
        symbol=pair,
        reply=strip_json_fence(text),
        market_snapshot=None,
        provider=provider,
        strategy_id=strategy.id,
    )


@app.get("/api/market/{symbol}")
async def market_only(
    symbol: str,
    exchange: str = "BINANCE",
    timeframe: str = "1h",
):
    settings = get_settings()
    pair = normalize_pair(symbol)
    return await fetch_coin_context_async(pair, exchange, timeframe, settings)


@app.get("/api/correlation/{symbol}", response_model=CorrelationResponse)
def correlation(symbol: str) -> CorrelationResponse:
    """Correlation and beta to BTC and ETH, 30d of 1h and 90d of 1d (sync: runs in the threadpool)."""
    from .correlation import compute_correlation

    return CorrelationResponse(**compute_correlation(symbol))


@app.get("/api/pulse", response_model=PulseResponse)
async def pulse() -> PulseResponse:
    """BTC and ETH price, 24h change and a per-timeframe pulse; cached 20 s per cell."""
    from .pulse import build_pulse

    return PulseResponse(**await build_pulse())


@app.get("/api/symbols/search")
async def symbols_search(q: str = "", exchange: str = "BINANCE", limit: int = 25):
    from .symbols import search_symbols

    if not q.strip():
        return {"results": []}
    return {"results": search_symbols(q, exchange=exchange, limit=min(limit, 40))}


@app.post("/api/watchlist/score")
async def watchlist_score(req: WatchlistRequest):
    from .watchlist import score_watchlist

    return score_watchlist(req.symbols, req.timeframe)


@app.get("/api/watchlist/score")
async def watchlist_score_get(timeframe: str = "1h", symbols: str = ""):
    from .watchlist import DEFAULT_WATCHLIST, score_watchlist

    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()] or None
    return score_watchlist(syms or DEFAULT_WATCHLIST, timeframe)


@app.get("/api/journal/stats")
async def journal_stats():
    from .journal import stats

    return stats()


@app.get("/api/signals")
async def signals_list(limit: int = 80, symbol: str = "", strategy_id: str = ""):
    from .signals import list_signals, signal_stats

    sid = strategy_id.strip() or None
    rows = list_signals(limit, symbol or None, sid)
    return {
        "signals": rows,
        "stats": signal_stats(rows) if sid or symbol else signal_stats(),
    }


@app.get("/api/signals/dashboard")
async def signals_dashboard():
    """Strategy performance cards and chart series from the signal archive (WL-051)."""
    from .dashboard import build_dashboard

    return build_dashboard()


@app.get("/api/signals/{signal_id}")
async def signal_get(signal_id: str):
    """Full signal including multi_analysis_json and live_review_json (WL-054)."""
    from .signals import get_signal

    if signal_id in ("dashboard", "verify", "review"):
        raise HTTPException(404, "signal not found")
    sig = get_signal(signal_id)
    if not sig:
        raise HTTPException(404, "signal not found")
    return {"signal": sig}


@app.post("/api/signals/verify")
async def signals_verify(symbol: str = "", only_open: bool = True, limit: int = 50):
    """Re-check archived signals vs later candles (TP/SL/expired)."""
    from .signals import verify_all

    return verify_all(
        symbol=symbol or None,
        only_open=only_open,
        limit=limit,
    )


@app.post("/api/signals/review")
async def signals_review_all(only_open: bool = True, limit: int = 50):
    """Live review open signals: append stance history; originals stay frozen (WL-052)."""
    from .signals import live_review_all

    return live_review_all(only_open=only_open, limit=limit)


@app.post("/api/signals/{signal_id}/review")
async def signal_review_one(signal_id: str):
    from .signals import live_review_one, signal_stats

    sig, review, err = live_review_one(signal_id)
    if sig is None:
        raise HTTPException(404, "signal not found")
    if err in ("signal is not open", "incomplete levels"):
        raise HTTPException(400, err)
    return {"signal": sig, "review": review, "stats": signal_stats(), "warning": err}


@app.post("/api/signals/{signal_id}/verify")
async def signal_verify_one(signal_id: str):
    from .signals import signal_stats, verify_one

    sig = verify_one(signal_id, force=True)
    if not sig:
        raise HTTPException(404, "signal not found")
    return {"signal": sig, "stats": signal_stats()}


@app.get("/api/calendar", response_model=CalendarResponse)
def calendar_list(days: int = 7, kind: str = "") -> CalendarResponse:
    """Events from today 00:00 PKT for `days` more days, sorted by time, plus source status."""
    from .calendar_feed import list_events, source_status

    if kind and kind not in ("macro", "earnings", "crypto", "binance"):
        raise HTTPException(400, "kind must be macro, earnings, crypto or binance")
    return CalendarResponse(events=list_events(days, kind or None), sources=source_status())


@app.get("/api/jobs", response_model=JobsResponse)
def jobs_status() -> JobsResponse:
    """Last run per scheduled job plus its next run (sync: runs in the threadpool)."""
    from .jobs import job_status

    return JobsResponse(jobs=job_status())


@app.get("/api/journal")
async def journal_list(limit: int = 100):
    from .journal import list_entries, stats

    return {"entries": list_entries(limit), "stats": stats()}


@app.post("/api/journal")
async def journal_add(req: JournalCreate):
    from .journal import add_entry

    return add_entry(req.model_dump())


@app.post("/api/journal/{entry_id}/close")
async def journal_close(entry_id: str, req: JournalClose):
    from .journal import close_entry

    try:
        return close_entry(entry_id, req.status, req.exit_price)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.delete("/api/journal/{entry_id}")
async def journal_delete(entry_id: str):
    from .journal import delete_entry

    if not delete_entry(entry_id):
        raise HTTPException(404, "entry not found")
    return {"ok": True}


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    run()
