"""Whale / smart-money proxies from Binance Futures public data."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_PERIOD_MAP = {
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "1d": "1d",
    "1D": "1d",
}


def _period(tf: str) -> str:
    return _PERIOD_MAP.get(tf, "1h")


def fetch_flow_snapshot(pair: str, timeframe: str = "1h") -> dict[str, Any]:
    """Top-trader positioning, retail L/S, funding, OI, taker flow."""
    symbol = pair.upper().replace(".P", "")
    period = _period(timeframe)
    out: dict[str, Any] = {"symbol": symbol, "period": period, "available": False}

    try:
        with httpx.Client(timeout=15.0) as client:
            oi = _get(client, f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}")
            prem = _get(client, f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}")
            top = _get(
                client,
                f"https://fapi.binance.com/futures/data/topLongShortPositionRatio"
                f"?symbol={symbol}&period={period}&limit=3",
            )
            retail = _get(
                client,
                f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
                f"?symbol={symbol}&period={period}&limit=3",
            )
            taker = _get(
                client,
                f"https://fapi.binance.com/futures/data/takerlongshortRatio"
                f"?symbol={symbol}&period={period}&limit=3",
            )
            oi_hist = _get(
                client,
                f"https://fapi.binance.com/futures/data/openInterestHist"
                f"?symbol={symbol}&period={period}&limit=6",
            )
            ticker = _get(
                client,
                f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}",
            )

        if not oi and not prem:
            out["note"] = "No Binance futures market for this symbol (spot-only?)"
            return out

        top_row = _latest(top)
        retail_row = _latest(retail)
        taker_row = _latest(taker)
        prev_top = _prev(top)
        prev_retail = _prev(retail)

        funding = float(prem.get("lastFundingRate", 0)) if prem else None
        mark = float(prem.get("markPrice", 0)) if prem else None
        index = float(prem.get("indexPrice", 0)) if prem else None
        basis_pct = None
        if mark and index:
            basis_pct = round((mark - index) / index * 100, 4)
        oi_now = float(oi.get("openInterest", 0)) if oi else None
        oi_change_pct = None
        if isinstance(oi_hist, list) and len(oi_hist) >= 2:
            try:
                a = float(oi_hist[-2].get("sumOpenInterest", 0))
                b = float(oi_hist[-1].get("sumOpenInterest", 0))
                if a:
                    oi_change_pct = round((b - a) / a * 100, 3)
            except (TypeError, ValueError, ZeroDivisionError):
                pass

        price_chg = _f(ticker, "priceChangePercent") if ticker else None
        oi_price_signal = _oi_price_signal(price_chg, oi_change_pct)

        top_ls = _f(top_row, "longShortRatio")
        retail_ls = _f(retail_row, "longShortRatio")
        top_long_pct = _pct(_f(top_row, "longAccount"))
        retail_long_pct = _pct(_f(retail_row, "longAccount"))
        taker_bs = _f(taker_row, "buySellRatio")

        # Interpretations (heuristic, not advice)
        whale_bias = _ls_bias(top_ls)
        retail_bias = _ls_bias(retail_ls)
        funding_bias = _funding_bias(funding)
        taker_bias = "Buyers" if taker_bs and taker_bs > 1.05 else (
            "Sellers" if taker_bs and taker_bs < 0.95 else "Balanced"
        )
        divergence = None
        if whale_bias in ("Long", "Short") and retail_bias in ("Long", "Short"):
            if whale_bias != retail_bias:
                divergence = f"Whales {whale_bias} vs retail {retail_bias} (contrarian cue)"
            else:
                divergence = f"Whales + retail both {whale_bias}"

        crowded = None
        if top_ls and top_ls >= 1.8:
            crowded = "Crowded long (top traders)"
        elif top_ls and top_ls <= 0.55:
            crowded = "Crowded short (top traders)"

        out.update(
            {
                "available": True,
                "mark_price": mark,
                "open_interest": oi_now,
                "oi_change_pct": oi_change_pct,
                "funding_rate": funding,
                "funding_apr_est": round(funding * 3 * 365 * 100, 2) if funding is not None else None,
                "funding_bias": funding_bias,
                "basis_pct": basis_pct,
                "oi_price_signal": oi_price_signal,
                "whale_long_short_ratio": top_ls,
                "whale_long_pct": top_long_pct,
                "whale_bias": whale_bias,
                "whale_ls_delta": _delta(top_ls, _f(prev_top, "longShortRatio")),
                "retail_long_short_ratio": retail_ls,
                "retail_long_pct": retail_long_pct,
                "retail_bias": retail_bias,
                "retail_ls_delta": _delta(retail_ls, _f(prev_retail, "longShortRatio")),
                "taker_buy_sell_ratio": taker_bs,
                "taker_bias": taker_bias,
                "positioning_divergence": divergence,
                "crowding": crowded,
                "volume_24h": _f(ticker, "quoteVolume") if ticker else None,
                "price_change_24h_pct": _f(ticker, "priceChangePercent") if ticker else None,
                "summary": _summary(
                    whale_bias,
                    retail_bias,
                    funding_bias,
                    taker_bias,
                    oi_change_pct,
                    crowded,
                    divergence,
                    oi_price_signal,
                    basis_pct,
                ),
            }
        )
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("flow snapshot failed for %s: %s", symbol, exc)
        return {"symbol": symbol, "available": False, "error": str(exc)}


def _oi_price_signal(price_chg: float | None, oi_chg: float | None) -> str | None:
    if price_chg is None or oi_chg is None:
        return None
    if price_chg > 0.3 and oi_chg > 0.3:
        return "Long build (price↑ + OI↑)"
    if price_chg < -0.3 and oi_chg > 0.3:
        return "Short build (price↓ + OI↑)"
    if price_chg > 0.3 and oi_chg < -0.3:
        return "Short cover (price↑ + OI↓)"
    if price_chg < -0.3 and oi_chg < -0.3:
        return "Long unwind (price↓ + OI↓)"
    return "Mixed / low conviction"


def _get(client: httpx.Client, url: str) -> Any:
    try:
        r = client.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:  # noqa: BLE001
        return None


def _latest(rows: Any) -> dict[str, Any]:
    if isinstance(rows, list) and rows:
        return rows[-1] if isinstance(rows[-1], dict) else {}
    return {}


def _prev(rows: Any) -> dict[str, Any]:
    if isinstance(rows, list) and len(rows) >= 2:
        return rows[-2] if isinstance(rows[-2], dict) else {}
    return {}


def _f(row: dict[str, Any] | None, key: str) -> float | None:
    if not row:
        return None
    try:
        return float(row.get(key))
    except (TypeError, ValueError):
        return None


def _pct(v: float | None) -> float | None:
    if v is None:
        return None
    return round(v * 100, 2)


def _delta(cur: float | None, prev: float | None) -> float | None:
    if cur is None or prev is None:
        return None
    return round(cur - prev, 4)


def _ls_bias(ratio: float | None) -> str:
    if ratio is None:
        return "Unknown"
    if ratio >= 1.15:
        return "Long"
    if ratio <= 0.87:
        return "Short"
    return "Neutral"


def _funding_bias(rate: float | None) -> str:
    if rate is None:
        return "Unknown"
    if rate >= 0.0003:
        return "Longs paying (crowded long)"
    if rate <= -0.0003:
        return "Shorts paying (crowded short)"
    return "Neutral"


def _summary(
    whale: str,
    retail: str,
    funding: str,
    taker: str,
    oi_chg: float | None,
    crowded: str | None,
    divergence: str | None,
    oi_price: str | None = None,
    basis: float | None = None,
) -> str:
    parts = [
        f"Whales:{whale}",
        f"Retail:{retail}",
        f"Taker:{taker}",
        f"Funding:{funding}",
    ]
    if oi_chg is not None:
        parts.append(f"OIΔ:{oi_chg:+.2f}%")
    if oi_price:
        parts.append(oi_price)
    if basis is not None:
        parts.append(f"Basis:{basis:+.3f}%")
    if crowded:
        parts.append(crowded)
    if divergence:
        parts.append(divergence)
    return " | ".join(parts)
