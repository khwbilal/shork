"""WL-051: signal performance dashboard aggregates."""

from __future__ import annotations

from app.dashboard import build_dashboard
from app.db import init_db
from app.signals import record_signal


def _levels(bias: str = "Buy", entry: float = 100.0) -> dict:
    return {
        "bias": bias,
        "entry": entry,
        "stop_loss": entry - 5,
        "take_profit": entry + 10,
        "confidence": 0.6,
        "reasoning": "t",
    }


def test_dashboard_empty():
    init_db()
    dash = build_dashboard()
    assert dash["overall"]["n"] == 0
    assert dash["best"] is None and dash["worst"] is None
    assert dash["volume_by_day"]
    assert len(dash["volume_by_day"]) == 30
    assert any(b["id"] == "desk" for b in dash["by_strategy"])


def test_dashboard_by_strategy_and_best_worst():
    init_db()
    # Five decided wins for breakout (reliable), five losses for scalping.
    for i in range(5):
        sig = record_signal(
            symbol="BTCUSDT",
            timeframe="1h",
            levels=_levels(entry=100.0 + i),
            strategy_id="breakout",
        )
        assert sig
        sig["status"] = "win"
        sig["r_multiple"] = 2.0
        sig["verified_at"] = f"2026-10-{10 + i:02d}T12:00:00+00:00"
        from app.db import SIGNAL_COLUMNS, connect, update_row

        with connect() as conn:
            update_row(conn, "signals", SIGNAL_COLUMNS, sig)

    for i in range(5):
        sig = record_signal(
            symbol="ETHUSDT",
            timeframe="5m",
            levels=_levels(bias="Sell", entry=200.0 + i),
            strategy_id="scalping",
        )
        assert sig
        sig["status"] = "loss"
        sig["r_multiple"] = -1.0
        sig["verified_at"] = f"2026-10-{10 + i:02d}T13:00:00+00:00"
        from app.db import SIGNAL_COLUMNS, connect, update_row

        with connect() as conn:
            update_row(conn, "signals", SIGNAL_COLUMNS, sig)

    dash = build_dashboard()
    assert dash["overall"]["wins"] == 5
    assert dash["overall"]["losses"] == 5
    assert dash["best"] == "breakout"
    assert dash["worst"] == "scalping"
    assert dash["equity_curve"]
    by = {b["id"]: b for b in dash["by_strategy"]}
    assert by["breakout"]["reliable"] is True
    assert by["scalping"]["hit_rate"] == 0.0
    assert by["breakout"]["hit_rate"] == 1.0
