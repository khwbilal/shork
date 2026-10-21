"""Local Binance OHLCV + indicators — used when TradingView TA is rate-limited."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_INTERVAL = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "1d": "1d",
    "1D": "1d",
    "1w": "1w",
    "1W": "1w",
}


def normalize_timeframe(tf: str) -> str:
    return _INTERVAL.get(tf, tf if tf in _INTERVAL.values() else "1h")


def _ema(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    k = 2 / (period + 1)
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def _rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) <= period:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        if d >= 0:
            gains += d
        else:
            losses -= d
    avg_gain = gains / period
    avg_loss = losses / period
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        gain = max(d, 0.0)
        loss = max(-d, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float | None:
    if len(closes) <= period:
        return None
    trs: list[float] = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def _fetch_klines(pair: str, interval: str, limit: int = 220) -> list[list[Any]]:
    urls = [
        f"https://api.binance.com/api/v3/klines?symbol={pair}&interval={interval}&limit={limit}",
        f"https://fapi.binance.com/fapi/v1/klines?symbol={pair}&interval={interval}&limit={limit}",
    ]
    last_err: Exception | None = None
    with httpx.Client(timeout=20.0) as client:
        for url in urls:
            try:
                r = client.get(url)
                if r.status_code == 200:
                    data = r.json()
                    if isinstance(data, list) and data:
                        return data
                last_err = RuntimeError(f"{url} -> {r.status_code} {r.text[:120]}")
            except Exception as exc:  # noqa: BLE001
                last_err = exc
    raise RuntimeError(f"Binance klines failed for {pair}: {last_err}")


def compute_local_analysis(pair: str, timeframe: str) -> dict[str, Any]:
    interval = normalize_timeframe(timeframe)
    raw = _fetch_klines(pair.upper(), interval)
    opens = [float(x[1]) for x in raw]
    highs = [float(x[2]) for x in raw]
    lows = [float(x[3]) for x in raw]
    closes = [float(x[4]) for x in raw]
    volumes = [float(x[5]) for x in raw]

    price = closes[-1]
    prev = closes[-2] if len(closes) > 1 else price
    change_pct = ((price - prev) / prev) * 100 if prev else 0.0

    ema20 = _ema(closes, 20)
    ema50 = _ema(closes, 50)
    ema200 = _ema(closes, 200)
    e20 = ema20[-1]
    e50 = ema50[-1]
    e200 = ema200[-1]
    rsi = _rsi(closes, 14)
    atr = _atr(highs, lows, closes, 14)
    atr_pct = (atr / price * 100) if atr and price else None
    macd = _macd(closes)
    stoch = _stochastic(highs, lows, closes)
    adx = _adx(highs, lows, closes)
    bb = _bollinger(closes)
    vwap = _vwap(highs, lows, closes, volumes, interval)
    pivots = _pivots(highs, lows, closes)
    avg_vol = sum(volumes[-20:]) / min(20, len(volumes)) if volumes else 0
    rvol = round(volumes[-1] / avg_vol, 2) if avg_vol else None

    lookback = min(40, len(highs))
    recent_high = max(highs[-lookback:])
    recent_low = min(lows[-lookback:])

    trend_score = 0
    if e20 and price > e20:
        trend_score += 1
    if e50 and price > e50:
        trend_score += 1
    if e200 and price > e200:
        trend_score += 1
    if e20 and price < e20:
        trend_score -= 1
    if e50 and price < e50:
        trend_score -= 1
    if e200 and price < e200:
        trend_score -= 1

    if trend_score >= 2:
        trend = "Bullish"
    elif trend_score <= -2:
        trend = "Bearish"
    else:
        trend = "Neutral"

    rsi_signal = "Neutral"
    if rsi is not None:
        if rsi >= 70:
            rsi_signal = "Overbought"
        elif rsi <= 30:
            rsi_signal = "Oversold"

    # Suggested structural levels (not trade advice by themselves).
    # The stop sits beyond the swing but within 0.75–2 ATR of entry; the target is
    # the far side of the swing, pushed out to at least 2R when price is already
    # near it (otherwise a trend entry at the high would pay a fraction of its risk).
    unit = atr or price * 0.01
    swing_pad = unit * 0.35
    entry = round(price, 6)
    if trend == "Bullish":
        risk = min(max(price - (recent_low - swing_pad), unit * 0.75), unit * 2.0)
        stop = round(price - risk, 6)
        target = round(max(recent_high + swing_pad, price + 2 * risk), 6)
        bias_hint = "Buy"
    elif trend == "Bearish":
        risk = min(max((recent_high + swing_pad) - price, unit * 0.75), unit * 2.0)
        stop = round(price + risk, 6)
        target = round(min(recent_low - swing_pad, price - 2 * risk), 6)
        bias_hint = "Sell"
    else:
        stop = round(price - unit, 6)
        target = round(price + unit, 6)
        bias_hint = "Neutral"

    return {
        "source": "binance_local",
        "symbol": pair.upper(),
        "timeframe": interval,
        "price_data": {
            "current_price": price,
            "open": opens[-1],
            "high": highs[-1],
            "low": lows[-1],
            "close": price,
            "change_percent": round(change_pct, 4),
            "volume": volumes[-1],
        },
        "rsi": {"value": round(rsi, 2) if rsi is not None else None, "signal": rsi_signal},
        "macd": macd,
        "stochastic": stoch,
        "ema": {
            "ema20": round(e20, 6) if e20 else None,
            "ema50": round(e50, 6) if e50 else None,
            "ema200": round(e200, 6) if e200 else None,
        },
        "atr": {
            "value": round(atr, 6) if atr else None,
            "percent_of_price": round(atr_pct, 4) if atr_pct else None,
        },
        "relative_volume": rvol,
        "adx": adx,
        "bollinger": bb,
        "vwap": vwap,
        "pivots": pivots,
        "support_resistance": {
            "nearest_support": round(recent_low, 6),
            "nearest_resistance": round(recent_high, 6),
            # Secondary: EMA cluster as dynamic S/R
            "support_2": round(min(x for x in [e20, e50, recent_low] if x), 6)
            if any(x for x in [e20, e50])
            else round(recent_low, 6),
            "resistance_2": round(max(x for x in [e20, e50, recent_high] if x), 6)
            if any(x for x in [e20, e50])
            else round(recent_high, 6),
        },
        "market_structure": {
            "trend": trend,
            "trend_strength": "Moderate" if abs(trend_score) >= 2 else "Weak",
            "trend_line": (
                f"{trend} structure: price vs EMA20/50/200 "
                f"({_side(price, e20)}/{_side(price, e50)}/{_side(price, e200)}); "
                f"swing low→high {round(recent_low, 4)} → {round(recent_high, 4)}"
            ),
        },
        "suggested_levels": {
            "bias_hint": bias_hint,
            "entry": entry,
            "stop_loss": stop,
            "take_profit": target,
            "support": round(recent_low, 6),
            "resistance": round(recent_high, 6),
            "support_2": round(e50, 6) if e50 else None,
            "resistance_2": round(e20, 6) if e20 and e20 > price else (
                round(recent_high, 6)
            ),
            "trend": trend,
            "trend_line": (
                f"{trend} · EMA20={_fmt(e20)} · EMA50={_fmt(e50)} · "
                f"swing {round(recent_low, 4)}–{round(recent_high, 4)}"
            ),
            "ema20": round(e20, 6) if e20 else None,
            "ema50": round(e50, 6) if e50 else None,
        },
        "volume_analysis": {
            "current": volumes[-1],
            "average_20": round(sum(volumes[-20:]) / min(20, len(volumes)), 4),
        },
    }


def _bollinger(closes: list[float], period: int = 20, mult: float = 2.0) -> dict[str, Any]:
    if len(closes) < period:
        return {"percent_b": None, "bandwidth": None, "squeeze": None, "position": None}
    window = closes[-period:]
    mid = sum(window) / period
    var = sum((x - mid) ** 2 for x in window) / period
    std = var ** 0.5
    upper = mid + mult * std
    lower = mid - mult * std
    width = (upper - lower) / mid if mid else 0
    pct_b = (closes[-1] - lower) / (upper - lower) if upper != lower else 0.5
    # squeeze vs recent bandwidths
    bands = []
    for i in range(period, len(closes) + 1):
        w = closes[i - period : i]
        m = sum(w) / period
        s = (sum((x - m) ** 2 for x in w) / period) ** 0.5
        bands.append(((m + mult * s) - (m - mult * s)) / m if m else 0)
    squeeze = False
    if len(bands) >= 20:
        squeeze = bands[-1] <= sorted(bands[-50:] if len(bands) >= 50 else bands)[
            max(0, len(bands[-50:] if len(bands) >= 50 else bands) // 10)
        ]
    pos = "Upper Half" if pct_b >= 0.5 else "Lower Half"
    if pct_b >= 1:
        pos = "Above Upper"
    elif pct_b <= 0:
        pos = "Below Lower"
    return {
        "upper": round(upper, 6),
        "middle": round(mid, 6),
        "lower": round(lower, 6),
        "percent_b": round(pct_b, 3),
        "bandwidth": round(width, 4),
        "squeeze": squeeze,
        "position": pos,
    }


def _adx(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> dict[str, Any]:
    if len(closes) < period + 2:
        return {"value": None, "plus_di": None, "minus_di": None, "trend_strength": None}
    plus_dm: list[float] = []
    minus_dm: list[float] = []
    trs: list[float] = []
    for i in range(1, len(closes)):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
        trs.append(
            max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        )

    def _wilder(vals: list[float], n: int) -> list[float]:
        out: list[float] = []
        if len(vals) < n:
            return out
        prev = sum(vals[:n])
        out.append(prev)
        for v in vals[n:]:
            prev = prev - (prev / n) + v
            out.append(prev)
        return out

    atr_w = _wilder(trs, period)
    p_w = _wilder(plus_dm, period)
    m_w = _wilder(minus_dm, period)
    if not atr_w or not p_w or not m_w:
        return {"value": None, "plus_di": None, "minus_di": None, "trend_strength": None}

    dxs: list[float] = []
    for a, p, m in zip(atr_w, p_w, m_w):
        if a == 0:
            dxs.append(0.0)
            continue
        pdi = 100 * p / a
        mdi = 100 * m / a
        denom = pdi + mdi
        dxs.append(0.0 if denom == 0 else abs(pdi - mdi) / denom * 100)

    if len(dxs) < period:
        adx_val = sum(dxs) / len(dxs) if dxs else None
    else:
        adx_val = sum(dxs[:period]) / period
        for d in dxs[period:]:
            adx_val = (adx_val * (period - 1) + d) / period

    a = atr_w[-1]
    pdi = 100 * p_w[-1] / a if a else 0
    mdi = 100 * m_w[-1] / a if a else 0
    strength = "Strong" if adx_val and adx_val >= 25 else (
        "Weak/Chop" if adx_val is not None and adx_val < 18 else "Moderate"
    )
    return {
        "value": round(adx_val, 2) if adx_val is not None else None,
        "plus_di": round(pdi, 2),
        "minus_di": round(mdi, 2),
        "di_signal": "Bullish" if pdi > mdi else "Bearish",
        "trend_strength": strength,
    }


def _vwap(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    volumes: list[float],
    interval: str,
) -> dict[str, Any]:
    # Session-style VWAP approx: last N bars (intraday denser)
    n = 48 if interval in ("15m", "30m", "1h") else (24 if interval == "4h" else 20)
    n = min(n, len(closes))
    typ = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(-n, 0)]
    vol = volumes[-n:]
    num = sum(t * v for t, v in zip(typ, vol))
    den = sum(vol) or 1.0
    val = num / den
    price = closes[-1]
    return {
        "value": round(val, 6),
        "side": "above" if price >= val else "below",
        "distance_pct": round((price - val) / val * 100, 3) if val else None,
    }


def _pivots(highs: list[float], lows: list[float], closes: list[float]) -> dict[str, Any]:
    if len(closes) < 2:
        return {}
    # prior completed bar as classic daily-style pivot seed
    h, lo, c = highs[-2], lows[-2], closes[-2]
    p = (h + lo + c) / 3
    r1 = 2 * p - lo
    s1 = 2 * p - h
    r2 = p + (h - lo)
    s2 = p - (h - lo)
    return {
        "pivot": round(p, 6),
        "r1": round(r1, 6),
        "s1": round(s1, 6),
        "r2": round(r2, 6),
        "s2": round(s2, 6),
    }


def _macd(closes: list[float]) -> dict[str, Any]:
    if len(closes) < 35:
        return {"crossover": None, "histogram": None}
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd_line: list[float] = []
    for a, b in zip(ema12, ema26):
        if a is None or b is None:
            macd_line.append(float("nan"))
        else:
            macd_line.append(a - b)
    # signal = EMA9 of macd_line (skip nans for seed)
    clean = [x for x in macd_line if x == x]
    if len(clean) < 10:
        return {"crossover": None, "histogram": None}
    sig_series = _ema(clean, 9)
    m = clean[-1]
    s = sig_series[-1]
    prev_m = clean[-2]
    prev_s = sig_series[-2]
    if s is None or prev_s is None:
        return {"macd_line": round(m, 6), "signal_line": None, "histogram": None, "crossover": None}
    hist = m - s
    cross = None
    if prev_m <= prev_s and m > s:
        cross = "Bullish"
    elif prev_m >= prev_s and m < s:
        cross = "Bearish"
    else:
        cross = "Bullish" if hist > 0 else "Bearish"
    return {
        "macd_line": round(m, 6),
        "signal_line": round(s, 6),
        "histogram": round(hist, 6),
        "crossover": cross,
    }


def _stochastic(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> dict[str, Any]:
    if len(closes) < period + 3:
        return {"k": None, "d": None, "signal": None}
    ks: list[float] = []
    for i in range(period - 1, len(closes)):
        window_h = max(highs[i - period + 1 : i + 1])
        window_l = min(lows[i - period + 1 : i + 1])
        denom = window_h - window_l
        k = 50.0 if denom == 0 else (closes[i] - window_l) / denom * 100
        ks.append(k)
    k_now = ks[-1]
    d_now = sum(ks[-3:]) / 3
    signal = "Overbought" if k_now >= 80 else ("Oversold" if k_now <= 20 else "Neutral")
    return {"k": round(k_now, 2), "d": round(d_now, 2), "signal": signal}


def _side(price: float, ema: float | None) -> str:
    if ema is None:
        return "?"
    return "above" if price >= ema else "below"


def _fmt(v: float | None) -> str:
    if v is None:
        return "n/a"
    return f"{v:.4g}"


def coin_analysis_usable(coin: Any) -> bool:
    if not isinstance(coin, dict):
        return False
    if coin.get("error") or coin.get("ok") is False:
        return False
    price = (coin.get("price_data") or {}).get("current_price")
    rsi = (coin.get("rsi") or {}).get("value")
    return price is not None or rsi is not None
