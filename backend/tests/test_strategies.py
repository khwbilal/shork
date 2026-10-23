"""WL-050: strategy registry, TF resolution, structure helpers, signal strategy_id."""

from __future__ import annotations

from app.binance_ta import (
    _bos_choch,
    _equal_levels,
    _fibonacci,
    _pivot_swings,
    build_suggested_levels,
    pick_indicator_blocks,
)
from app.strategies import get_strategy, list_strategies, resolve_timeframes, review_thresholds


def test_catalog_has_desk_and_seven_templates():
    ids = {s["id"] for s in list_strategies()}
    assert "desk" in ids
    for sid in (
        "smc",
        "liquidity_sweep",
        "breakout",
        "pullback",
        "retracement",
        "scalping",
        "ema_volatility",
    ):
        assert sid in ids
    assert get_strategy(None).id == "desk"
    assert get_strategy("unknown").id == "desk"
    assert get_strategy("SMC").id == "smc"


def test_resolve_timeframes_named_strategy_owns_primary():
    scalp = get_strategy("scalping")
    primary, context, overridden = resolve_timeframes(scalp, "1d")
    assert overridden is True
    assert primary == "5m"
    assert "15m" in context

    # Desk TF is ignored for named packs; primary is always the strategy's.
    primary2, ctx2, overridden2 = resolve_timeframes(scalp, "15m")
    assert overridden2 is True
    assert primary2 == "5m"
    assert "15m" in ctx2

    smc = get_strategy("smc")
    p_smc, c_smc, _ = resolve_timeframes(smc, "1h")
    assert p_smc == "15m"
    assert c_smc == ["1h", "4h"]

    desk = get_strategy("desk")
    p, c, o = resolve_timeframes(desk, "4h")
    assert p == "4h" and c == [] and o is False


def test_named_pack_fetches_every_needed_tf(monkeypatch):
    from app import market
    from app.config import Settings

    calls: list[str] = []

    def fake_local(pair: str, tf: str, **_kwargs):
        calls.append(tf)
        return {
            "price_data": {"current_price": 1.0},
            "atr": {"value": 0.1},
            "ema": {"ema20": 1.0},
            "structure": {"bias": "Neutral"},
            "support_resistance": {"nearest_support": 0.9, "nearest_resistance": 1.1},
            "suggested_levels": {
                "entry": 1.0,
                "stop_loss": 0.9,
                "take_profit": 1.2,
                "trend": "Neutral",
            },
        }

    monkeypatch.setattr(market, "compute_local_analysis", fake_local)
    settings = Settings(_env_file=None, ai_provider="none")
    ctx = market._build_named_strategy_pack("BTCUSDT", "BINANCE", "1h", settings, "smc")
    frames = (ctx.get("strategy_pack") or {}).get("timeframes") or {}
    assert set(frames.keys()) == {"15m", "1h", "4h"}
    assert set(calls) == {"15m", "1h", "4h"}
    assert (ctx.get("strategy_pack") or {}).get("needed_tfs") == ["15m", "1h", "4h"]


def test_pivot_equal_bos_fib_on_fixed_series():
    # Synthetic uptrend with two equal highs near the end.
    closes = [float(i) for i in range(1, 41)]
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    # Force two equal swing highs
    highs[20] = 30.0
    highs[30] = 30.0
    lows[15] = 10.0
    lows[25] = 18.0

    sh, sl = _pivot_swings(highs, lows, left=2, right=2)
    assert isinstance(sh, list) and isinstance(sl, list)

    eq = _equal_levels([{"index": 20, "price": 30.0}, {"index": 30, "price": 30.0}])
    assert eq and eq[0]["count"] >= 2

    structure = _bos_choch(
        [{"index": 10, "price": 20.0}, {"index": 30, "price": 35.0}],
        [{"index": 5, "price": 8.0}, {"index": 25, "price": 12.0}],
        closes,
    )
    assert structure["bias"] in ("Bullish", "Bearish", "Neutral")

    fib = _fibonacci(
        [{"index": 30, "price": 40.0}],
        [{"index": 10, "price": 10.0}],
        closes,
    )
    assert fib.get("available") is True
    assert "0.618" in (fib.get("levels") or {})


def test_pick_indicator_blocks_keeps_price():
    analysis = {
        "price_data": {"current_price": 1.0},
        "atr": {"value": 0.1},
        "ema": {"ema20": 1.0},
        "rsi": {"value": 50},
        "noise": 1,
    }
    picked = pick_indicator_blocks(analysis, ("ema", "rsi"))
    assert "ema" in picked and "rsi" in picked
    assert "price_data" in picked and "atr" in picked
    assert "noise" not in picked


def test_risk_profiles_scalping_tighter_than_smc():
    scalp = get_strategy("scalping").risk
    smc = get_strategy("smc").risk
    assert scalp.stop_atr_max < smc.stop_atr_max
    assert scalp.stop_atr_min <= smc.stop_atr_min
    assert scalp.review_exit_loss_r > smc.review_exit_loss_r  # -0.40 > -0.75
    bands = review_thresholds("scalping")
    assert bands["exit_loss_r"] == scalp.review_exit_loss_r
    catalog = {s["id"]: s for s in list_strategies()}
    assert "risk" in catalog["desk"]
    assert catalog["scalping"]["risk"]["stop_atr_max"] == 1.0


def test_build_suggested_levels_respects_atr_bands():
    # Wide swing would want a huge stop; clamp to max ATR.
    wide = build_suggested_levels(
        price=100.0,
        trend="Bullish",
        recent_high=110.0,
        recent_low=50.0,
        atr=2.0,
        stop_atr_min=0.5,
        stop_atr_max=1.0,
        target_r_min=1.5,
    )
    risk = 100.0 - wide["stop_loss"]
    assert abs(risk - 2.0) < 1e-6  # 1.0 ATR * atr

    tight_floor = build_suggested_levels(
        price=100.0,
        trend="Bullish",
        recent_high=101.0,
        recent_low=99.8,
        atr=2.0,
        stop_atr_min=0.75,
        stop_atr_max=2.0,
        target_r_min=2.0,
    )
    risk2 = 100.0 - tight_floor["stop_loss"]
    assert abs(risk2 - 1.5) < 1e-6  # 0.75 ATR floor


def test_record_signal_writes_strategy_id():
    from app.db import init_db
    from app.signals import list_signals, record_signal

    init_db()
    sig = record_signal(
        symbol="BTCUSDT",
        timeframe="1h",
        levels={
            "bias": "Buy",
            "entry": 100.0,
            "stop_loss": 90.0,
            "take_profit": 120.0,
            "confidence": 0.6,
            "reasoning": "test",
        },
        market={"setup": {"type": "breakout", "trade_allowed": True}, "confluence": {"score": 3}},
        strategy_id="breakout",
    )
    assert sig is not None
    assert sig.get("strategy_id") == "breakout"
    rows = list_signals(limit=10, strategy_id="breakout")
    assert any(r.get("id") == sig["id"] for r in rows)
    desk_only = list_signals(limit=10, strategy_id="desk")
    assert all(r.get("id") != sig["id"] for r in desk_only)
