"""Simple local trade journal + hit-rate stats (SQLite table `journal`, see db.py)."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from .db import JOURNAL_COLUMNS, connect, from_db, insert_row, update_row

_TABLE = "journal"
_ORDER = "ORDER BY COALESCE(created_at, '') DESC, seq ASC"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> list[dict[str, Any]]:
    """All rows in insertion order."""
    with connect() as conn:
        rows = conn.execute(f"SELECT * FROM {_TABLE} ORDER BY seq").fetchall()  # noqa: S608
    return [from_db(_TABLE, r) for r in rows]


def _get(conn: sqlite3.Connection, entry_id: str) -> dict[str, Any] | None:
    row = conn.execute(f"SELECT * FROM {_TABLE} WHERE id = ?", (entry_id,)).fetchone()  # noqa: S608
    return from_db(_TABLE, row)


def list_entries(limit: int = 100) -> list[dict[str, Any]]:
    # Newest first; equal timestamps keep insertion order (as the old stable sort did).
    with connect() as conn:
        if limit >= 0:
            rows = conn.execute(f"SELECT * FROM {_TABLE} {_ORDER} LIMIT ?", (limit,)).fetchall()  # noqa: S608
        else:
            rows = conn.execute(f"SELECT * FROM {_TABLE} {_ORDER}").fetchall()[:limit]  # noqa: S608
    return [from_db(_TABLE, r) for r in rows]


def add_entry(payload: dict[str, Any]) -> dict[str, Any]:
    entry = {
        "id": str(uuid.uuid4())[:8],
        "created_at": _now(),
        "symbol": str(payload.get("symbol") or "").upper(),
        "timeframe": payload.get("timeframe") or "1h",
        "side": payload.get("side") or "Buy",  # Buy / Sell
        "setup": payload.get("setup"),
        "entry": payload.get("entry"),
        "stop_loss": payload.get("stop_loss"),
        "take_profit": payload.get("take_profit"),
        "confluence": payload.get("confluence"),
        "notes": payload.get("notes") or "",
        "status": "open",  # open | win | loss | be | skipped
        "exit_price": None,
        "closed_at": None,
        "r_multiple": None,
    }
    with connect() as conn:
        for _ in range(5):
            try:
                insert_row(conn, _TABLE, JOURNAL_COLUMNS, entry)
                break
            except sqlite3.IntegrityError:
                entry["id"] = str(uuid.uuid4())[:8]  # 8-char id collision, try another
        else:
            raise RuntimeError("could not allocate a journal id")
    return entry


def close_entry(
    entry_id: str,
    status: str,
    exit_price: float | None = None,
) -> dict[str, Any]:
    status = status.lower()
    if status not in ("win", "loss", "be", "skipped"):
        raise ValueError("status must be win|loss|be|skipped")
    with connect() as conn:
        row = _get(conn, entry_id)
        if row is None:
            raise KeyError(f"entry {entry_id} not found")
        row["status"] = status
        row["closed_at"] = _now()
        if exit_price is not None:
            row["exit_price"] = exit_price
        # R-multiple if we have entry/SL
        entry = row.get("entry")
        sl = row.get("stop_loss")
        if (
            exit_price is not None
            and entry is not None
            and sl is not None
            and float(entry) != float(sl)
        ):
            risk = abs(float(entry) - float(sl))
            side = (row.get("side") or "Buy").lower()
            if side == "sell":
                pnl = float(entry) - float(exit_price)
            else:
                pnl = float(exit_price) - float(entry)
            row["r_multiple"] = round(pnl / risk, 2) if risk else None
        update_row(conn, _TABLE, JOURNAL_COLUMNS, row)
    return row


def delete_entry(entry_id: str) -> bool:
    with connect() as conn:
        cur = conn.execute(f"DELETE FROM {_TABLE} WHERE id = ?", (entry_id,))  # noqa: S608
    return cur.rowcount > 0


def stats() -> dict[str, Any]:
    rows = _load()
    closed = [r for r in rows if r.get("status") in ("win", "loss", "be")]
    wins = [r for r in closed if r.get("status") == "win"]
    losses = [r for r in closed if r.get("status") == "loss"]
    be = [r for r in closed if r.get("status") == "be"]
    open_n = sum(1 for r in rows if r.get("status") == "open")

    hit = (len(wins) / len(closed)) if closed else None
    rs = [float(r["r_multiple"]) for r in closed if r.get("r_multiple") is not None]
    avg_r = round(sum(rs) / len(rs), 2) if rs else None

    by_setup: dict[str, dict[str, Any]] = {}
    for r in closed:
        key = r.get("setup") or "unknown"
        bucket = by_setup.setdefault(key, {"n": 0, "wins": 0})
        bucket["n"] += 1
        if r.get("status") == "win":
            bucket["wins"] += 1
    for k, v in by_setup.items():
        v["hit_rate"] = round(v["wins"] / v["n"], 2) if v["n"] else None

    return {
        "total": len(rows),
        "open": open_n,
        "closed": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": len(be),
        "hit_rate": round(hit, 3) if hit is not None else None,
        "avg_r": avg_r,
        "by_setup": by_setup,
    }
