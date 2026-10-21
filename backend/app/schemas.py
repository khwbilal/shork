from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    symbol: str = Field(..., examples=["SOLUSDT", "BTCUSDT", "ETHUSDT"])
    exchange: str = Field(default="BINANCE")
    timeframe: str = Field(default="1h", examples=["15m", "1h", "4h", "1D"])
    custom_prompt: str | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    symbol: str = Field(..., examples=["SOLUSDT"])
    exchange: str = Field(default="BINANCE")
    timeframe: str = Field(default="1h")
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
    market: dict[str, Any]
    levels: TradeLevels
    analysis: str
    provider: str


class ChatResponse(BaseModel):
    symbol: str
    reply: str
    market_snapshot: dict[str, Any] | None = None
    provider: str


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
