"""Instrument catalogue (WL-044): every Binance spot pair and USD-M contract, with names.

refresh() pulls both exchangeInfo endpoints and upserts the `instruments` table.
Names come from optional sources, each of which may fail without stopping the
refresh (its status is recorded as available / error in the result):

- crypto: Binance public asset list (assetCode -> assetName), else the base asset.
  The TradingView coin list has symbols only, so it cannot supply names.
- US stocks and ETFs: SEC company_tickers.json, else the bundled snapshot.
- ETFs, HK / KR / CN stocks, commodities, FX, index, pre-IPO: the curated names in
  app/data/instrument_names.json, which win over every other source.

A market whose exchangeInfo fails is left as it is: its rows are not marked delisted.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from . import db

logger = logging.getLogger(__name__)

SPOT_URL = "https://api.binance.com/api/v3/exchangeInfo"
USDM_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
ASSETS_URL = "https://www.binance.com/bapi/asset/v2/public/asset/asset/get-all-asset"
SEC_URL = "https://www.sec.gov/files/company_tickers.json"
# SEC asks for a User-Agent; no email or personal data in it.
SEC_HEADERS = {"User-Agent": "CryptoChartAI/1.0 (personal local use)"}
NAMES_FILE = Path(__file__).resolve().parent / "data" / "instrument_names.json"

_REGION = {"EQUITY": "US", "HK_EQUITY": "HK", "KR_EQUITY": "KR", "CN_EQUITY": "CN"}
_TYPE = {"COMMODITY": "commodity", "FX": "fx", "PREMARKET": "premarket", "INDEX": "index"}
_MULTIPLIER = re.compile(r"^10{3,}(?=[A-Z])")  # 1000PEPE, 1000000MOG

_refresh_lock = threading.Lock()


@lru_cache(maxsize=1)
def bundled() -> dict[str, Any]:
    try:
        data = json.loads(NAMES_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        logger.exception("instrument names file unreadable")
        data = {}
    return {
        "names": {k.upper(): v for k, v in (data.get("names") or {}).items()},
        "etf": {t.upper() for t in data.get("etf") or []},
        "us_fallback": {k.upper(): v for k, v in (data.get("us_fallback") or {}).items()},
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_json(client: httpx.Client, url: str, **kwargs: Any) -> Any:
    r = client.get(url, **kwargs)
    r.raise_for_status()
    return r.json()


def _source(fn, *args) -> tuple[Any, dict[str, Any]]:
    """Run one optional source: (value, {"available": bool, "error"?: str})."""
    try:
        return fn(*args), {"available": True}
    except Exception as exc:  # noqa: BLE001
        logger.warning("instrument source %s failed: %s", getattr(fn, "__name__", fn), exc)
        return None, {"available": False, "error": f"{type(exc).__name__}: {exc}"[:300]}


def _fetch_spot(client: httpx.Client) -> list[dict[str, Any]]:
    data = _get_json(client, SPOT_URL)
    return [s for s in data["symbols"] if s.get("status") == "TRADING"]


def _fetch_usdm(client: httpx.Client) -> list[dict[str, Any]]:
    data = _get_json(client, USDM_URL)
    return [s for s in data["symbols"] if s.get("status") == "TRADING"]


def _fetch_asset_names(client: httpx.Client) -> dict[str, str]:
    data = _get_json(client, ASSETS_URL)
    rows = data.get("data") if isinstance(data, dict) else None
    if not rows:
        raise ValueError("asset list empty")
    return {
        str(a["assetCode"]).upper(): str(a.get("assetName") or "").strip()
        for a in rows
        if a.get("assetCode") and a.get("assetName")
    }


def _fetch_sec_names(client: httpx.Client) -> dict[str, str]:
    data = _get_json(client, SEC_URL, headers=SEC_HEADERS)
    # BRK-B in SEC terms is BRKB on Binance
    return {re.sub(r"[-.]", "", str(v["ticker"]).upper()): str(v["title"]) for v in data.values()}


def classify(contract: dict[str, Any]) -> tuple[str, str | None]:
    """(type, region) for a USD-M contract."""
    underlying = str(contract.get("underlyingType") or "").upper()
    subtypes = [str(s).lower() for s in contract.get("underlyingSubType") or []]
    base = str(contract.get("baseAsset") or "").upper()
    if underlying == "PREMARKET" or "pre-ipo" in subtypes:
        return "premarket", None
    if underlying in _REGION:
        return ("etf" if base in bundled()["etf"] else "stock"), _REGION[underlying]
    if underlying in _TYPE:
        return _TYPE[underlying], None
    return "crypto", None


def crypto_name(base: str, assets: dict[str, str] | None) -> str | None:
    if not assets:
        return None
    return assets.get(base) or assets.get(_MULTIPLIER.sub("", base))


def pick_name(kind: str, region: str | None, base: str,
              assets: dict[str, str] | None, sec: dict[str, str] | None) -> str | None:
    """Best known name, or None when only the ticker is known."""
    b = bundled()
    if base in b["names"]:
        return b["names"][base]
    if kind == "crypto":
        return crypto_name(base, assets)
    if region == "US":
        return (sec or {}).get(base) or b["us_fallback"].get(base)
    return None


def refresh() -> dict[str, Any]:
    """Fetch, upsert, mark delisted, rebuild the search index. Never raises."""
    with _refresh_lock:
        try:
            return _refresh()
        except Exception as exc:  # noqa: BLE001
            logger.exception("instrument refresh failed")
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:300]}


def _refresh() -> dict[str, Any]:
    sources: dict[str, dict[str, Any]] = {}
    with httpx.Client(timeout=30.0) as client:
        spot, sources["spot"] = _source(_fetch_spot, client)
        usdm, sources["usdm"] = _source(_fetch_usdm, client)
        assets, sources["asset_names"] = _source(_fetch_asset_names, client)
        has_us = any(c.get("underlyingType") == "EQUITY" for c in usdm or [])
        sec, sources["sec"] = _source(_fetch_sec_names, client) if has_us else (None, {"available": None})

    rows: list[dict[str, Any]] = []
    for s in spot or []:
        base = str(s.get("baseAsset") or "").upper()
        rows.append({"symbol": s["symbol"], "market": "spot", "type": "crypto", "base": base,
                     "quote": s.get("quoteAsset"), "region": None,
                     "name": pick_name("crypto", None, base, assets, sec)})
    for c in usdm or []:
        base = str(c.get("baseAsset") or "").upper()
        kind, region = classify(c)
        rows.append({"symbol": c["symbol"], "market": "usdm", "type": kind, "base": base,
                     "quote": c.get("quoteAsset"), "region": region,
                     "name": pick_name(kind, region, base, assets, sec)})

    stamp = _now()
    delisted = 0
    with db.connect() as conn:
        existing = {
            (r["symbol"], r["market"]): r["name"]
            for r in conn.execute("SELECT symbol, market, name FROM instruments")
        }
        fallback = 0
        for r in rows:
            if r["name"] is None:
                # Keep a name an earlier run found; otherwise the ticker stands in.
                old = existing.get((r["symbol"], r["market"]))
                r["name"] = old if old and old != r["base"] else r["base"]
                if r["name"] == r["base"]:
                    fallback += 1
            conn.execute(
                "INSERT INTO instruments (symbol, market, type, base, quote, name, region, status,"
                " first_seen, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'trading', ?, ?)"
                " ON CONFLICT (symbol, market) DO UPDATE SET type = excluded.type,"
                " base = excluded.base, quote = excluded.quote, name = excluded.name,"
                " region = excluded.region, status = 'trading', updated_at = excluded.updated_at",
                (r["symbol"], r["market"], r["type"], r["base"], r["quote"], r["name"],
                 r["region"], stamp, stamp),
            )
        conn.execute("CREATE TEMP TABLE IF NOT EXISTS seen (symbol TEXT, market TEXT)")
        conn.execute("DELETE FROM temp.seen")
        conn.executemany("INSERT INTO temp.seen VALUES (?, ?)", [(r["symbol"], r["market"]) for r in rows])
        for market, got in (("spot", spot), ("usdm", usdm)):
            if got is None:
                continue  # source failed: do not delist what we could not see
            cur = conn.execute(
                "UPDATE instruments SET status = 'delisted', updated_at = ?"
                " WHERE market = ? AND status = 'trading' AND NOT EXISTS (SELECT 1 FROM temp.seen s"
                " WHERE s.symbol = instruments.symbol AND s.market = instruments.market)",
                (stamp, market),
            )
            delisted += cur.rowcount
        conn.execute("INSERT INTO instruments_fts (instruments_fts) VALUES ('rebuild')")

    by_type = Counter(r["type"] for r in rows)
    return {
        "ok": spot is not None or usdm is not None,
        "spot": len(spot or []),
        "usdm": len(usdm or []),
        "by_type": dict(sorted(by_type.items())),
        "delisted": delisted,
        "names_fallback": fallback,
        "sources": sources,
    }


def run() -> str:
    """Job entry point (python -m app.jobs instruments)."""
    res = refresh()
    if not res.get("ok"):
        failed = {k: v.get("error") for k, v in (res.get("sources") or {}).items() if v.get("available") is False}
        raise RuntimeError(res.get("error") or f"no exchangeInfo source answered: {failed}")
    types = " ".join(f"{k}={v}" for k, v in res["by_type"].items())
    down = [k for k, v in res["sources"].items() if v.get("available") is False]
    return (f"spot={res['spot']} usdm={res['usdm']} {types} delisted={res['delisted']}"
            f" names_fallback={res['names_fallback']}" + (f" sources_down={','.join(down)}" if down else ""))


# --- read side for search -------------------------------------------------------

_items_cache: dict[str, Any] = {"key": None, "items": []}
_items_lock = threading.Lock()


def count_trading() -> int:
    with db.connect() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM instruments WHERE status = 'trading'").fetchone()["n"]


def _to_item(r: dict[str, Any]) -> dict[str, Any]:
    if r["market"] == "usdm":
        sym = f"{r['symbol']}.P"  # TradingView perps use SYMBOL.P
        item = {"symbol": sym, "exchange": "BINANCE", "tv_symbol": f"BINANCE:{sym}", "kind": "perp",
                "label": f"{sym} · BINANCE perp", "aliases": r["symbol"]}
    else:
        sym = r["symbol"]
        item = {"symbol": sym, "exchange": "BINANCE", "tv_symbol": f"BINANCE:{sym}", "kind": "spot",
                "label": f"{sym} · BINANCE spot"}
    item.update({"type": r["type"], "name": r["name"], "market": r["market"]})
    return item


def search_items() -> list[dict[str, Any]]:
    """Trading instruments as search items; reloaded only when the table changes."""
    with db.connect() as conn:
        k = conn.execute(
            "SELECT COUNT(*) AS n, MAX(updated_at) AS u FROM instruments WHERE status = 'trading'"
        ).fetchone()
        key = (str(db.db_path()), k["n"], k["u"])
        if _items_cache["key"] == key:
            return _items_cache["items"]
        rows = conn.execute(
            "SELECT symbol, market, type, name FROM instruments WHERE status = 'trading' ORDER BY id"
        ).fetchall()
    items = [_to_item(r) for r in rows]
    with _items_lock:
        _items_cache.update(key=key, items=items)
    return items


def name_matches(query: str) -> set[str]:
    """tv_symbols whose symbol, base or name has a word starting with every query word."""
    words = re.findall(r"[0-9A-Za-z]+", query)
    if not words:
        return set()
    match = " AND ".join(f'"{w}"*' for w in words)
    try:
        with db.connect() as conn:
            rows = conn.execute(
                "SELECT i.symbol, i.market FROM instruments_fts f JOIN instruments i ON i.id = f.rowid"
                " WHERE instruments_fts MATCH ? AND i.status = 'trading'",
                (match,),
            ).fetchall()
    except Exception:  # noqa: BLE001
        logger.exception("instrument name search failed")
        return set()
    return {f"BINANCE:{r['symbol']}.P" if r["market"] == "usdm" else f"BINANCE:{r['symbol']}" for r in rows}


def refresh_in_background_if_empty() -> bool:
    """Startup hook: fill an empty catalogue without blocking startup."""
    try:
        if count_trading():
            return False
    except Exception:  # noqa: BLE001
        logger.exception("instrument count failed")
        return False
    threading.Thread(target=refresh, name="instruments-refresh", daemon=True).start()
    return True
