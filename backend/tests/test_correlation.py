"""correlation: Pearson and beta of log returns to BTC and ETH on fixed synthetic series (WL-036)."""

from __future__ import annotations

import math
import sys
import types

import pytest

from app import correlation, market
from app.correlation import compute_correlation, pair_stats

H = 3_600_000
D = 86_400_000
NOW = 1_800_000_000_000  # fixed clock; every candle below is closed


def series(n, interval=H, start=NOW - 2000 * H, fn=None):
    """Klines with a wiggly close; fn maps the base close to another close."""
    fn = fn or (lambda c: c)
    out = []
    for i in range(n):
        base = 100 * math.exp(0.01 * math.sin(i * 0.7) + 0.004 * math.cos(i * 1.9) + 0.0005 * i)
        out.append([start + i * interval, "0", "0", "0", str(fn(base))])
    return out


def test_identical_series_correlation_one_beta_one():
    k = series(720)
    s = pair_stats(k, k, H, 720, now_ms=NOW)
    assert s["available"] is True
    assert s["correlation"] == 1.0
    assert s["beta"] == 1.0
    assert s["overlap_pct"] == 100.0


def test_inverse_series_correlation_minus_one():
    bench = series(720)
    inv = series(720, fn=lambda c: 10_000 / c)  # log return is the negative
    s = pair_stats(inv, bench, H, 720, now_ms=NOW)
    assert s["correlation"] == -1.0
    assert s["beta"] == -1.0


def test_doubled_series_beta_two():
    bench = series(720)
    doubled = series(720, fn=lambda c: c * c / 100)  # log returns are exactly doubled
    s = pair_stats(doubled, bench, H, 720, now_ms=NOW)
    assert s["correlation"] == 1.0
    assert s["beta"] == 2.0


def test_insufficient_overlap_is_unavailable():
    bench = series(720)
    sym = series(300, start=bench[-300][0])  # 300 of 720 = 42% overlap
    s = pair_stats(sym, bench, H, 720, now_ms=NOW)
    assert s["available"] is False
    assert "overlap" in s["error"]
    assert s["overlap_pct"] == pytest.approx(41.7)


def test_open_candle_is_ignored():
    k = series(720)
    # The last candle opens one interval before NOW plus one ms, so it is still open.
    k_open = k + [[NOW - H + 1, "0", "0", "0", "999999"]]
    assert pair_stats(k_open, k_open, H, 720, now_ms=NOW)["correlation"] == 1.0


def test_flat_benchmark_is_unavailable():
    k = series(720)
    flat = [[r[0], "0", "0", "0", "50"] for r in k]
    s = pair_stats(k, flat, H, 720, now_ms=NOW)
    assert s["available"] is False


def test_compute_correlation_with_stub_fetch():
    calls = []

    def fetch(mkt, symbol, interval, limit):
        calls.append((mkt, symbol, interval, limit))
        if interval == "1h":
            base = series(limit, H, start=NOW - limit * H)
        else:
            base = series(limit, D, start=NOW - limit * D)
        if symbol == "SOLUSDT":
            return [[r[0], "0", "0", "0", str(float(r[4]) ** 2 / 100)] for r in base]
        return base

    out = compute_correlation("SOLUSDT", fetch=fetch, now_ms=NOW)
    assert out["available"] is True
    assert set(out["windows"]) == {"30d_1h", "90d_1d"}
    for win in out["windows"].values():
        assert win["btc"]["beta"] == 2.0
        assert win["eth"]["correlation"] == 1.0
    assert out["windows"]["30d_1h"]["candles"] == 720
    assert out["windows"]["90d_1d"]["candles"] == 90
    assert {c[3] for c in calls} == {721, 91}
    assert "BTC corr +1.00 beta 2.00" in out["summary"]


def test_perp_symbol_uses_futures():
    seen = set()

    def fetch(mkt, symbol, interval, limit):
        seen.add((mkt, symbol))
        raise RuntimeError("stub")

    out = compute_correlation("NVDAUSDT.P", fetch=fetch, now_ms=NOW)
    assert out["available"] is False
    assert out["market"] == "usdm"
    assert ("usdm", "NVDAUSDT") in seen and ("usdm", "BTCUSDT") in seen
    assert out["error"] == "stub"


def test_fetch_failure_never_raises():
    # The real fetcher hits the blocked network and must come back as unavailable.
    correlation.clear_cache()
    out = compute_correlation("BTCUSDT")
    assert out["available"] is False
    assert out["windows"]["30d_1h"]["btc"]["available"] is False


def test_snapshot_has_correlation_field(monkeypatch, make_settings):
    # Keep TradingView out of the test: fake modules without the service functions.
    fake = types.ModuleType("tradingview_mcp")
    core = types.ModuleType("tradingview_mcp.core")
    services = types.ModuleType("tradingview_mcp.core.services")
    services.screener_service = types.SimpleNamespace()
    services.yahoo_finance_service = types.SimpleNamespace()
    for name, mod in (
        ("tradingview_mcp", fake),
        ("tradingview_mcp.core", core),
        ("tradingview_mcp.core.services", services),
    ):
        monkeypatch.setitem(sys.modules, name, mod)
    stub = {"available": True, "symbol": "SOLUSDT", "windows": {
        "30d_1h": {"btc": {"available": True, "correlation": 0.8, "beta": 1.5}, "eth": {"available": False}},
    }}
    monkeypatch.setattr(correlation, "compute_correlation", lambda symbol: stub)
    ctx = market.fetch_coin_context("SOLUSDT", "BINANCE", "1h", make_settings())
    assert ctx["correlation"] == stub
    block = market.context_to_prompt_block(ctx)
    assert '"correlation":{"30d_1h":{"btc_corr":0.8,"btc_beta":1.5}}' in block
    assert len(block) <= 8000


def test_snapshot_survives_correlation_crash(monkeypatch, make_settings):
    monkeypatch.setitem(sys.modules, "tradingview_mcp", types.ModuleType("tradingview_mcp"))

    def boom(symbol):
        raise ValueError("kaput")

    monkeypatch.setattr(correlation, "compute_correlation", boom)
    ctx = market.fetch_coin_context("SOLUSDT", "BINANCE", "1h", make_settings())
    assert ctx["correlation"] == {"available": False, "error": "kaput"}
    assert market.condense_market_context(ctx)["correlation"] == {"available": False}


def test_endpoint_shape(monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    def fake(symbol):
        return compute_correlation(symbol, fetch=lambda *a: series(a[3], H if a[2] == "1h" else D,
                                   start=NOW - a[3] * (H if a[2] == "1h" else D)), now_ms=NOW)

    monkeypatch.setattr(correlation, "compute_correlation", fake)
    r = TestClient(app).get("/api/correlation/ETHUSDT")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    assert body["windows"]["90d_1d"]["btc"]["correlation"] == 1.0
