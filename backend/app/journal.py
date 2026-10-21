"""Simple local trade journal + hit-rate stats (JSON file)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
JOURNAL_PATH = DATA_DIR / "journal.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> list[dict[str, Any]]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not JOURNAL_PATH.exists():
        return []
    try:
        raw = json.loads(JOURNAL_PATH.read_text(encoding="utf-8"))
        return raw if isinstance(raw, list) else []
    except Exception:  # noqa: BLE001
        return []


def _save(rows: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    JOURNAL_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def list_entries(limit: int = 100) -> list[dict[str, Any]]:
    rows = _load()
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return rows[:limit]


def add_entry(payload: dict[str, Any]) -> dict[str, Any]:
    rows = _load()
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
    rows.append(entry)
    _save(rows)
    return entry


def close_entry(
    entry_id: str,
    status: str,
    exit_price: float | None = None,
) -> dict[str, Any]:
    rows = _load()
    status = status.lower()
    if status not in ("win", "loss", "be", "skipped"):
        raise ValueError("status must be win|loss|be|skipped")
    for row in rows:
        if row.get("id") == entry_id:
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
            _save(rows)
            return row
    raise KeyError(f"entry {entry_id} not found")


def delete_entry(entry_id: str) -> bool:
    rows = _load()
    new = [r for r in rows if r.get("id") != entry_id]
    if len(new) == len(rows):
        return False
    _save(new)
    return True


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
