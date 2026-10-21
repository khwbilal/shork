"""Instrument catalogue: refresh with stubbed HTTP, classification, names, catalogue search."""

from __future__ import annotations

import pytest

from app import db, instruments, symbols


def spot(sym, base, quote="USDT"):
    return {"symbol": sym, "baseAsset": base, "quoteAsset": quote, "status": "TRADING"}


def fut(sym, base, underlying="COIN", contract="PERPETUAL", sub=None):
    return {"symbol": sym, "baseAsset": base, "quoteAsset": "USDT", "status": "TRADING",
            "contractType": contract, "underlyingType": underlying, "underlyingSubType": sub or []}


def tradfi(sym, base, underlying, sub=("TradFi",)):
    return fut(sym, base, underlying, "TRADIFI_PERPETUAL", list(sub))


SPOT = [spot("BTCUSDT", "BTC"), spot("ETHUSDT", "ETH"), spot("ETHBTC", "ETH", "BTC"),
        spot("ETHFIUSDT", "ETHFI"), spot("PAXGUSDT", "PAXG"), spot("NEWCOINUSDT", "NEWCOIN")]
USDM = [
    fut("BTCUSDT", "BTC"), fut("ETHUSDT", "ETH"), fut("1000PEPEUSDT", "1000PEPE"),
    fut("BTCDOMUSDT", "BTCDOM", "INDEX"),
    tradfi("NVDAUSDT", "NVDA", "EQUITY"), tradfi("SPYUSDT", "SPY", "EQUITY"),
    tradfi("ZZZQUSDT", "ZZZQ", "EQUITY"), tradfi("HK0700USDT", "HK0700", "HK_EQUITY"),
    tradfi("KODEX200USDT", "KODEX200", "KR_EQUITY"), tradfi("CXMTUSDT", "CXMT", "CN_EQUITY"),
    tradfi("XAUUSDT", "XAU", "COMMODITY"), tradfi("CLUSDT", "CL", "COMMODITY"),
    tradfi("USDBRLUSDT", "USDBRL", "FX"), tradfi("OPENAIUSDT", "OPENAI", "PREMARKET", ("Pre-IPO", "TradFi")),
]
ASSETS = {"BTC": "Bitcoin", "ETH": "Ethereum", "ETHFI": "ether.fi", "PAXG": "PAX Gold", "PEPE": "Pepe"}
SEC = {"NVDA": "NVIDIA CORP", "SPY": "SPDR S&P 500 ETF TRUST"}


class Stub:
    def __init__(self, monkeypatch):
        self.spot, self.usdm, self.assets, self.sec = list(SPOT), list(USDM), dict(ASSETS), dict(SEC)
        for name in ("spot", "usdm", "assets", "sec"):
            monkeypatch.setattr(instruments, {"spot": "_fetch_spot", "usdm": "_fetch_usdm",
                                              "assets": "_fetch_asset_names",
                                              "sec": "_fetch_sec_names"}[name], self._make(name))

    def _make(self, name):
        def fetch(_client):
            value = getattr(self, name)
            if isinstance(value, Exception):
                raise value
            return value

        fetch.__name__ = f"_fetch_{name}"
        return fetch


@pytest.fixture
def stub(monkeypatch):
    return Stub(monkeypatch)


def rows():
    with db.connect() as conn:
        return {(r["symbol"], r["market"]): r for r in conn.execute("SELECT * FROM instruments")}


def test_refresh_upserts_and_classifies(stub):
    res = instruments.refresh()
    assert res["ok"] is True and res["spot"] == 6 and res["usdm"] == 14
    assert res["by_type"] == {"commodity": 2, "crypto": 9, "etf": 2, "fx": 1, "index": 1,
                              "premarket": 1, "stock": 4}
    assert all(s["available"] for s in res["sources"].values())
    r = rows()
    assert r[("NVDAUSDT", "usdm")]["type"] == "stock" and r[("NVDAUSDT", "usdm")]["region"] == "US"
    assert r[("SPYUSDT", "usdm")]["type"] == "etf"
    assert r[("HK0700USDT", "usdm")]["region"] == "HK" and r[("HK0700USDT", "usdm")]["type"] == "stock"
    assert r[("KODEX200USDT", "usdm")]["type"] == "etf" and r[("KODEX200USDT", "usdm")]["region"] == "KR"
    assert r[("CXMTUSDT", "usdm")]["region"] == "CN"
    assert r[("XAUUSDT", "usdm")]["type"] == "commodity" and r[("XAUUSDT", "usdm")]["region"] is None
    assert r[("USDBRLUSDT", "usdm")]["type"] == "fx"
    assert r[("OPENAIUSDT", "usdm")]["type"] == "premarket"
    assert r[("BTCDOMUSDT", "usdm")]["type"] == "index"
    assert r[("BTCUSDT", "spot")]["type"] == "crypto" and r[("BTCUSDT", "spot")]["quote"] == "USDT"
    assert all(x["status"] == "trading" for x in r.values())


def test_names_and_fallbacks(stub):
    res = instruments.refresh()
    r = rows()
    assert r[("BTCUSDT", "spot")]["name"] == "Bitcoin"
    assert r[("1000PEPEUSDT", "usdm")]["name"] == "Pepe"  # multiplier prefix stripped
    assert r[("NVDAUSDT", "usdm")]["name"] == "NVIDIA CORP"  # SEC
    assert r[("SPYUSDT", "usdm")]["name"] == "SPDR S&P 500 ETF Trust"  # curated wins over SEC
    assert r[("XAUUSDT", "usdm")]["name"] == "Gold"
    assert r[("CLUSDT", "usdm")]["name"] == "Crude Oil WTI"
    # unknown names stay the ticker and are counted
    assert r[("NEWCOINUSDT", "spot")]["name"] == "NEWCOIN"
    assert r[("ZZZQUSDT", "usdm")]["name"] == "ZZZQ"
    assert res["names_fallback"] == 2


def test_sources_fail_softly(stub):
    instruments.refresh()
    stub.assets = RuntimeError("asset list down")
    stub.sec = RuntimeError("403")
    res = instruments.refresh()
    assert res["ok"] is True
    assert res["sources"]["asset_names"]["available"] is False
    assert "asset list down" in res["sources"]["asset_names"]["error"]
    r = rows()
    assert r[("BTCUSDT", "spot")]["name"] == "Bitcoin"  # earlier name kept
    assert r[("NVDAUSDT", "usdm")]["name"] == "NVIDIA CORP"  # bundled SEC snapshot


def test_first_run_without_name_sources(stub):
    stub.assets = RuntimeError("down")
    stub.sec = RuntimeError("down")
    res = instruments.refresh()
    r = rows()
    assert r[("BTCUSDT", "spot")]["name"] == "BTC"
    assert r[("NVDAUSDT", "usdm")]["name"] == "NVIDIA CORP"  # bundled snapshot
    assert r[("XAUUSDT", "usdm")]["name"] == "Gold"
    assert res["names_fallback"] > 2


def test_missing_rows_marked_delisted_never_deleted(stub):
    instruments.refresh()
    stub.spot = [s for s in SPOT if s["symbol"] != "ETHFIUSDT"]
    stub.usdm = [c for c in USDM if c["symbol"] != "CLUSDT"]
    res = instruments.refresh()
    assert res["delisted"] == 2
    r = rows()
    assert r[("ETHFIUSDT", "spot")]["status"] == "delisted"
    assert r[("CLUSDT", "usdm")]["status"] == "delisted"
    first_seen = r[("BTCUSDT", "spot")]["first_seen"]
    # relisted: back to trading, first_seen unchanged
    stub.spot = list(SPOT)
    instruments.refresh()
    r = rows()
    assert r[("ETHFIUSDT", "spot")]["status"] == "trading"
    assert r[("BTCUSDT", "spot")]["first_seen"] == first_seen
    assert len(r) == 20


def test_failed_market_is_not_delisted(stub):
    instruments.refresh()
    stub.usdm = RuntimeError("fapi down")
    res = instruments.refresh()
    assert res["ok"] is True and res["delisted"] == 0
    assert rows()[("NVDAUSDT", "usdm")]["status"] == "trading"


def test_refresh_never_raises_and_job_fails_when_nothing_answers(stub):
    stub.spot = RuntimeError("down")
    stub.usdm = RuntimeError("down")
    res = instruments.refresh()
    assert res["ok"] is False
    with pytest.raises(RuntimeError):
        instruments.run()


def test_job_summary(stub):
    msg = instruments.run()
    assert msg.startswith("spot=6 usdm=14 ") and "names_fallback=2" in msg


# --- catalogue search -------------------------------------------------------------


@pytest.fixture
def catalogue(stub, monkeypatch):
    instruments.refresh()
    monkeypatch.setattr(symbols, "_CACHE", {"ts": 0.0, "items": []})
    kucoin = [{"symbol": "ETHUSDT", "exchange": "KUCOIN", "tv_symbol": "KUCOIN:ETHUSDT", "kind": "spot",
               "label": "ETHUSDT · KUCOIN spot"},
              {"symbol": "BTCUSDT", "exchange": "BINANCE", "tv_symbol": "BINANCE:BTCUSDT", "kind": "spot",
               "label": "BTCUSDT · BINANCE spot"},
              {"symbol": "NVDA", "exchange": "NASDAQ", "tv_symbol": "NASDAQ:NVDA", "kind": "spot",
               "label": "NVDA · NASDAQ spot"}]
    monkeypatch.setattr(symbols, "_load_coinlist_items", lambda: list(kucoin))

    def no_fetch():
        raise AssertionError("catalogue mode must not fetch exchangeInfo")

    monkeypatch.setattr(symbols, "_fetch_binance_universe", no_fetch)


def tvs(results):
    return [r["tv_symbol"] for r in results]


def test_prefix_finds_stock(catalogue):
    out = symbols.search_symbols("nvd", "BINANCE")
    assert out[0]["tv_symbol"] == "BINANCE:NVDAUSDT.P"
    assert out[0]["type"] == "stock" and out[0]["name"] == "NVIDIA CORP" and out[0]["market"] == "usdm"
    assert out[0]["aliases"] == "NVDAUSDT" and out[0]["kind"] == "perp"


def test_name_search_finds_gold(catalogue):
    out = tvs(symbols.search_symbols("gold", "BINANCE"))
    assert out[0] == "BINANCE:XAUUSDT.P"  # exact name first
    assert "BINANCE:PAXGUSDT" in out  # "PAX Gold" by word prefix
    assert tvs(symbols.search_symbols("crude oil", "BINANCE"))[0] == "BINANCE:CLUSDT.P"


def test_catalogue_ranking_unchanged(catalogue):
    out = tvs(symbols.search_symbols("eth", "BINANCE"))
    assert out[:2] == ["BINANCE:ETHUSDT", "BINANCE:ETHUSDT.P"]
    assert out.index("BINANCE:ETHUSDT") < out.index("BINANCE:ETHBTC")
    assert out.index("BINANCE:ETHUSDT") < out.index("BINANCE:ETHFIUSDT")
    # other venues still come from the coin list, behind the selected exchange
    assert out.index("BINANCE:ETHUSDT") < out.index("KUCOIN:ETHUSDT")
    kucoin = tvs(symbols.search_symbols("eth", "KUCOIN"))
    assert kucoin[0] == "KUCOIN:ETHUSDT"
    assert symbols.search_symbols("btcusdt.p", "BINANCE")[0]["tv_symbol"] == "BINANCE:BTCUSDT.P"


def test_catalogue_results_keep_keys(catalogue):
    for r in symbols.search_symbols("eth", "BINANCE", limit=40):
        assert {"symbol", "exchange", "tv_symbol", "kind", "label", "type", "name", "market"} <= set(r)
    coin = next(r for r in symbols.search_symbols("eth", "KUCOIN") if r["exchange"] == "KUCOIN")
    assert coin["type"] == "crypto" and coin["name"] is None and coin["market"] == "spot"
    nasdaq = next(r for r in symbols.search_symbols("nvda", "BINANCE") if r["exchange"] == "NASDAQ")
    assert nasdaq["type"] == "stock"


def test_delisted_not_searchable(catalogue, stub):
    stub.spot = [s for s in SPOT if s["symbol"] != "ETHFIUSDT"]
    instruments.refresh()
    assert "BINANCE:ETHFIUSDT" not in tvs(symbols.search_symbols("ethfi", "BINANCE"))


def test_background_refresh_only_when_empty(stub, monkeypatch):
    started = []
    monkeypatch.setattr(instruments.threading, "Thread",
                        lambda **kw: type("T", (), {"start": lambda self: started.append(kw["name"])})())
    assert instruments.refresh_in_background_if_empty() is True
    assert started == ["instruments-refresh"]
    instruments.refresh()
    assert instruments.refresh_in_background_if_empty() is False


def test_classify_and_names_units():
    assert instruments.classify(tradfi("EWYUSDT", "EWY", "EQUITY")) == ("etf", "US")
    assert instruments.classify(tradfi("AAPLUSDT", "AAPL", "EQUITY")) == ("stock", "US")
    assert instruments.classify(tradfi("XUSDT", "X", "EQUITY", ("TradFi", "Pre-IPO"))) == ("premarket", None)
    assert instruments.classify(fut("BTCUSDT", "BTC")) == ("crypto", None)
    assert instruments.crypto_name("1000000MOG", {"MOG": "Mog Coin"}) == "Mog Coin"
    assert instruments.crypto_name("1INCH", {"1INCH": "1inch"}) == "1inch"
    assert instruments.pick_name("stock", "HK", "HK1810", None, None) == "Xiaomi Corporation"
    assert instruments.pick_name("stock", "US", "UNKNOWNX", None, None) is None
