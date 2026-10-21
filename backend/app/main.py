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
    HealthResponse,
    JobsResponse,
    JournalClose,
    JournalCreate,
    TradeLevels,
    WatchlistRequest,
)


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


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    settings = get_settings()
    pair = normalize_pair(req.symbol)
    if not pair:
        raise HTTPException(400, "Invalid symbol")

    market = await fetch_coin_context_async(
        pair, req.exchange, req.timeframe, settings
    )
    prompt = build_analysis_prompt(
        pair,
        req.exchange.upper(),
        req.timeframe,
        context_to_prompt_block(market),
        req.custom_prompt,
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
    levels = _apply_confluence_guardrail(levels, market)
    levels = _apply_reward_risk_guard(levels)
    analysis = format_clear_brief(
        pair, req.exchange.upper(), req.timeframe, levels, text
    )
    if provider != "offline" and levels.bias != model_bias:
        # The card below is the model's own; say why the plan's bias differs from it.
        conf = market.get("confluence") if isinstance(market.get("confluence"), dict) else {}
        analysis = (
            f"DESK OVERRIDE: the analyst said {model_bias}; the plan is {levels.bias} "
            f"(confluence {float(conf.get('score') or 0):+.1f}/10 and the R:R guard decide the bias).\n\n"
            + analysis
        )
    logger.info("analyze %s %s via %s -> %s", pair, req.timeframe, provider, levels.bias)

    # Archive Buy/Sell plans for later TP/SL verification. Offline plans are
    # never archived — the track record is for calls an AI actually made.
    if provider != "offline":
        try:
            from .signals import record_signal

            sig = record_signal(
                symbol=pair,
                timeframe=req.timeframe,
                levels=levels.model_dump(),
                market=market,
            )
            if sig:
                market = {**market, "recorded_signal_id": sig.get("id")}
        except Exception as exc:  # noqa: BLE001
            logger.warning("signal archive failed: %s", exc)

    return AnalyzeResponse(
        symbol=pair,
        exchange=req.exchange.upper(),
        timeframe=req.timeframe,
        tv_symbol=tv_symbol(pair, req.exchange),
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

    market = await fetch_coin_context_async(
        pair, req.exchange, req.timeframe, settings
    )
    prompt = build_chat_prompt(
        pair,
        req.exchange.upper(),
        req.timeframe,
        context_to_prompt_block(market),
        req.message.strip(),
        req.history,
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
async def signals_list(limit: int = 80, symbol: str = ""):
    from .signals import list_signals, signal_stats

    return {
        "signals": list_signals(limit, symbol or None),
        "stats": signal_stats(),
    }


@app.post("/api/signals/verify")
async def signals_verify(symbol: str = "", only_open: bool = True, limit: int = 50):
    """Re-check archived signals vs later candles (TP/SL/expired)."""
    from .signals import verify_all

    return verify_all(
        symbol=symbol or None,
        only_open=only_open,
        limit=limit,
    )


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
