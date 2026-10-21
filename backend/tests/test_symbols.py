"""symbols.search_symbols ranking, with the universe loaders stubbed out."""

from __future__ import annotations

import pytest

from app import symbols

_REAL_COINLIST_LOADER = symbols._load_coinlist_items


def spot(sym, ex):
    return {
        "symbol": sym,
        "exchange": ex,
        "tv_symbol": f"{ex}:{sym}",
        "kind": "spot",
        "label": f"{sym} · {ex} spot",
    }


def perp(bare, ex="BINANCE"):
    sym = f"{bare}.P"
    return {
        "symbol": sym,
        "exchange": ex,
        "tv_symbol": f"{ex}:{sym}",
        "kind": "perp",
        "label": f"{sym} · {ex} perp",
        "aliases": bare,
    }


COINLIST = [
    spot("ETHBTC", "BINANCE"),
    spot("ETHFIUSDT", "BINANCE"),
    spot("ETHUSDT", "BINANCE"),
    spot("ETHUSDT", "KUCOIN"),
    spot("ETHUSDT", "BYBIT"),
    spot("SETHUSDT", "BINANCE"),
    spot("BTCUSDT", "BINANCE"),
    spot("BTCUSDT", "KUCOIN"),
]
BINANCE_API = [spot("ETHUSDT", "BINANCE"), perp("ETHUSDT"), perp("BTCUSDT")]


@pytest.fixture(autouse=True)
def universe(monkeypatch):
    monkeypatch.setattr(symbols, "_CACHE", {"ts": 0.0, "items": []})
    monkeypatch.setattr(symbols, "_load_coinlist_items", lambda: list(COINLIST))
    monkeypatch.setattr(symbols, "_fetch_binance_universe", lambda: list(BINANCE_API))


def tvs(results):
    return [r["tv_symbol"] for r in results]


def test_q_usdt_comes_first_spot_before_perp():
    out = tvs(symbols.search_symbols("eth", "BINANCE"))
    assert out[:2] == ["BINANCE:ETHUSDT", "BINANCE:ETHUSDT.P"]
    assert out.index("BINANCE:ETHUSDT") < out.index("BINANCE:ETHBTC")
    assert out.index("BINANCE:ETHUSDT") < out.index("BINANCE:ETHFIUSDT")


def test_selected_exchange_first():
    out = tvs(symbols.search_symbols("eth", "kucoin"))
    assert out[0] == "KUCOIN:ETHUSDT"
    assert out.index("KUCOIN:ETHUSDT") < out.index("BINANCE:ETHUSDT")
    assert "BYBIT:ETHUSDT" in out  # other venues still listed, behind


def test_selected_exchange_beats_other_venue_prefix_match():
    # Other venues lose 15, so a selected-venue prefix match (80+10) beats
    # another venue's ETHUSDT (95-15).
    out = tvs(symbols.search_symbols("eth", "KUCOIN"))
    assert out.index("KUCOIN:ETHUSDT") < out.index("BINANCE:ETHUSDT")
    assert out.index("BINANCE:ETHUSDT") < out.index("BINANCE:ETHBTC")


def test_without_exchange_no_venue_bonus():
    out = tvs(symbols.search_symbols("eth"))
    # Equal score for every ETHUSDT spot; ties break on symbol, so the three spots lead.
    assert set(out[:3]) == {"BINANCE:ETHUSDT", "KUCOIN:ETHUSDT", "BYBIT:ETHUSDT"}


def test_all_pseudo_exchange_means_no_preference():
    assert tvs(symbols.search_symbols("eth", "ALL")) == tvs(symbols.search_symbols("eth"))


def test_exact_match_beats_usdt_pair():
    assert tvs(symbols.search_symbols("ethbtc", "BINANCE"))[0] == "BINANCE:ETHBTC"


def test_perp_query_prefers_perp():
    assert tvs(symbols.search_symbols("BTCUSDT.P", "BINANCE"))[0] == "BINANCE:BTCUSDT.P"
    assert tvs(symbols.search_symbols("btcusdt-perp", "BINANCE"))[0] == "BINANCE:BTCUSDT.P"


def test_tradingview_prefix_is_stripped():
    assert tvs(symbols.search_symbols("BINANCE:ETHUSDT", "BINANCE"))[0] == "BINANCE:ETHUSDT"


def test_deduped_and_limited():
    assert len(symbols.search_symbols("eth", "BINANCE", limit=3)) == 3
    full = tvs(symbols.search_symbols("eth", "BINANCE", limit=100))
    assert len(full) == len(set(full))


def test_empty_query():
    assert symbols.search_symbols("  ") == []


def test_universe_is_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(symbols, "_load_coinlist_items", lambda: calls.append(1) or list(COINLIST))
    symbols.search_symbols("eth")
    symbols.search_symbols("btc")
    assert len(calls) == 1


def test_real_coinlist_has_no_all_pseudo_exchange():
    # The real loader reads the installed tradingview_mcp coinlist files (no network).
    items = _REAL_COINLIST_LOADER()
    assert items, "coinlist files should load"
    assert "ALL" not in {it["exchange"] for it in items}
    assert any(it["exchange"] == "BINANCE" for it in items)
