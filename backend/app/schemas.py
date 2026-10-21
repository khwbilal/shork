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
    disclaimer: str = (
        "Not financial advice. Analysis is informational only. "
        "Trading involves substantial risk of loss."
    )


class ChatResponse(BaseModel):
    symbol: str
    reply: str
    market_snapshot: dict[str, Any] | None = None
    provider: str
    disclaimer: str = (
        "Not financial advice. Analysis is informational only. "
        "Trading involves substantial risk of loss."
    )


class HealthResponse(BaseModel):
    status: str
    app: str
    ai_provider: str
    tradingview_ready: bool


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
