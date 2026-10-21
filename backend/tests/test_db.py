"""db.py migrations and JSON import, plus the journal and signals storage on SQLite."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone

import pytest

from app import db, journal, signals


@pytest.fixture
def path(tmp_path):
    p = db.db_path()
    assert p == tmp_path / "data" / "app.db"  # conftest isolation
    assert p != db.DEFAULT_DB_PATH
    return p


def tables(p):
    conn = sqlite3.connect(p)
    try:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    finally:
        conn.close()


# --- migrations -----------------------------------------------------------------


def test_migrations_apply_once(path):
    versions = [v for v, _name, _file in db._migrations()]
    assert versions[0] == 1 and versions == sorted(set(versions))
    assert db.migrate(path) == versions
    assert db.migrate(path) == []
    assert {"schema_version", "journal", "signals"} <= tables(path)
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute("SELECT version, name FROM schema_version ORDER BY version").fetchall()
        assert [v for v, _ in rows] == versions and rows[0] == (1, "init")
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    finally:
        conn.close()


def test_connect_migrates_and_enables_foreign_keys(path):
    with db.connect() as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone() == {"foreign_keys": 1}
    assert "journal" in tables(path)


def test_connect_rolls_back_on_error(path):
    with pytest.raises(RuntimeError):
        with db.connect() as conn:
            conn.execute("INSERT INTO journal (id, symbol) VALUES ('aaaaaaaa', 'X')")
            raise RuntimeError("boom")
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM journal").fetchone()["n"] == 0


def test_connect_from_threads(path):
    errors = []

    def work():
        try:
            for _ in range(5):
                journal.add_entry({"symbol": "btcusdt"})
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=work) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert journal.stats()["total"] == 20


# --- journal ----------------------------------------------------------------------


def test_journal_round_trip(path):
    a = journal.add_entry(
        {"symbol": "btcusdt", "side": "Buy", "entry": 100.0, "stop_loss": 95.0,
         "take_profit": 110.0, "setup": "pullback", "confluence": 3.0}
    )
    assert len(a["id"]) == 8
    assert a["symbol"] == "BTCUSDT" and a["status"] == "open" and a["timeframe"] == "1h"
    b = journal.add_entry({"symbol": "ethusdt", "side": "Sell", "entry": 50.0, "stop_loss": 55.0})

    listed = journal.list_entries()
    assert [r["id"] for r in listed] == [b["id"], a["id"]]  # newest first
    assert listed[1] == a  # same keys and values as add_entry returned
    assert list(listed[1]) == list(a)  # same key order
    assert journal.list_entries(limit=1) == [listed[0]]

    closed = journal.close_entry(a["id"], "WIN", exit_price=110.0)
    assert closed["status"] == "win" and closed["r_multiple"] == 2.0 and closed["closed_at"]
    assert journal.list_entries()[1] == closed

    sold = journal.close_entry(b["id"], "loss", exit_price=55.0)
    assert sold["r_multiple"] == -1.0

    st = journal.stats()
    assert st == {
        "total": 2, "open": 0, "closed": 2, "wins": 1, "losses": 1, "breakeven": 0,
        "hit_rate": 0.5, "avg_r": 0.5,
        "by_setup": {"pullback": {"n": 1, "wins": 1, "hit_rate": 1.0},
                     "unknown": {"n": 1, "wins": 0, "hit_rate": 0.0}},
    }

    assert journal.delete_entry(a["id"]) is True
    assert journal.delete_entry(a["id"]) is False
    assert [r["id"] for r in journal.list_entries()] == [b["id"]]


def test_journal_close_errors(path):
    with pytest.raises(ValueError):
        journal.close_entry("whatever", "open")
    with pytest.raises(KeyError):
        journal.close_entry("missing1", "win")


def test_journal_ties_keep_insertion_order(path, monkeypatch):
    monkeypatch.setattr(journal, "_now", lambda: "2026-01-01T00:00:00+00:00")
    ids = [journal.add_entry({"symbol": f"c{i}"})["id"] for i in range(3)]
    assert [r["id"] for r in journal.list_entries()] == ids


# --- signals ----------------------------------------------------------------------


LEVELS = {"bias": "Buy", "entry": 100, "stop_loss": 95, "take_profit": 110, "confidence": 0.7,
          "reasoning": "why"}
MARKET = {"setup": {"type": "pullback", "trade_allowed": True}, "confluence": {"score": 3.0}}


def test_record_signal_round_trip(path):
    assert signals.record_signal(symbol="btcusdt", timeframe="4h", levels={"bias": "Neutral"}) is None
    assert signals.record_signal(symbol="btcusdt", timeframe="4h", levels={"bias": "Buy", "entry": 1}) is None

    sig = signals.record_signal(symbol="btcusdt", timeframe="4h", levels=LEVELS, market=MARKET)
    assert len(sig["id"]) == 8
    assert sig["trade_allowed"] is True and sig["entry"] == 100.0 and sig["status"] == "open"

    # Dedupe within 30 minutes returns the stored row
    again = signals.record_signal(symbol="BTCUSDT", timeframe="4h", levels=LEVELS, market=MARKET)
    assert again == sig

    other = signals.record_signal(symbol="ethusdt.p", timeframe="1h",
                                  levels={**LEVELS, "bias": "Sell", "stop_loss": 105, "take_profit": 90})
    assert other["trade_allowed"] is None

    listed = signals.list_signals()
    assert [r["id"] for r in listed] == [other["id"], sig["id"]]
    assert listed[1] == sig and list(listed[1]) == list(sig)
    assert signals.list_signals(symbol="ETHUSDT") == [other]  # .P stripped on both sides
    assert signals.list_signals(limit=1) == [other]

    st = signals.signal_stats()
    assert st["total"] == 2 and st["open"] == 2 and st["hit_rate"] is None


def test_verify_writes_back(path, monkeypatch):
    sig = signals.record_signal(symbol="btcusdt", timeframe="1h", levels=LEVELS, market=MARKET)
    t0 = int(datetime.now(timezone.utc).timestamp() * 1000) + 60_000
    bars = [{"t": t0, "o": 100, "h": 111, "l": 99, "c": 110}]
    monkeypatch.setattr(signals, "_fetch_klines_after", lambda *a, **k: bars)

    out = signals.verify_one(sig["id"])
    assert out["status"] == "win" and out["r_multiple"] == 2.0
    assert signals.list_signals()[0] == out
    assert signals.verify_one("missing1") is None

    st = signals.signal_stats()
    assert st["wins"] == 1 and st["hit_rate"] == 1.0
    assert st["by_setup"] == {"pullback": {"n": 1, "wins": 1, "hit_rate": 1.0}}


def test_verify_all_offline(path):
    # conftest blocks the network, so the fetch returns no bars
    sig = signals.record_signal(symbol="btcusdt", timeframe="1h", levels=LEVELS, market=MARKET)
    res = signals.verify_all()
    assert res["checked"] == 1 and res["updated"] == 0
    row = signals.list_signals()[0]
    assert row["id"] == sig["id"] and row["outcome"] == "waiting_for_bars" and row["verified_at"]


# --- JSON import ------------------------------------------------------------------


def _old_signal(sid, minutes_ago=0):
    ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
    return {
        "id": sid, "created_at": ts, "symbol": "BTCUSDT", "timeframe": "4h", "bias": "Buy",
        "entry": 100.0, "stop_loss": 95.0, "take_profit": 110.0, "price_at_signal": 100.5,
        "setup": "pullback", "trade_allowed": False, "confluence": 3.0, "confidence": 0.6,
        "status": "open", "outcome": None, "verified_at": None, "bars_checked": 0,
        "hit_price": None, "hit_at": None, "r_multiple": None, "notes": "n",
    }


def test_json_import_is_idempotent_and_renames(path):
    data_dir = path.parent
    data_dir.mkdir(parents=True, exist_ok=True)
    old = [_old_signal("abcd1234", 10), _old_signal("bcde2345", 5)]
    (data_dir / "signals.json").write_text(json.dumps(old), encoding="utf-8")
    entry = {"id": "jjjj0001", "created_at": "2026-01-01T00:00:00+00:00", "symbol": "ETHUSDT",
             "timeframe": "1h", "side": "Buy", "setup": None, "entry": 1.0, "stop_loss": 0.9,
             "take_profit": 1.2, "confluence": None, "notes": "", "status": "open",
             "exit_price": None, "closed_at": None, "r_multiple": None}
    (data_dir / "journal.json").write_text(json.dumps([entry]), encoding="utf-8")

    assert db.init_db() == {"journal": 1, "signals": 2}
    assert not (data_dir / "signals.json").exists()
    assert (data_dir / "signals.json.imported").exists()
    assert (data_dir / "journal.json.imported").exists()
    assert signals.list_signals() == [old[1], old[0]]  # exact dicts, bool restored
    assert journal.list_entries() == [entry]

    # Run again: nothing to import
    assert db.init_db() == {}

    # The same file showing up again adds nothing and keeps the first backup
    (data_dir / "signals.json").write_text(json.dumps(old), encoding="utf-8")
    assert db.import_json_files() == {"signals": 0}
    assert (data_dir / "signals.json.imported.2").exists()
    assert signals.signal_stats()["total"] == 2


def test_broken_json_is_left_in_place(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    (path.parent / "journal.json").write_text("{not json", encoding="utf-8")
    assert db.import_json_files() == {}
    assert (path.parent / "journal.json").exists()
