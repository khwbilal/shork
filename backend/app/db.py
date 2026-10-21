"""SQLite storage (WL-028): connection helper, migrations and the one-time JSON import.

Stdlib sqlite3 only. Every call opens its own connection, so FastAPI worker
threads never share one. The file is backend/data/app.db unless DB_PATH is set.

Add a migration: drop `NNN_name.sql` into app/migrations/ with the next number.
It runs once, in order, at startup (or on the first connect), inside a
transaction, and is recorded in schema_version. Write it with IF NOT EXISTS so a
second process starting at the same moment cannot fail on it.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import get_settings

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_DB_PATH = DATA_DIR / "app.db"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

_MIGRATION_RE = re.compile(r"^(\d+)_([\w-]+)\.sql$")
_ready: set[str] = set()
_ready_lock = threading.Lock()

# Column lists per table, in the order the API dicts use. seq is internal.
JOURNAL_COLUMNS = (
    "id", "created_at", "symbol", "timeframe", "side", "setup", "entry", "stop_loss",
    "take_profit", "confluence", "notes", "status", "exit_price", "closed_at", "r_multiple",
)
SIGNAL_COLUMNS = (
    "id", "created_at", "symbol", "timeframe", "bias", "entry", "stop_loss", "take_profit",
    "price_at_signal", "setup", "trade_allowed", "confluence", "confidence", "status",
    "outcome", "verified_at", "bars_checked", "hit_price", "hit_at", "r_multiple", "notes",
)
BOOL_COLUMNS = {"signals": ("trade_allowed",)}


def db_path() -> Path:
    """DB_PATH from the env or .env, else backend/data/app.db."""
    configured = (get_settings().db_path or "").strip()
    return Path(configured).expanduser().resolve() if configured else DEFAULT_DB_PATH


def _dict_factory(cursor: sqlite3.Cursor, row: Sequence[Any]) -> dict[str, Any]:
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


def _open(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = _dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrations() -> list[tuple[int, str, Path]]:
    found = []
    for p in MIGRATIONS_DIR.glob("*.sql"):
        m = _MIGRATION_RE.match(p.name)
        if m:
            found.append((int(m.group(1)), m.group(2), p))
    return sorted(found)


def migrate(path: Path | None = None) -> list[int]:
    """Apply pending migrations in order; returns the versions applied now."""
    path = path or db_path()
    conn = _open(path)
    applied_now: list[int] = []
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_version ("
            "version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)"
        )
        conn.commit()
        done = {r["version"] for r in conn.execute("SELECT version FROM schema_version")}
        for version, name, file in _migrations():
            if version in done:
                continue
            sql = file.read_text(encoding="utf-8")
            now = datetime.now(timezone.utc).isoformat()
            # executescript runs the whole file plus the version row as one transaction
            conn.executescript(
                f"BEGIN IMMEDIATE;\n{sql}\n;"
                f"INSERT OR IGNORE INTO schema_version (version, name, applied_at) "
                f"VALUES ({version}, '{name}', '{now}');\nCOMMIT;"
            )
            applied_now.append(version)
            logger.info("db migration %03d_%s applied to %s", version, name, path)
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()
    return applied_now


def _ensure_ready(path: Path) -> None:
    key = str(path)
    if key in _ready:
        return
    with _ready_lock:
        if key not in _ready:
            migrate(path)
            _ready.add(key)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """One connection per call: commit on success, roll back on error, always close."""
    path = db_path()
    _ensure_ready(path)
    conn = _open(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --- small repository helpers -------------------------------------------------


def to_db(value: Any) -> Any:
    """Booleans as 0/1; dicts and lists as JSON text."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def from_db(table: str, row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    row.pop("seq", None)
    for col in BOOL_COLUMNS.get(table, ()):
        if row.get(col) is not None:
            row[col] = bool(row[col])
    return row


def insert_row(conn: sqlite3.Connection, table: str, columns: Sequence[str], row: dict[str, Any]) -> None:
    cols = ", ".join(columns)
    marks = ", ".join("?" for _ in columns)
    conn.execute(
        f"INSERT INTO {table} ({cols}) VALUES ({marks})",  # noqa: S608 (names are module constants)
        [to_db(row.get(c)) for c in columns],
    )


def update_row(conn: sqlite3.Connection, table: str, columns: Sequence[str], row: dict[str, Any]) -> None:
    sets = ", ".join(f"{c} = ?" for c in columns if c != "id")
    conn.execute(
        f"UPDATE {table} SET {sets} WHERE id = ?",  # noqa: S608 (names are module constants)
        [to_db(row.get(c)) for c in columns if c != "id"] + [row["id"]],
    )


# --- one-time import of the old JSON files -------------------------------------

_IMPORTS = (("journal.json", "journal", JOURNAL_COLUMNS), ("signals.json", "signals", SIGNAL_COLUMNS))


def _imported_name(src: Path) -> Path:
    target = src.with_name(src.name + ".imported")
    n = 2
    while target.exists():
        target = src.with_name(f"{src.name}.imported.{n}")
        n += 1
    return target


def import_json_files() -> dict[str, int]:
    """Import journal.json / signals.json from the db's folder once, then rename them.

    Rows whose id is already in the db are skipped, so a rerun is harmless.
    A file that does not parse is left in place and logged.
    """
    path = db_path()
    counts: dict[str, int] = {}
    for filename, table, columns in _IMPORTS:
        src = path.parent / filename
        if not src.exists():
            continue
        try:
            rows = json.loads(src.read_text(encoding="utf-8"))
            if not isinstance(rows, list):
                raise ValueError("top level is not a list")
        except Exception as exc:  # noqa: BLE001
            logger.warning("db import skipped %s: %s", src, exc)
            continue
        added = 0
        with connect() as conn:
            for raw in rows:
                if not isinstance(raw, dict) or not raw.get("id"):
                    continue
                unknown = set(raw) - set(columns)
                if unknown:
                    logger.warning("db import %s: dropping unknown keys %s", filename, sorted(unknown))
                cur = conn.execute(f"SELECT 1 FROM {table} WHERE id = ?", (raw["id"],))  # noqa: S608
                if cur.fetchone():
                    continue
                insert_row(conn, table, columns, raw)
                added += 1
        target = _imported_name(src)
        src.rename(target)
        counts[table] = added
        logger.info("db import: %d new %s rows from %s, file renamed to %s", added, table, src.name, target.name)
    return counts


def init_db() -> dict[str, int]:
    """Startup hook: migrate, then import any old JSON files."""
    _ensure_ready(db_path())
    return import_json_files()
