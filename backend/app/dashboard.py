"""Signal performance dashboard aggregates (WL-051)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .signals import _load
from .strategies import list_strategies


_MIN_RELIABLE = 5


def _sid(row: dict[str, Any]) -> str:
    raw = row.get("strategy_id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().lower()
    return "desk"


def _parse_day(iso: str | None) -> str | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).date().isoformat()
    except Exception:  # noqa: BLE001
        return None


def _label_map() -> dict[str, str]:
    return {s["id"]: s["label"] for s in list_strategies()}


def _bucket_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    closed = [r for r in rows if r.get("status") in ("win", "loss", "expired")]
    wins = [r for r in closed if r.get("status") == "win"]
    losses = [r for r in closed if r.get("status") == "loss"]
    expired = [r for r in closed if r.get("status") == "expired"]
    open_n = sum(1 for r in rows if r.get("status") == "open")
    decided = wins + losses
    hit = (len(wins) / len(decided)) if decided else None
    rs = [float(r["r_multiple"]) for r in closed if r.get("r_multiple") is not None]
    avg_r = round(sum(rs) / len(rs), 2) if rs else None
    total_r = round(sum(rs), 2) if rs else 0.0
    return {
        "n": len(rows),
        "open": open_n,
        "wins": len(wins),
        "losses": len(losses),
        "expired": len(expired),
        "decided": len(decided),
        "hit_rate": round(hit, 3) if hit is not None else None,
        "avg_r": avg_r,
        "total_r": total_r,
        "reliable": len(decided) >= _MIN_RELIABLE,
    }


def build_dashboard() -> dict[str, Any]:
    rows = _load()
    labels = _label_map()
    overall = _bucket_stats(rows)

    by_id: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_id.setdefault(_sid(r), []).append(r)

    by_strategy: list[dict[str, Any]] = []
    for sid, group in sorted(by_id.items(), key=lambda kv: labels.get(kv[0], kv[0])):
        stats = _bucket_stats(group)
        by_strategy.append(
            {
                "id": sid,
                "label": labels.get(sid, sid),
                **stats,
            }
        )
    # Also list catalog strategies with zero signals so the UI can show empty bars.
    seen = {b["id"] for b in by_strategy}
    for s in list_strategies():
        if s["id"] not in seen:
            by_strategy.append(
                {
                    "id": s["id"],
                    "label": s["label"],
                    "n": 0,
                    "open": 0,
                    "wins": 0,
                    "losses": 0,
                    "expired": 0,
                    "decided": 0,
                    "hit_rate": None,
                    "avg_r": None,
                    "total_r": 0.0,
                    "reliable": False,
                }
            )
    by_strategy.sort(key=lambda b: (-(b["n"] or 0), b["label"]))

    reliable = [b for b in by_strategy if b["reliable"] and b["hit_rate"] is not None]
    best = max(reliable, key=lambda b: (b["hit_rate"], b["avg_r"] or 0))["id"] if reliable else None
    worst = min(reliable, key=lambda b: (b["hit_rate"], b["avg_r"] or 0))["id"] if reliable else None

    # Equity curve: closed signals in time order, cumulative R overall and per strategy.
    closed_timed: list[tuple[str, dict[str, Any]]] = []
    for r in rows:
        if r.get("status") not in ("win", "loss", "expired"):
            continue
        if r.get("r_multiple") is None:
            continue
        day = _parse_day(r.get("verified_at") or r.get("created_at"))
        if not day:
            continue
        closed_timed.append((day, r))
    closed_timed.sort(key=lambda x: (x[0], x[1].get("created_at") or ""))

    cum = 0.0
    cum_by: dict[str, float] = {}
    equity_by_day: dict[str, dict[str, Any]] = {}
    for day, r in closed_timed:
        rm = float(r["r_multiple"])
        cum += rm
        sid = _sid(r)
        cum_by[sid] = cum_by.get(sid, 0.0) + rm
        point = equity_by_day.setdefault(
            day,
            {"date": day, "cumulative_r": 0.0, "cumulative_r_by_strategy": {}},
        )
        point["cumulative_r"] = round(cum, 2)
        point["cumulative_r_by_strategy"] = {
            k: round(v, 2) for k, v in cum_by.items()
        }
    equity_curve = [equity_by_day[d] for d in sorted(equity_by_day)]

    # Volume last 30 days (by created_at).
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=29)
    volume_map = {(start + timedelta(days=i)).isoformat(): 0 for i in range(30)}
    for r in rows:
        day = _parse_day(r.get("created_at"))
        if day and day in volume_map:
            volume_map[day] += 1
    volume_by_day = [{"date": d, "count": volume_map[d]} for d in sorted(volume_map)]

    outcomes_by_strategy = [
        {
            "id": b["id"],
            "label": b["label"],
            "wins": b["wins"],
            "losses": b["losses"],
            "expired": b["expired"],
        }
        for b in by_strategy
        if b["n"] > 0
    ]

    return {
        "overall": overall,
        "by_strategy": by_strategy,
        "best": best,
        "worst": worst,
        "best_label": labels.get(best) if best else None,
        "worst_label": labels.get(worst) if worst else None,
        "min_reliable": _MIN_RELIABLE,
        "equity_curve": equity_curve,
        "volume_by_day": volume_by_day,
        "outcomes_by_strategy": outcomes_by_strategy,
    }
