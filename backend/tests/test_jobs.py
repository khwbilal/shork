"""Scheduled jobs runner (app.jobs) and the backup job, all in tmp_path."""

from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from app import db, jobs, signals
from app.jobs import __main__ as jobs_main
from app.jobs import backup

LEVELS = {"bias": "Buy", "entry": 100, "stop_loss": 95, "take_profit": 110}


@pytest.fixture
def bdir(tmp_path):
    d = backup.backup_dir()
    assert d == tmp_path / "backups"  # conftest isolation
    assert d != backup.DEFAULT_BACKUP_DIR
    return d


@pytest.fixture(autouse=True)
def no_schtasks(monkeypatch):
    monkeypatch.setattr(jobs, "_next_run", lambda _name: None)


def read_signals(path):
    conn = sqlite3.connect(path)
    try:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
        return [r[0] for r in conn.execute("SELECT id FROM signals")]
    finally:
        conn.close()


def runs():
    with db.connect() as conn:
        return conn.execute("SELECT * FROM job_runs ORDER BY id").fetchall()


def test_backup_creates_todays_copy(bdir):
    sig = signals.record_signal(symbol="btcusdt", timeframe="4h", levels=LEVELS)
    assert jobs.run_job("backup") == 0
    today = bdir / f"{date.today().isoformat()}.db"
    assert today.exists()
    assert read_signals(today) == [sig["id"]]
    assert sorted(p.name for p in bdir.iterdir()) == [today.name]  # no tmp, wal or shm left


def test_same_day_rerun_overwrites(bdir):
    jobs.run_job("backup")
    sig = signals.record_signal(symbol="ethusdt", timeframe="1h", levels=LEVELS)
    assert jobs.run_job("backup") == 0
    files = list(bdir.iterdir())
    assert len(files) == 1
    assert read_signals(files[0]) == [sig["id"]]


def test_retention_keeps_30_and_ignores_other_files(bdir):
    bdir.mkdir(parents=True)
    old = [bdir / f"2020-01-{d:02d}.db" for d in range(1, 32)]  # 31 old dated files
    for p in old:
        p.write_bytes(b"x")
    others = ["notes.txt", "2020-01-01.db.bak", "manual.db", "2020-1-1.db"]
    for name in others:
        (bdir / name).write_bytes(b"keep")

    backup.run(today=date(2026, 10, 21))
    names = {p.name for p in bdir.iterdir()}
    dated = sorted(n for n in names if n.endswith(".db") and n[:4].isdigit() and len(n) == 13)
    assert len(dated) == 30
    assert "2026-10-21.db" in dated
    # the two oldest went: 31 old + 1 new = 32, keep 30
    assert "2020-01-01.db" not in names and "2020-01-02.db" not in names
    assert "2020-01-03.db" in names
    assert set(others) <= names


def test_job_run_rows_and_log(bdir):
    assert jobs.run_job("backup") == 0
    rows = runs()
    assert len(rows) == 1
    row = rows[0]
    assert row["job"] == "backup" and row["exit_code"] == 0
    assert row["started_at"] and row["finished_at"] and "wrote" in row["message"]
    log = jobs.log_path().read_text(encoding="ascii")
    assert "backup start" in log and "backup end exit=0" in log

    status = {s["job"]: s for s in jobs.job_status()}
    assert status["backup"] == {**row_view(row), "schedule": "daily 20:00", "next_run": None}
    assert status["instruments"]["started_at"] is None


def row_view(row):
    return {k: row[k] for k in ("job", "started_at", "finished_at", "exit_code", "message")}


def test_failing_job_records_exit_1(bdir, monkeypatch):
    def boom():
        raise RuntimeError("disk full")

    monkeypatch.setitem(jobs.JOBS, "backup", jobs.Job("backup", boom, "daily 20:00"))
    assert jobs.run_job("backup") == 1
    row = runs()[-1]
    assert row["exit_code"] == 1 and row["message"] == "RuntimeError: disk full"


def test_unknown_job_exits_2(capsys):
    assert jobs.run_job("nope") == 2
    assert jobs_main.main(["nope"]) == 2
    assert jobs_main.main([]) == 2
    assert "unknown job" in capsys.readouterr().err


def test_job_status_lists_jobs_that_never_ran():
    empty = {"started_at": None, "finished_at": None, "exit_code": None, "message": None, "next_run": None}
    assert jobs.job_status() == [
        {"job": "instruments", "schedule": "daily 15:30", **empty},
        {"job": "calendar", "schedule": "daily 16:00", **empty},
        {"job": "backup", "schedule": "daily 20:00", **empty},
    ]


def test_migration_002_applied(tmp_path):
    with db.connect() as conn:
        versions = [r["version"] for r in conn.execute("SELECT version FROM schema_version ORDER BY version")]
    assert versions[:2] == [1, 2]
