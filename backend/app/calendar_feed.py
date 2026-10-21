"""Economic, earnings and Binance calendar (WL-039, earnings part of WL-045).

Named calendar_feed so it never shadows the stdlib `calendar` module.
All times are stored and returned in PKT (+05:00, no daylight saving).

Sources (free, no keys; each one optional, a failure is recorded, never raised):
- forexfactory: the weekly JSON feed (this week only; a next-week feed does not
  exist). USD events of every impact plus high-impact events of other countries.
  The feed has no `actual` values.
- nasdaq: the public earnings calendar, one request per day in the window. Only
  tickers that Binance lists (USD-M stock or ETF perps, or spot bStocks in the
  instruments table) are kept.
- binance: the public announcement list (new listings and delistings). The event
  date comes from the title when it carries one, else the release time is used.

Not covered: BNB quarterly burns and token unlocks have no free keyless feed.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from . import db

logger = logging.getLogger(__name__)

PKT = timezone(timedelta(hours=5))

FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
NASDAQ_URL = "https://api.nasdaq.com/api/calendar/earnings"
BINANCE_URL = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query"
BINANCE_ARTICLE = "https://www.binance.com/en/support/announcement/detail/{code}"
# Nasdaq refuses non-browser clients; a generic browser string, no personal data.
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}
BINANCE_CATALOGS = {48: "listing", 161: "delisting"}  # 48 also carries futures launches
_IMPACT = {"high": "high", "medium": "medium", "low": "low"}
_TITLE_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
# Not available without a key or a paid plan; listed so the API says so.
UNCOVERED = {
    "bnb_burn": "no free structured source for BNB burn dates",
    "token_unlocks": "free sources need an API key; none configured",
}

_refresh_lock = threading.Lock()
_PAUSE = 0.3  # seconds between the daily Nasdaq requests


# --- time helpers -----------------------------------------------------------------


def window(days: int = 7, now: datetime | None = None) -> tuple[datetime, datetime]:
    """Today 00:00 PKT up to (not including) the day after today + days."""
    now = (now or datetime.now(timezone.utc)).astimezone(PKT)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=days + 1)


def iso(dt: datetime) -> str:
    return dt.astimezone(PKT).isoformat(timespec="seconds")


def _us_eastern_offset(day: date) -> timedelta:
    """UTC offset of New York on `day` (DST from the 2nd Sunday of March to the 1st Sunday of November)."""
    try:
        from zoneinfo import ZoneInfo

        return datetime(day.year, day.month, day.day, 12, tzinfo=ZoneInfo("America/New_York")).utcoffset()
    except Exception:  # noqa: BLE001  (no tz database: apply the US rule by hand)
        march = date(day.year, 3, 8)
        dst_start = march + timedelta(days=(6 - march.weekday()) % 7)
        nov = date(day.year, 11, 1)
        dst_end = nov + timedelta(days=(6 - nov.weekday()) % 7)
        return timedelta(hours=-4 if dst_start <= day < dst_end else -5)


def eastern(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=timezone(_us_eastern_offset(day)))


def day_start_pkt(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=PKT)


def _blank(v: Any) -> Any:
    return None if v in (None, "") else v


# --- parsers (pure, tested with fixtures) -----------------------------------------


def parse_forexfactory(data: Any, start: datetime, end: datetime) -> tuple[list[dict], tuple[str, str] | None]:
    """Events in the window, and the time range the feed covers (for removals)."""
    events, latest = [], None
    for e in data if isinstance(data, list) else []:
        try:
            when = datetime.fromisoformat(str(e["date"]))
        except (KeyError, ValueError):
            continue
        latest = when if latest is None or when > latest else latest
        country = str(e.get("country") or "")
        impact_raw = str(e.get("impact") or "").lower()
        impact = _IMPACT.get(impact_raw)
        if country != "USD" and impact != "high":
            continue
        if not (start <= when < end):
            continue
        events.append({
            "source": "forexfactory", "kind": "macro", "title": str(e.get("title") or "").strip(),
            "starts_at": iso(when), "all_day": impact_raw == "holiday", "session": None,
            "impact": impact, "country": country or None, "ticker": "", "instrument_symbols": None,
            "forecast": _blank(e.get("forecast")), "previous": _blank(e.get("previous")),
            "actual": _blank(e.get("actual")), "url": None,
        })
    covered = (iso(start), iso(min(end, latest + timedelta(seconds=1)))) if latest else None
    return events, covered


def parse_nasdaq(day: date, data: Any, tickers: dict[str, list[str]]) -> list[dict]:
    rows = ((data or {}).get("data") or {}).get("rows") or []
    events = []
    for r in rows:
        sym = str(r.get("symbol") or "").upper()
        if sym not in tickers:
            continue
        code = str(r.get("time") or "")
        if code == "time-pre-market":
            when, session, all_day = eastern(day, 9, 30), "before_open", False  # by the 09:30 ET open
        elif code == "time-after-hours":
            when, session, all_day = eastern(day, 16, 0), "after_close", False  # after the 16:00 ET close
        else:
            when, session, all_day = day_start_pkt(day), None, True
        name = str(r.get("name") or sym).strip()
        events.append({
            "source": "nasdaq", "kind": "earnings", "title": f"{name} earnings",
            "starts_at": iso(when), "all_day": all_day, "session": session, "impact": None,
            "country": "US", "ticker": sym, "instrument_symbols": tickers[sym],
            "forecast": _blank(str(r.get("epsForecast") or "").strip()),
            "previous": _blank(str(r.get("lastYearEPS") or "").strip()), "actual": None,
            "url": f"https://www.nasdaq.com/market-activity/stocks/{sym.lower()}/earnings",
        })
    return events


def parse_binance(data: Any, start: datetime, end: datetime) -> list[dict]:
    catalogs = (((data or {}).get("data") or {}).get("catalogs")) or []
    events = []
    for cat in catalogs:
        if cat.get("catalogId") not in BINANCE_CATALOGS:
            continue
        for a in cat.get("articles") or []:
            title = str(a.get("title") or "").strip()
            dates = _TITLE_DATE.findall(title)
            if dates:
                try:
                    d = date.fromisoformat(dates[-1])
                except ValueError:
                    continue
                when, all_day = day_start_pkt(d), True
            elif a.get("releaseDate"):
                when, all_day = datetime.fromtimestamp(int(a["releaseDate"]) / 1000, tz=timezone.utc), False
            else:
                continue
            if not (start <= when < end):
                continue
            events.append({
                "source": "binance", "kind": "binance", "title": title, "starts_at": iso(when),
                "all_day": all_day, "session": None, "impact": None, "country": None, "ticker": "",
                "instrument_symbols": None, "forecast": None, "previous": None, "actual": None,
                "url": BINANCE_ARTICLE.format(code=a.get("code")) if a.get("code") else None,
            })
    return events


# --- instruments link ---------------------------------------------------------------


def binance_tickers() -> dict[str, list[str]]:
    """US-style ticker -> TradingView symbols Binance lists for it (perps and bStocks)."""
    out: dict[str, list[str]] = defaultdict(list)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT symbol, market, type, base, name FROM instruments WHERE status = 'trading'"
            " AND (type IN ('stock', 'etf') OR name LIKE '%(bStocks)') ORDER BY market DESC, symbol"
        ).fetchall()
    for r in rows:
        base = str(r["base"] or "").upper()
        if r["market"] == "usdm":
            out[base].append(f"BINANCE:{r['symbol']}.P")
        else:
            ticker = base[:-1] if base.endswith("B") and len(base) > 1 else base  # NVDAB -> NVDA
            out[ticker].append(f"BINANCE:{r['symbol']}")
    return dict(out)


# --- refresh ------------------------------------------------------------------------


def _fetch_json(client: httpx.Client, url: str, **kwargs: Any) -> Any:
    r = client.get(url, **kwargs)
    r.raise_for_status()
    return r.json()


def _error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"[:300]


def refresh(days: int = 7, now: datetime | None = None) -> dict[str, Any]:
    """Fetch every source, upsert, remove vanished future rows. Never raises."""
    with _refresh_lock:
        try:
            return _refresh(days, now)
        except Exception as exc:  # noqa: BLE001
            logger.exception("calendar refresh failed")
            return {"ok": False, "error": _error(exc), "sources": {}, "counts": {}}


def _refresh(days: int, now: datetime | None) -> dict[str, Any]:
    start, end = window(days, now)
    collected: dict[str, list[dict]] = {}
    covered: dict[str, tuple[str, str] | None] = {}
    status: dict[str, dict[str, Any]] = {}

    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        # ForexFactory: one request
        try:
            evs, rng = parse_forexfactory(_fetch_json(client, FF_URL), start, end)
            collected["forexfactory"], covered["forexfactory"] = evs, rng
            status["forexfactory"] = {"available": True, "error": None}
        except Exception as exc:  # noqa: BLE001
            status["forexfactory"] = {"available": False, "error": _error(exc)}

        # Nasdaq: one request per day; removals only when every day answered
        try:
            tickers = binance_tickers()
        except Exception as exc:  # noqa: BLE001
            tickers, status["nasdaq"] = {}, {"available": False, "error": f"instruments: {_error(exc)}"}
        if "nasdaq" not in status:
            evs, failures = [], []
            day = start.date()
            while day_start_pkt(day) < end:
                try:
                    data = _fetch_json(client, NASDAQ_URL, params={"date": day.isoformat()},
                                       headers=BROWSER_HEADERS)
                    evs += [e for e in parse_nasdaq(day, data, tickers) if start <= datetime.fromisoformat(e["starts_at"]) < end]
                except Exception as exc:  # noqa: BLE001
                    failures.append(f"{day.isoformat()} {_error(exc)}")
                day += timedelta(days=1)
                time.sleep(_PAUSE)  # polite spacing between the daily requests
            total_days = (end.date() - start.date()).days
            if len(failures) < total_days:
                collected["nasdaq"] = evs
                covered["nasdaq"] = (iso(start), iso(end)) if not failures else None
            if not tickers:
                failures.append("no Binance stock or ETF instruments in the catalogue yet")
            status["nasdaq"] = {"available": len(failures) < total_days,
                                "error": "; ".join(failures)[:300] or None}

        # Binance announcements: one request, never removes (the list only shows the latest)
        try:
            data = _fetch_json(client, BINANCE_URL, params={"type": 1, "pageNo": 1, "pageSize": 20})
            collected["binance"], covered["binance"] = parse_binance(data, start, end), None
            status["binance"] = {"available": True, "error": None}
        except Exception as exc:  # noqa: BLE001
            status["binance"] = {"available": False, "error": _error(exc)}

    stamp = datetime.now(timezone.utc).isoformat()
    counts: dict[str, dict[str, int]] = {}
    removed = 0
    with db.connect() as conn:
        for source, evs in collected.items():
            for e in evs:
                conn.execute(
                    "INSERT INTO calendar_events (source, kind, title, starts_at, all_day, session, impact,"
                    " country, ticker, instrument_symbols, forecast, previous, actual, url, fetched_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                    " ON CONFLICT (source, kind, title, starts_at, ticker) DO UPDATE SET"
                    " all_day = excluded.all_day, session = excluded.session, impact = excluded.impact,"
                    " country = excluded.country, instrument_symbols = excluded.instrument_symbols,"
                    " forecast = excluded.forecast, previous = excluded.previous,"
                    " actual = COALESCE(excluded.actual, calendar_events.actual), url = excluded.url,"
                    " fetched_at = excluded.fetched_at",
                    (e["source"], e["kind"], e["title"], e["starts_at"], int(bool(e["all_day"])),
                     e["session"], e["impact"], e["country"], e["ticker"],
                     json.dumps(e["instrument_symbols"]) if e["instrument_symbols"] else None,
                     e["forecast"], e["previous"], e["actual"], e["url"], stamp),
                )
            counts[source] = dict(Counter(e["kind"] for e in evs))
            rng = covered.get(source)
            if rng:
                # Rescheduled or cancelled: future rows of this source the feed no longer lists
                lo = max(rng[0], iso(now or datetime.now(timezone.utc)))
                cur = conn.execute(
                    "DELETE FROM calendar_events WHERE source = ? AND starts_at >= ? AND starts_at < ?"
                    " AND fetched_at <> ?",
                    (source, lo, rng[1], stamp),
                )
                removed += cur.rowcount
        for name, st in status.items():
            conn.execute(
                "INSERT INTO calendar_sources (name, available, error, events, fetched_at) VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT (name) DO UPDATE SET available = excluded.available, error = excluded.error,"
                " events = excluded.events, fetched_at = excluded.fetched_at",
                (name, int(st["available"]), st["error"], len(collected.get(name, [])), stamp),
            )
        for name, why in UNCOVERED.items():
            conn.execute(
                "INSERT INTO calendar_sources (name, available, error, events, fetched_at)"
                " VALUES (?, 0, ?, 0, ?) ON CONFLICT (name) DO UPDATE SET error = excluded.error,"
                " fetched_at = excluded.fetched_at",
                (name, why, stamp),
            )

    return {
        "ok": any(s["available"] for s in status.values()),
        "window": [iso(start), iso(end)],
        "sources": status,
        "counts": counts,
        "removed": removed,
    }


def run() -> str:
    """Job entry point (python -m app.jobs calendar)."""
    res = refresh()
    if not res.get("ok"):
        raise RuntimeError(res.get("error") or f"no calendar source answered: {res.get('sources')}")
    parts = [f"{src}:" + ",".join(f"{k}={v}" for k, v in sorted(kinds.items())) for src, kinds in res["counts"].items()]
    down = [k for k, v in res["sources"].items() if not v["available"]]
    msg = " ".join(parts) + f" removed={res['removed']}" + (f" down={','.join(down)}" if down else "")
    return msg.encode("ascii", "replace").decode("ascii")


# --- read side ----------------------------------------------------------------------


def _row(r: dict[str, Any]) -> dict[str, Any]:
    syms = r.get("instrument_symbols")
    return {
        "id": r["id"], "source": r["source"], "kind": r["kind"], "title": r["title"],
        "starts_at": r["starts_at"], "all_day": bool(r["all_day"]), "session": r["session"],
        "impact": r["impact"], "country": r["country"], "ticker": r["ticker"] or None,
        "instrument_symbols": json.loads(syms) if syms else [],
        "forecast": r["forecast"], "previous": r["previous"], "actual": r["actual"],
        "url": r["url"], "fetched_at": r["fetched_at"],
    }


def list_events(days: int = 7, kind: str | None = None, now: datetime | None = None) -> list[dict[str, Any]]:
    start, end = window(max(0, min(days, 30)), now)
    sql = "SELECT * FROM calendar_events WHERE starts_at >= ? AND starts_at < ?"
    params: list[Any] = [iso(start), iso(end)]
    if kind:
        sql += " AND kind = ?"
        params.append(kind)
    with db.connect() as conn:
        rows = conn.execute(sql + " ORDER BY starts_at, id", params).fetchall()
    return [_row(r) for r in rows]


def source_status() -> list[dict[str, Any]]:
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM calendar_sources ORDER BY name").fetchall()
    return [
        {"name": r["name"], "available": None if r["available"] is None else bool(r["available"]),
         "error": r["error"], "events": r["events"], "fetched_at": r["fetched_at"]}
        for r in rows
    ]


def upcoming_high_impact(hours: int = 24, now: datetime | None = None, limit: int = 5) -> list[dict[str, Any]]:
    """High-impact macro events from now to now + hours, short form for the snapshot."""
    now = now or datetime.now(timezone.utc)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT title, starts_at, country, impact, forecast, previous FROM calendar_events"
            " WHERE kind = 'macro' AND impact = 'high' AND starts_at >= ? AND starts_at < ?"
            " ORDER BY starts_at LIMIT ?",
            (iso(now), iso(now + timedelta(hours=hours)), limit),
        ).fetchall()
    return [{k: v for k, v in r.items() if v is not None} for r in rows]


def refresh_in_background_if_empty() -> bool:
    """Startup hook: no events from today onward means fetch once, off the request path."""
    try:
        start, _ = window(0)
        with db.connect() as conn:
            n = conn.execute("SELECT COUNT(*) AS n FROM calendar_events WHERE starts_at >= ?",
                             (iso(start),)).fetchone()["n"]
    except Exception:  # noqa: BLE001
        logger.exception("calendar count failed")
        return False
    if n:
        return False
    threading.Thread(target=refresh, name="calendar-refresh", daemon=True).start()
    return True
