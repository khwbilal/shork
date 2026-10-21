"""market.context_to_prompt_block: order, pruning and the 8k budget."""

from __future__ import annotations

import json

from app.market import context_to_prompt_block

TRUNC = " …[truncated]"


def base_context(**overrides):
    ctx = {
        "tv_symbol": "BINANCE:BTCUSDT",
        "timeframe": "1h",
        "data_source": "test",
        "coin_analysis": {
            "price_data": {"current_price": 65000.0, "change_percent": 1.2},
            "rsi": {"value": 55.0, "signal": ""},
            "macd": {"crossover": None, "histogram": 12.5},
        },
        "setup": {
            "type": "trend_pullback",
            "trade_allowed": True,
            "prefer_bias": "Buy",
            "summary": "Pullback",
        },
        "confluence": {
            "bias": "Buy",
            "score": 3.0,
            "summary": "Confluence +3",
            "setup": {"type": "embedded copy"},
        },
    }
    ctx.update(overrides)
    return ctx


def test_guard_sections_come_first():
    keys = list(json.loads(context_to_prompt_block(base_context())))
    assert keys[:5] == ["pair", "timeframe", "price", "setup", "confluence"]


def test_embedded_setup_removed_from_confluence():
    data = json.loads(context_to_prompt_block(base_context()))
    assert "setup" not in data["confluence"]
    assert data["confluence"]["bias"] == "Buy"
    assert data["setup"]["type"] == "trend_pullback"


def test_empty_values_dropped():
    data = json.loads(context_to_prompt_block(base_context()))
    assert "rsi_signal" not in data  # ""
    assert "macd_crossover" not in data  # None
    assert "ema20" not in data  # missing source
    assert "mtf" not in data  # dict that pruned down to nothing
    assert data["rsi"] == 55.0
    # False is information, not emptiness
    assert data["orderbook"] == {"available": False}


def test_false_and_zero_are_kept():
    ctx = base_context()
    ctx["setup"]["trade_allowed"] = False
    ctx["confluence"]["score"] = 0
    data = json.loads(context_to_prompt_block(ctx))
    assert data["setup"]["trade_allowed"] is False
    assert data["confluence"]["score"] == 0


def test_small_block_untouched_by_budget():
    blob = context_to_prompt_block(base_context())
    assert len(blob) < 8000
    assert not blob.endswith(TRUNC)
    assert "macd_histogram" in json.loads(blob)


def test_low_value_sections_dropped_whole_in_order():
    ctx = base_context()
    ctx["coin_analysis"]["pivots"] = {"levels": ["p" * 50] * 120}  # about 6.3k chars
    ctx["coin_analysis"]["suggested_levels"] = {"note": "h" * 2000}
    ctx["coin_analysis"]["sma"] = {"sma50": 64000.0, "sma200": 60000.0}
    blob = context_to_prompt_block(ctx)
    data = json.loads(blob)
    assert len(blob) <= 8000
    assert "pivots" not in data  # dropped first
    assert data["level_hints"] == {"note": "h" * 2000}  # room after pivots went, kept whole
    assert data["sma50"] == 64000.0


def test_drops_continue_until_under_budget():
    ctx = base_context()
    ctx["coin_analysis"]["pivots"] = {"levels": ["p" * 50] * 120}
    ctx["coin_analysis"]["suggested_levels"] = {"note": "h" * 5000}
    ctx["regime"] = {"available": True, "summary": "r" * 3000}
    blob = context_to_prompt_block(ctx)
    data = json.loads(blob)
    assert len(blob) <= 8000
    assert "pivots" not in data and "level_hints" not in data
    assert data["regime"]["summary"] == "r" * 3000  # fits after two drops, so kept
    assert list(data)[3:5] == ["setup", "confluence"]


def test_hard_truncation_keeps_guard_sections():
    # Whale flow is not in the drop list; a huge summary forces the final cut.
    ctx = base_context(flow={"available": True, "summary": "w" * 20000})
    blob = context_to_prompt_block(ctx)
    assert blob.endswith(TRUNC)
    # WL-027: the marker counts against the budget, so the block is exactly max_chars.
    assert len(blob) == 8000
    head = blob[:600]
    assert '"setup":{' in head and '"confluence":{' in head


def test_custom_budget():
    blob = context_to_prompt_block(base_context(), max_chars=100)
    assert len(blob) == 100
    assert blob.endswith(TRUNC)
    assert blob.startswith('{"pair":"BINANCE:BTCUSDT"')


def test_budget_smaller_than_marker_still_capped():
    for budget in (0, 5, len(TRUNC)):
        assert len(context_to_prompt_block(base_context(), max_chars=budget)) <= budget
