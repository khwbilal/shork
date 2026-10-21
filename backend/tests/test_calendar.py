"""calendar_feed: parsers, PKT conversion, refresh with stubbed HTTP, API, snapshot field."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import pytest

from app import calendar_feed as cf
from app import db, main, market

NOW = datetime(2026, 10, 21, 7, 0, tzinfo=timezone.utc)  # 12:00 PKT, Wednesday
START, END = cf.window(7, NOW)

FF = [
    {"title": "CPI m/m", "country": "USD", "date": "2026-10-22T08:30:00-04:00", "impact": "High",
     "forecast": "0.3%", "previous": "0.4%"},
    {"title": "Unemployment Claims", "country": "USD", "date": "2026-10-23T08:30:00-04:00", "impact": "Medium",
     "forecast": "", "previous": "230K"},
    {"title": "German ifo", "country": "EUR", "date": "2026-10-22T04:00:00-04:00", "impact": "Low",
     "forecast": "", "previous": ""},
    {"title": "ECB Rate Decision", "country": "EUR", "date": "2026-10-23T08:15:00-04:00", "impact": "High",
     "forecast": "2.0%", "previous": "2.0%"},
    {"title": "Bank Holiday", "country": "USD", "date": "2026-10-24T00:00:00-04:00", "impact": "Holiday",
     "forecast": "", "previous": ""},
    {"title": "Old item", "country": "USD", "date": "2026-10-19T10:00:00-04:00", "impact": "High",
     "forecast": "", "previous": ""},
]


def nasdaq_day(rows):
    return {"data": {"asOf": "x", "rows": rows}}


NASDAQ = {
    "2026-10-22": nasdaq_day([
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "time": "time-after-hours",
         "epsForecast": "$1.10", "lastYearEPS": "$0.81"},
        {"symbol": "PG", "name": "Procter & Gamble", "time": "time-pre-market", "epsForecast": "$1.89"},
        {"symbol": "MU", "name": "Micron Technology", "time": "time-pre-market", "epsForecast": "$2.00"},
    ]),
    "2026-10-23": nasdaq_day([
        {"symbol": "SPY", "name": "SPDR", "time": "time-not-supplied", "epsForecast": ""},
    ]),
}

BINANCE = {"data": {"catalogs": [
    {"catalogId": 48, "articles": [
        {"code": "abc", "title": "Binance Futures Will Launch FOOUSDT Perpetual (2026-10-24)",
         "releaseDate": 1792000000000},
        {"code": "def", "title": "Binance Will List BAR (BAR)",
         "releaseDate": int(datetime(2026, 10, 21, 8, 0, tzinfo=timezone.utc).timestamp() * 1000)},
        {"code": "old", "title": "Old listing (2026-10-01)", "releaseDate": 1790000000000},
    ]},
    {"catalogId": 161, "articles": [
        {"code": "ghi", "title": "Binance Will Delist EPIC, QUICK on 2026-10-28", "releaseDate": 1792000000000},
    ]},
    {"catalogId": 93, "articles": [{"code": "z", "title": "Trading competition (2026-10-22)"}]},
]}}


class Http:
    """Stub for calendar_feed._fetch_json: canned data per source, or an exception."""

    def __init__(self):
        self.ff, self.nasdaq, self.binance = list(FF), dict(NASDAQ), BINANCE
        self.calls = []

    def __call__(self, _client, url, params=None, headers=None):
        self.calls.append(url)
        if url == cf.FF_URL:
            value = self.ff
        elif url == cf.NASDAQ_URL:
            assert "Mozilla" in headers["User-Agent"]
            value = self.nasdaq if isinstance(self.nasdaq, Exception) else self.nasdaq.get(
                params["date"], nasdaq_day(None))
        else:
            value = self.binance
        if isinstance(value, Exception):
            raise value
        return value


@pytest.fixture
def http(monkeypatch):
    stub = Http()
    monkeypatch.setattr(cf, "_fetch_json", stub)
    monkeypatch.setattr(cf, "_PAUSE", 0)
    return stub


@pytest.fixture
def listed():
    with db.connect() as conn:
        for sym, market_, typ, base, name in [
            ("NVDAUSDT", "usdm", "stock", "NVDA", "NVIDIA CORP"),
            ("SPYUSDT", "usdm", "etf", "SPY", "SPDR S&P 500 ETF Trust"),
            ("NVDABUSDT", "spot", "crypto", "NVDAB", "NVIDIA (bStocks)"),
            ("MUBUSDT", "spot", "crypto", "MUB", "Micron Technology (bStocks)"),
            ("BTCUSDT", "spot", "crypto", "BTC", "Bitcoin"),
        ]:
            conn.execute(
                "INSERT INTO instruments (symbol, market, type, base, quote, name, status, first_seen, updated_at)"
                " VALUES (?, ?, ?, ?, 'USDT', ?, 'trading', 'x', 'x')", (sym, market_, typ, base, name))


def events():
    with db.connect() as conn:
        return conn.execute("SELECT * FROM calendar_events ORDER BY starts_at, id").fetchall()


# --- pure parts ---------------------------------------------------------------------


def test_window_is_today_pkt_plus_days():
    assert cf.iso(START) == "2026-10-21T00:00:00+05:00"
    assert cf.iso(END) == "2026-10-29T00:00:00+05:00"
    late = datetime(2026, 10, 21, 20, 30, tzinfo=timezone.utc)  # 01:30 PKT on the 22nd
    assert cf.iso(cf.window(7, late)[0]) == "2026-10-22T00:00:00+05:00"


def test_eastern_to_pkt_with_dst():
    assert cf.iso(cf.eastern(date(2026, 10, 22), 9, 30)) == "2026-10-22T18:30:00+05:00"  # EDT
    assert cf.iso(cf.eastern(date(2026, 11, 3), 9, 30)) == "2026-11-03T19:30:00+05:00"  # EST
    assert cf.iso(cf.eastern(date(2026, 10, 22), 16, 0)) == "2026-10-23T01:00:00+05:00"


def test_parse_forexfactory():
    evs, covered = cf.parse_forexfactory(FF, START, END)
    titles = [e["title"] for e in evs]
    assert titles == ["CPI m/m", "Unemployment Claims", "ECB Rate Decision", "Bank Holiday"]
    cpi = evs[0]
    assert cpi["starts_at"] == "2026-10-22T17:30:00+05:00" and cpi["impact"] == "high"
    assert cpi["forecast"] == "0.3%" and cpi["actual"] is None and cpi["kind"] == "macro"
    assert evs[1]["forecast"] is None  # blank becomes None
    holiday = evs[3]
    assert holiday["all_day"] is True and holiday["impact"] is None
    assert covered == ("2026-10-21T00:00:00+05:00", "2026-10-24T09:00:01+05:00")


def test_parse_nasdaq_keeps_binance_tickers_only():
    tickers = {"NVDA": ["BINANCE:NVDAUSDT.P", "BINANCE:NVDABUSDT"], "MU": ["BINANCE:MUBUSDT"]}
    evs = cf.parse_nasdaq(date(2026, 10, 22), NASDAQ["2026-10-22"], tickers)
    assert [e["ticker"] for e in evs] == ["NVDA", "MU"]
    nvda, mu = evs
    assert nvda["session"] == "after_close" and nvda["starts_at"] == "2026-10-23T01:00:00+05:00"
    assert nvda["forecast"] == "$1.10" and nvda["previous"] == "$0.81"
    assert nvda["instrument_symbols"] == tickers["NVDA"] and nvda["title"] == "NVIDIA Corporation earnings"
    assert mu["session"] == "before_open" and mu["starts_at"] == "2026-10-22T18:30:00+05:00"
    spy = cf.parse_nasdaq(date(2026, 10, 23), NASDAQ["2026-10-23"], {"SPY": ["BINANCE:SPYUSDT.P"]})[0]
    assert spy["all_day"] is True and spy["session"] is None and spy["starts_at"] == "2026-10-23T00:00:00+05:00"
    assert spy["forecast"] is None
    assert cf.parse_nasdaq(date(2026, 10, 24), nasdaq_day(None), tickers) == []


def test_parse_binance():
    evs = cf.parse_binance(BINANCE, START, END)
    by_title = {e["title"]: e for e in evs}
    assert set(by_title) == {"Binance Futures Will Launch FOOUSDT Perpetual (2026-10-24)",
                             "Binance Will List BAR (BAR)", "Binance Will Delist EPIC, QUICK on 2026-10-28"}
    launch = by_title["Binance Futures Will Launch FOOUSDT Perpetual (2026-10-24)"]
    assert launch["all_day"] is True and launch["starts_at"] == "2026-10-24T00:00:00+05:00"
    assert launch["url"].endswith("/abc") and launch["kind"] == "binance"
    listing = by_title["Binance Will List BAR (BAR)"]  # no date in the title: release time
    assert listing["all_day"] is False and listing["starts_at"] == "2026-10-21T13:00:00+05:00"


def test_binance_tickers_includes_bstocks(listed):
    t = cf.binance_tickers()
    assert t["NVDA"] == ["BINANCE:NVDAUSDT.P", "BINANCE:NVDABUSDT"]
    assert t["MU"] == ["BINANCE:MUBUSDT"] and t["SPY"] == ["BINANCE:SPYUSDT.P"]
    assert "BTC" not in t


# --- refresh ------------------------------------------------------------------------


def test_refresh_stores_everything(http, listed):
    res = cf.refresh(now=NOW)
    assert res["ok"] is True
    assert res["counts"] == {"forexfactory": {"macro": 4}, "nasdaq": {"earnings": 3},
                             "binance": {"binance": 3}}
    assert all(s["available"] for s in res["sources"].values())
    assert http.calls.count(cf.NASDAQ_URL) == 8 and http.calls.count(cf.FF_URL) == 1
    rows = events()
    assert len(rows) == 10
    nvda = next(r for r in rows if r["ticker"] == "NVDA")
    assert json.loads(nvda["instrument_symbols"]) == ["BINANCE:NVDAUSDT.P", "BINANCE:NVDABUSDT"]
    status = {s["name"]: s for s in cf.source_status()}
    assert status["forexfactory"]["available"] is True and status["forexfactory"]["events"] == 4
    assert status["bnb_burn"]["available"] is False and "no free" in status["bnb_burn"]["error"]


def test_refresh_is_idempotent(http, listed):
    cf.refresh(now=NOW)
    first = [(r["id"], r["title"], r["starts_at"]) for r in events()]
    res = cf.refresh(now=NOW)
    assert [(r["id"], r["title"], r["starts_at"]) for r in events()] == first
    assert res["removed"] == 0


def test_rescheduled_event_replaces_old_row(http, listed):
    cf.refresh(now=NOW)
    http.ff = [dict(FF[0], date="2026-10-23T08:30:00-04:00")] + FF[1:]
    res = cf.refresh(now=NOW)
    cpi = [r for r in events() if r["title"] == "CPI m/m"]
    assert [r["starts_at"] for r in cpi] == ["2026-10-23T17:30:00+05:00"]
    assert res["removed"] == 1


def test_failed_source_leaves_others_working(http, listed):
    cf.refresh(now=NOW)
    http.ff = RuntimeError("feed down")
    http.nasdaq = RuntimeError("blocked")
    res = cf.refresh(now=NOW)
    assert res["ok"] is True  # binance still answered
    assert res["sources"]["forexfactory"] == {"available": False, "error": "RuntimeError: feed down"}
    assert res["sources"]["nasdaq"]["available"] is False
    # earlier rows of the failed sources are kept, not removed
    kinds = sorted({r["kind"] for r in events()})
    assert kinds == ["binance", "earnings", "macro"]
    status = {s["name"]: s for s in cf.source_status()}
    assert status["forexfactory"]["available"] is False


def test_nothing_answers_job_fails(http):
    http.ff = http.nasdaq = http.binance = RuntimeError("offline")
    assert cf.refresh(now=NOW)["ok"] is False
    with pytest.raises(RuntimeError):
        cf.run()


def test_refresh_never_raises(monkeypatch):
    monkeypatch.setattr(cf, "_refresh", lambda *_a: 1 / 0)
    assert cf.refresh()["ok"] is False


# --- read side, API and snapshot --------------------------------------------------------


def _insert(title, starts, kind="macro", impact="high", ticker=""):
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO calendar_events (source, kind, title, starts_at, impact, ticker, fetched_at)"
            " VALUES ('t', ?, ?, ?, ?, ?, 'x')", (kind, title, cf.iso(starts), impact, ticker))


def test_api_sorted_and_filtered():
    now = datetime.now(timezone.utc)
    _insert("later", now + timedelta(days=2))
    _insert("sooner", now + timedelta(hours=1), kind="earnings", impact=None, ticker="NVDA")
    _insert("yesterday", now - timedelta(days=2))
    _insert("too far", now + timedelta(days=20))
    res = main.calendar_list(days=7, kind="")
    assert [e.title for e in res.events] == ["sooner", "later"]
    assert res.events[0].ticker == "NVDA" and res.events[1].ticker is None
    assert [e.title for e in main.calendar_list(days=7, kind="earnings").events] == ["sooner"]
    with pytest.raises(main.HTTPException):
        main.calendar_list(days=7, kind="nope")


def test_upcoming_high_impact_and_snapshot_field(monkeypatch):
    now = datetime.now(timezone.utc)
    _insert("FOMC", now + timedelta(hours=3))
    _insert("Medium thing", now + timedelta(hours=2), impact="medium")
    _insert("Next week", now + timedelta(days=3))
    up = cf.upcoming_high_impact()
    assert [e["title"] for e in up] == ["FOMC"]
    # the prompt block carries it after the guard sections
    blob = market.context_to_prompt_block({
        "tv_symbol": "BINANCE:BTCUSDT", "timeframe": "1h",
        "setup": {"type": "x"}, "confluence": {"bias": "Buy", "score": 3}, "upcoming_events": up,
    })
    data = json.loads(blob)
    assert list(data)[:4] == ["pair", "timeframe", "setup", "confluence"]
    assert data["upcoming_events"][0]["title"] == "FOMC"


def test_background_refresh_only_when_empty(monkeypatch):
    started = []
    monkeypatch.setattr(cf.threading, "Thread",
                        lambda **kw: type("T", (), {"start": lambda self: started.append(kw["name"])})())
    assert cf.refresh_in_background_if_empty() is True
    _insert("soon", datetime.now(timezone.utc) + timedelta(hours=1))
    assert cf.refresh_in_background_if_empty() is False
    assert started == ["calendar-refresh"]
