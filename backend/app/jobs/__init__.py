"""Scheduled jobs (WL-029): a registry, a runner and the run history.

Run one by name:  .venv\\Scripts\\python.exe -m app.jobs <job>
Task Scheduler starts it through scripts/jobs/<job>.bat (see register.ps1).

Add a job:
1. Write `app/jobs/<name>.py` with `run() -> str`; return a short ASCII summary,
   raise on failure.
2. Add it to JOBS below, with its local schedule for display.
3. Copy scripts/jobs/backup.bat to scripts/jobs/<name>.bat and change the job name.
4. Add a line to the job list at the top of scripts/jobs/register.ps1 and run it.

Every run appends one row to the job_runs table and lines to data/logs/jobs.log
(next to the db file).
"""

from __future__ import annotations

import subprocess
import sys
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .. import calendar_feed, db, instruments
from . import backup


@dataclass(frozen=True)
class Job:
    name: str
    run: Callable[[], str]
    schedule: str  # local time, as registered by scripts/jobs/register.ps1


JOBS: dict[str, Job] = {
    "instruments": Job("instruments", instruments.run, "daily 15:30"),
    "calendar": Job("calendar", calendar_feed.run, "daily 16:00"),
    "backup": Job("backup", backup.run, "daily 20:00"),
}

TASK_PATH = "\\CryptoChartAI\\"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def log_path() -> Path:
    return db.db_path().parent / "logs" / "jobs.log"


def _log(line: str) -> None:
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="ascii", errors="replace", newline="\n") as fh:
        fh.write(f"{_now()} {line}\n")


def _ascii(text: str, limit: int = 500) -> str:
    return " ".join(text.split()).encode("ascii", "replace").decode("ascii")[:limit]


def run_job(name: str) -> int:
    """Run one job; returns the process exit code (0 ok, 1 failed, 2 unknown job)."""
    job = JOBS.get(name)
    if job is None:
        print(f"unknown job {name!r}; known: {', '.join(sorted(JOBS))}", file=sys.stderr)
        return 2

    started = _now()
    _log(f"{name} start")
    run_id: int | None = None
    try:
        with db.connect() as conn:
            cur = conn.execute("INSERT INTO job_runs (job, started_at) VALUES (?, ?)", (name, started))
            run_id = cur.lastrowid
    except Exception as exc:  # noqa: BLE001
        _log(f"{name} could not record the run start: {_ascii(str(exc))}")

    try:
        message, code = _ascii(job.run() or "ok"), 0
    except Exception as exc:  # noqa: BLE001
        message, code = _ascii(f"{type(exc).__name__}: {exc}"), 1
        _log(f"{name} traceback: {_ascii(traceback.format_exc(), 2000)}")

    finished = _now()
    _log(f"{name} end exit={code} {message}")
    try:
        with db.connect() as conn:
            if run_id is None:
                conn.execute(
                    "INSERT INTO job_runs (job, started_at, finished_at, exit_code, message) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (name, started, finished, code, message),
                )
            else:
                conn.execute(
                    "UPDATE job_runs SET finished_at = ?, exit_code = ?, message = ? WHERE id = ?",
                    (finished, code, message, run_id),
                )
    except Exception as exc:  # noqa: BLE001
        _log(f"{name} could not record the run end: {_ascii(str(exc))}")
        code = code or 1
    print(f"{name}: exit={code} {message}")
    return code


def _next_run(name: str) -> str | None:
    """Next run time as Task Scheduler reports it, or None (not registered, not Windows)."""
    if sys.platform != "win32":
        return None
    try:
        proc = subprocess.run(  # noqa: S603
            ["schtasks", "/Query", "/TN", f"{TASK_PATH}{name}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    # "TaskName","Next Run Time","Status"
    parts = [p.strip('"') for p in proc.stdout.strip().splitlines()[0].split('","')] if proc.stdout.strip() else []
    if len(parts) < 2 or not parts[1] or parts[1].upper() in ("N/A", "DISABLED"):
        return None
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%d/%m/%Y %H:%M:%S", "%m/%d/%Y %H:%M:%S"):
        try:
            return datetime.strptime(parts[1], fmt).astimezone().isoformat(timespec="seconds")
        except ValueError:
            continue
    return parts[1]  # unknown locale format: pass the text through


def job_status() -> list[dict[str, Any]]:
    """Last run per registered job, plus the next scheduled run when known."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT job, started_at, finished_at, exit_code, message FROM job_runs r "
            "WHERE id = (SELECT MAX(id) FROM job_runs WHERE job = r.job)"
        ).fetchall()
    last = {r["job"]: r for r in rows}
    out = []
    for name, job in JOBS.items():
        r = last.get(name) or {}
        out.append(
            {
                "job": name,
                "schedule": job.schedule,
                "started_at": r.get("started_at"),
                "finished_at": r.get("finished_at"),
                "exit_code": r.get("exit_code"),
                "message": r.get("message"),
                "next_run": _next_run(name),
            }
        )
    return out
