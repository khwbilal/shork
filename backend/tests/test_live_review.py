"""WL-052: live review appends history; originals stay frozen."""

from __future__ import annotations

from app.db import init_db
from app.signals import (
    REVIEW_BANK_TARGET_FRAC,
    REVIEW_EXIT_LOSS_R,
    compute_live_stance,
    live_review_one,
    live_review_signal,
    record_signal,
)


def _levels(entry: float = 100.0) -> dict:
    return {
        "bias": "Buy",
        "entry": entry,
        "stop_loss": entry - 10,
        "take_profit": entry + 20,
        "confidence": 0.5,
        "reasoning": "original note",
    }


def test_stance_hold_caution_exit():
    hold = compute_live_stance(
        bias="Buy", entry=100, stop_loss=90, take_profit=120, price=102, strategy_id="desk"
    )
    assert hold["stance"] == "hold"

    # Choppy: small R and flipped vs prior review.
    caution = compute_live_stance(
        bias="Buy",
        entry=100,
        stop_loss=90,
        take_profit=120,
        price=100.5,
        prior_unrealized_r=-0.1,
        strategy_id="desk",
    )
    assert caution["stance"] == "caution"

    exit_loss = compute_live_stance(
        bias="Buy",
        entry=100,
        stop_loss=90,
        take_profit=120,
        price=100 + REVIEW_EXIT_LOSS_R * 10 - 0.1,
        strategy_id="desk",
    )
    assert exit_loss["stance"] == "exit_early"

    bank = compute_live_stance(
        bias="Buy",
        entry=100,
        stop_loss=90,
        take_profit=120,
        price=100 + REVIEW_BANK_TARGET_FRAC * 20,
        strategy_id="desk",
    )
    assert bank["stance"] == "exit_early"


def test_stance_bands_differ_by_strategy():
    # -0.50R: scalping exits early; SMC still holds (wider loss band).
    price = 100 - 0.50 * 10
    scalp = compute_live_stance(
        bias="Buy",
        entry=100,
        stop_loss=90,
        take_profit=120,
        price=price,
        strategy_id="scalping",
    )
    smc = compute_live_stance(
        bias="Buy",
        entry=100,
        stop_loss=90,
        take_profit=120,
        price=price,
        strategy_id="smc",
    )
    assert scalp["stance"] == "exit_early"
    assert smc["stance"] == "hold"


def test_live_review_appends_and_keeps_originals(monkeypatch):
    init_db()
    monkeypatch.setattr("app.signals.verify_signal", lambda sig, force=False: sig)
    monkeypatch.setattr("app.signals._fetch_last_price", lambda _s: 105.0)

    sig = record_signal(
        symbol="BTCUSDT",
        timeframe="1h",
        levels=_levels(100),
        strategy_id="desk",
    )
    assert sig is not None
    sid = sig["id"]
    entry, sl, tp, notes = sig["entry"], sig["stop_loss"], sig["take_profit"], sig["notes"]

    out, review, err = live_review_one(sid)
    assert err is None and out is not None and review is not None
    assert out["entry"] == entry and out["stop_loss"] == sl and out["take_profit"] == tp
    assert out["notes"] == notes
    assert len(out["live_review_json"]) == 1
    assert review["stance"] in ("hold", "caution", "exit_early")
    assert review["price"] == 105.0

    monkeypatch.setattr("app.signals._fetch_last_price", lambda _s: 108.0)
    out2, review2, err2 = live_review_one(sid)
    assert err2 is None and out2 is not None and review2 is not None
    assert len(out2["live_review_json"]) == 2
    assert out2["entry"] == entry
    assert out2["live_review_json"][0]["price"] == 105.0
    assert out2["live_review_json"][1]["price"] == 108.0


def test_live_review_rejects_closed(monkeypatch):
    init_db()
    monkeypatch.setattr("app.signals.verify_signal", lambda sig, force=False: sig)
    monkeypatch.setattr("app.signals._fetch_last_price", lambda _s: 105.0)

    sig = record_signal(
        symbol="ETHUSDT",
        timeframe="1h",
        levels=_levels(200),
        strategy_id="breakout",
    )
    assert sig
    sig["status"] = "win"
    from app.db import SIGNAL_COLUMNS, connect, update_row

    with connect() as conn:
        update_row(conn, "signals", SIGNAL_COLUMNS, sig)

    out, review, err = live_review_one(sig["id"])
    assert err == "signal is not open"
    assert review is None
    assert out is not None
    assert out.get("live_review_json") in ([], None) or len(out.get("live_review_json") or []) == 0


def test_live_review_signal_no_price(monkeypatch):
    init_db()
    monkeypatch.setattr("app.signals.verify_signal", lambda sig, force=False: sig)
    monkeypatch.setattr("app.signals._fetch_last_price", lambda _s: None)

    sig = record_signal(
        symbol="SOLUSDT",
        timeframe="15m",
        levels=_levels(50),
        strategy_id="scalping",
    )
    assert sig
    updated, review, err = live_review_signal(sig)
    assert err is None
    assert review is not None
    assert review["price"] is None
    assert review["stance"] is None
    assert 'na("no live price")' in (review["summary"] or "")
    assert len(updated["live_review_json"]) == 1
