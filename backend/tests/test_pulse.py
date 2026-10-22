"""pulse: BTC and ETH per-timeframe trend, RSI and bias on stubbed klines (WL-035)."""

from __future__ import annotations

import asyncio
import math

import pytest

from app import pulse
from app.pulse import bias_of, cell_from_klines, trend_of


def klines(closes):
    return [[1_700_000_000_000 + i * 60_000, "0", "0", "0", str(c)] for i, c in enumerate(closes)]


def rising(n=120):
    # Up drift with pullbacks, so RSI stays below 70.
    return [100 + i * 0.5 + 3 * math.sin(i * 0.9) for i in range(n)]


def falling(n=120):
    return [200 - i * 0.5 + 3 * math.sin(i * 0.9) for i in range(n)]


@pytest.fixture(autouse=True)
def _fresh_cache():
    pulse.clear_cache()
    yield
    pulse.clear_cache()


def test_trend_rule():
    assert trend_of(110, 105, 100) == "up"
    assert trend_of(90, 95, 100) == "down"
    assert trend_of(103, 105, 100) == "flat"  # EMAs up but price under EMA20
    assert trend_of(97, 95, 100) == "flat"


def test_bias_rule():
    assert bias_of("up", 60) == "Buy"
    assert bias_of("up", 75) == "Neutral"  # stretched
    assert bias_of("down", 40) == "Sell"
    assert bias_of("down", 25) == "Neutral"
    assert bias_of("flat", 50) == "Neutral"
    assert bias_of("up", None) == "Neutral"


def test_cell_uptrend_and_downtrend():
    up = cell_from_klines("1h", klines(rising()))
    assert up["available"] and up["trend"] == "up" and up["bias"] == "Buy"
    assert up["rsi"] < 70 and up["price_vs_ema20"] == "above"
    closes = rising()
    assert up["change_pct"] == round((closes[-1] - closes[-2]) / closes[-2] * 100, 2)
    down = cell_from_klines("1d", klines(falling()))
    assert down["trend"] == "down" and down["bias"] == "Sell"
    assert down["price_vs_ema20"] == "below"


def test_cell_needs_enough_candles():
    cell = cell_from_klines("1M", klines(rising(30)))
    assert cell == {"tf": "1M", "available": False, "error": "only 30 candles, need 51"}


def stub(monkeypatch, fail_tf=None, ticker_fails=False):
    calls = {"klines": 0, "ticker": 0}

    async def fake_klines(_client, symbol, tf):
        calls["klines"] += 1
        if tf == fail_tf:
            raise RuntimeError(f"boom {symbol} {tf}")
        return klines(rising() if symbol == "BTCUSDT" else falling())

    async def fake_ticker(_client, symbol):
        calls["ticker"] += 1
        if ticker_fails:
            raise RuntimeError("ticker down")
        return {"lastPrice": "65000.5", "priceChangePercent": "-1.234"}

    monkeypatch.setattr(pulse, "_fetch_klines", fake_klines)
    monkeypatch.setattr(pulse, "_fetch_ticker", fake_ticker)
    return calls


def test_build_pulse_shape(monkeypatch):
    stub(monkeypatch)
    out = asyncio.run(pulse.build_pulse())
    assert [s["symbol"] for s in out["symbols"]] == ["BTCUSDT", "ETHUSDT"]
    btc, eth = out["symbols"]
    assert btc["price"] == 65000.5 and btc["change_24h_pct"] == -1.23
    assert [c["tf"] for c in btc["timeframes"]] == ["1M", "1w", "1d", "1h", "15m"]
    assert all(c["bias"] == "Buy" for c in btc["timeframes"])
    assert all(c["bias"] == "Sell" for c in eth["timeframes"])
    assert "EMA20" in out["rule"]


def test_failed_timeframe_only_marks_that_cell(monkeypatch):
    stub(monkeypatch, fail_tf="1w")
    out = asyncio.run(pulse.build_pulse())
    for sym in out["symbols"]:
        cells = {c["tf"]: c for c in sym["timeframes"]}
        assert cells["1w"]["available"] is False and "boom" in cells["1w"]["error"]
        assert all(cells[tf]["available"] for tf in ("1M", "1d", "1h", "15m"))
        assert sym["available"] is True


def test_ticker_failure_keeps_cells(monkeypatch):
    stub(monkeypatch, ticker_fails=True)
    btc = asyncio.run(pulse.build_pulse())["symbols"][0]
    assert btc["available"] is False and btc["price"] is None and btc["error"] == "ticker down"
    assert all(c["available"] for c in btc["timeframes"])


def test_cache_serves_repeat_polls(monkeypatch):
    calls = stub(monkeypatch)
    asyncio.run(pulse.build_pulse())
    asyncio.run(pulse.build_pulse())
    assert calls == {"klines": 10, "ticker": 2}
    pulse.clear_cache()
    asyncio.run(pulse.build_pulse())
    assert calls == {"klines": 20, "ticker": 4}


def test_cache_expires(monkeypatch):
    calls = stub(monkeypatch)
    asyncio.run(pulse.build_pulse())
    monkeypatch.setattr(pulse, "CACHE_TTL", 0.0)
    asyncio.run(pulse.build_pulse())
    assert calls["klines"] == 20


def test_real_fetch_blocked_returns_unavailable_cells():
    # conftest blocks the network: every cell and ticker must degrade, not raise.
    out = asyncio.run(pulse.build_pulse())
    assert all(not s["available"] for s in out["symbols"])
    assert all(not c["available"] for s in out["symbols"] for c in s["timeframes"])


def test_endpoint(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    stub(monkeypatch)
    r = TestClient(app).get("/api/pulse")
    assert r.status_code == 200
    body = r.json()
    assert body["timeframes"] == ["1M", "1w", "1d", "1h", "15m"]
    assert body["symbols"][1]["timeframes"][0]["trend"] == "down"
