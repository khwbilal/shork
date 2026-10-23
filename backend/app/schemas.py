from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    symbol: str = Field(..., examples=["SOLUSDT", "BTCUSDT", "ETHUSDT"])
    exchange: str = Field(default="BINANCE")
    timeframe: str = Field(default="1h", examples=["15m", "1h", "4h", "1D"])
    strategy_id: str = Field(
        default="desk",
        examples=["desk", "smc", "scalping", "all"],
        description="Use 'all' to run every pack and optimize.",
    )
    optimize_mode: str = Field(
        default="local_score",
        examples=["local_score", "ai_ensemble", "majority_vote"],
        description="Only used when strategy_id is 'all'.",
    )
    custom_prompt: str | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    symbol: str = Field(..., examples=["SOLUSDT"])
    exchange: str = Field(default="BINANCE")
    timeframe: str = Field(default="1h")
    strategy_id: str = Field(default="desk")
    message: str
    history: list[ChatMessage] = Field(default_factory=list)


class TradeLevels(BaseModel):
    bias: Literal["Buy", "Sell", "Neutral"] = "Neutral"
    entry: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    support: float | None = None
    resistance: float | None = None
    support_2: float | None = None
    resistance_2: float | None = None
    trend: str | None = None
    trend_line: str | None = None
    ema20: float | None = None
    ema50: float | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    reasoning: str = ""


class AnalyzeResponse(BaseModel):
    symbol: str
    exchange: str
    timeframe: str
    tv_symbol: str
    strategy_id: str = "desk"
    strategy_label: str = "Desk (default)"
    market: dict[str, Any]
    levels: TradeLevels
    analysis: str
    provider: str
    optimize_mode: str | None = None
    final_strategy_id: str | None = None
    packs: list[dict[str, Any]] | None = None


class ChatResponse(BaseModel):
    symbol: str
    reply: str
    market_snapshot: dict[str, Any] | None = None
    provider: str
    strategy_id: str = "desk"


class StrategyRiskInfo(BaseModel):
    stop_atr_min: float = 0.75
    stop_atr_max: float = 2.0
    min_reward_risk: float = 1.5
    target_r_min: float = 2.0
    review_near_stop_r: float = 0.35
    review_hold_min_r: float = -0.35
    review_hold_max_r: float = 0.70
    review_exit_loss_r: float = -0.60
    review_bank_target_frac: float = 0.85
    review_chop_band_r: float = 0.15


class StrategyInfo(BaseModel):
    id: str
    label: str
    summary: str
    primary_tf: str | None = None
    context_tfs: list[str] = []
    incompatible_desk_tfs: list[str] = []
    indicators: list[str] = []
    uses_desk_pipeline: bool = False
    risk: StrategyRiskInfo = Field(default_factory=StrategyRiskInfo)


class StrategiesResponse(BaseModel):
    strategies: list[StrategyInfo]
    default: str = "desk"


class HealthResponse(BaseModel):
    status: str
    app: str
    ai_provider: str
    ai_model: str | None = None
    tradingview_ready: bool


class CalendarEvent(BaseModel):
    id: int
    source: str  # forexfactory | nasdaq | binance
    kind: Literal["macro", "earnings", "crypto", "binance"]
    title: str
    starts_at: str  # ISO 8601 in PKT (+05:00)
    all_day: bool = False
    session: str | None = None  # earnings: before_open | after_close
    impact: Literal["high", "medium", "low"] | None = None
    country: str | None = None
    ticker: str | None = None
    instrument_symbols: list[str] = []  # TradingView symbols Binance lists for the ticker
    forecast: str | None = None
    previous: str | None = None
    actual: str | None = None
    url: str | None = None
    fetched_at: str


class CalendarSource(BaseModel):
    name: str
    available: bool | None = None
    error: str | None = None
    events: int | None = None
    fetched_at: str | None = None


class CalendarResponse(BaseModel):
    events: list[CalendarEvent]
    sources: list[CalendarSource]


class CorrelationStat(BaseModel):
    """Correlation and beta of the symbol's log returns to one benchmark."""

    available: bool
    correlation: float | None = None  # Pearson, -1 to 1
    beta: float | None = None  # cov(symbol, benchmark) / var(benchmark)
    overlap_pct: float | None = None  # share of expected candles present for both
    samples: int | None = None  # consecutive returns used
    error: str | None = None


class CorrelationWindow(BaseModel):
    interval: str  # 1h | 1d
    days: int
    candles: int  # expected closed candles in the window
    btc: CorrelationStat
    eth: CorrelationStat


class CorrelationResponse(BaseModel):
    available: bool
    symbol: str
    market: Literal["spot", "usdm", "spot_or_usdm"] | None = None
    windows: dict[str, CorrelationWindow] = {}  # keys: 30d_1h, 90d_1d
    summary: str | None = None
    error: str | None = None


class PulseCell(BaseModel):
    """One timeframe of the pulse; the last candle is the live one."""

    tf: Literal["1M", "1w", "1d", "1h", "15m"]
    available: bool
    price: float | None = None  # last close
    trend: Literal["up", "down", "flat"] | None = None
    rsi: float | None = None  # RSI 14
    ema20: float | None = None
    ema50: float | None = None
    price_vs_ema20: Literal["above", "below"] | None = None
    change_pct: float | None = None  # last candle vs the previous close
    bias: Literal["Buy", "Sell", "Neutral"] | None = None
    candle_open: str | None = None  # ISO 8601 UTC open time of the last candle
    error: str | None = None


class PulseSymbol(BaseModel):
    symbol: str
    available: bool  # the 24h ticker; cells carry their own flag
    price: float | None = None
    change_24h_pct: float | None = None
    error: str | None = None
    timeframes: list[PulseCell]


class PulseResponse(BaseModel):
    symbols: list[PulseSymbol]
    timeframes: list[str]
    rule: str  # the trend and bias rule in words
    generated_at: str


class JobStatus(BaseModel):
    job: str
    schedule: str
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    message: str | None = None
    next_run: str | None = None  # from Task Scheduler; None when not registered


class JobsResponse(BaseModel):
    jobs: list[JobStatus]


class WatchlistRequest(BaseModel):
    symbols: list[str] | None = None
    timeframe: str = "1h"


class JournalCreate(BaseModel):
    symbol: str
    timeframe: str = "1h"
    side: Literal["Buy", "Sell"] = "Buy"
    setup: str | None = None
    entry: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    confluence: float | None = None
    notes: str = ""


class JournalClose(BaseModel):
    status: Literal["win", "loss", "be", "skipped"]
    exit_price: float | None = None
