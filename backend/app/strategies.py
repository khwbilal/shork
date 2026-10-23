"""Strategy registry for GPTChart-style analysis packs (WL-050, WL-053)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RiskProfile:
    """Per-strategy stop width and live-review stance bands (WL-053).

    Stop bands clamp suggested levels and steer the AI prompt.
    Review bands drive Hold / Caution / Exit early on live review.
    A full stop-out is still -1R by definition of R.
    """

    stop_atr_min: float = 0.75
    stop_atr_max: float = 2.0
    min_reward_risk: float = 1.5  # prompt ask; hard guard floor stays 1:1
    target_r_min: float = 2.0
    review_near_stop_r: float = 0.35
    review_hold_min_r: float = -0.35
    review_hold_max_r: float = 0.70
    review_exit_loss_r: float = -0.60
    review_bank_target_frac: float = 0.85
    review_chop_band_r: float = 0.15


@dataclass(frozen=True)
class Strategy:
    id: str
    label: str
    summary: str
    primary_tf: str | None  # None = use desk TF
    context_tfs: tuple[str, ...] = ()
    # Desk TFs that are too slow / too fast for this pack; primary_tf then wins.
    incompatible_desk_tfs: tuple[str, ...] = ()
    indicators: tuple[str, ...] = ()
    prompt_rules: str = ""
    uses_desk_pipeline: bool = False
    needs_liquidity: bool = False
    needs_orderbook: bool = False
    risk: RiskProfile = RiskProfile()


_STRATEGIES: dict[str, Strategy] = {}


def _reg(s: Strategy) -> Strategy:
    _STRATEGIES[s.id] = s
    return s


_reg(
    Strategy(
        id="desk",
        label="Desk (default)",
        summary="Full confluence, setup classifier, MTF, order book, liquidity and flow.",
        primary_tf=None,
        context_tfs=(),
        indicators=(),
        prompt_rules="",
        uses_desk_pipeline=True,
        needs_liquidity=True,
        needs_orderbook=True,
        risk=RiskProfile(),
    )
)

_reg(
    Strategy(
        id="smc",
        label="Smart Money Concepts",
        summary="Market structure, BOS/CHoCH, equal highs/lows and nearby liquidity.",
        primary_tf="15m",
        context_tfs=("1h", "4h"),
        incompatible_desk_tfs=("1d", "1D", "1w", "1W"),
        indicators=("ema", "atr", "swings", "structure", "equal_levels", "rsi"),
        prompt_rules=(
            "Playbook: Smart Money Concepts. Prefer entries after a break of structure "
            "(BOS) or change of character (CHoCH) that aligns with the higher-TF bias. "
            "Stops beyond the invalidating swing or swept liquidity pool. Targets at the "
            "next equal high/low or opposing liquidity. Neutral when structure is mixed "
            "or no clear BOS/CHoCH in the pack."
        ),
        needs_liquidity=True,
        needs_orderbook=True,
        risk=RiskProfile(
            stop_atr_min=1.0,
            stop_atr_max=3.0,
            min_reward_risk=1.5,
            target_r_min=1.5,
            review_near_stop_r=0.25,
            review_hold_min_r=-0.50,
            review_hold_max_r=1.00,
            review_exit_loss_r=-0.75,
            review_bank_target_frac=0.90,
            review_chop_band_r=0.20,
        ),
    )
)

_reg(
    Strategy(
        id="liquidity_sweep",
        label="Liquidity Sweep",
        summary="Equal high/low sweeps with rejection, book walls and liquidation magnets.",
        primary_tf="15m",
        context_tfs=("1h",),
        incompatible_desk_tfs=("1d", "1D", "1w", "1W"),
        indicators=("atr", "swings", "equal_levels", "rsi", "relative_volume"),
        prompt_rules=(
            "Playbook: Liquidity Sweep. Look for a wick through equal highs or lows "
            "(or a nearby liq magnet) then a close back inside the range. Enter with "
            "the reclaim; stop beyond the sweep extreme; target the opposite side of "
            "the range or mid-range. Neutral if no sweep and reclaim is present."
        ),
        needs_liquidity=True,
        needs_orderbook=True,
        risk=RiskProfile(
            stop_atr_min=0.5,
            stop_atr_max=1.5,
            min_reward_risk=1.5,
            target_r_min=1.5,
            review_near_stop_r=0.40,
            review_hold_min_r=-0.30,
            review_hold_max_r=0.55,
            review_exit_loss_r=-0.45,
            review_bank_target_frac=0.80,
            review_chop_band_r=0.12,
        ),
    )
)

_reg(
    Strategy(
        id="breakout",
        label="Breakout",
        summary="Range break with volume and ADX confirmation.",
        primary_tf="1h",
        context_tfs=("4h",),
        incompatible_desk_tfs=("1m", "5m"),
        indicators=("atr", "adx", "relative_volume", "bollinger", "swings", "ema"),
        prompt_rules=(
            "Playbook: Breakout. Prefer a close beyond recent range high/low with "
            "relative volume elevated and ADX showing trend strength. Stop back inside "
            "the broken range; target at least 1.5R using ATR or the next swing. "
            "Neutral on low volume or ADX weak."
        ),
        risk=RiskProfile(
            stop_atr_min=0.75,
            stop_atr_max=2.5,
            min_reward_risk=1.5,
            target_r_min=2.0,
            review_near_stop_r=0.30,
            review_hold_min_r=-0.40,
            review_hold_max_r=0.90,
            review_exit_loss_r=-0.70,
            review_bank_target_frac=0.85,
            review_chop_band_r=0.15,
        ),
    )
)

_reg(
    Strategy(
        id="pullback",
        label="Pullback",
        summary="Trend continuation after a pullback to EMA or structure.",
        primary_tf="1h",
        context_tfs=("4h",),
        incompatible_desk_tfs=("1m", "5m"),
        indicators=("ema", "rsi", "atr", "swings", "adx"),
        prompt_rules=(
            "Playbook: Pullback. Higher TF trend must be clear. Enter when price pulls "
            "into EMA20/50 or a prior swing and shows rejection with RSI not extreme "
            "against the trend. Stop beyond the pullback extreme; target prior swing "
            "or 1.5R+. Neutral in chop or when ADX is weak."
        ),
        risk=RiskProfile(
            stop_atr_min=0.75,
            stop_atr_max=2.0,
            min_reward_risk=1.5,
            target_r_min=1.5,
            review_near_stop_r=0.30,
            review_hold_min_r=-0.35,
            review_hold_max_r=0.80,
            review_exit_loss_r=-0.65,
            review_bank_target_frac=0.85,
            review_chop_band_r=0.15,
        ),
    )
)

_reg(
    Strategy(
        id="retracement",
        label="Retracement",
        summary="Fibonacci pullback into an established trend.",
        primary_tf="1h",
        context_tfs=("4h",),
        incompatible_desk_tfs=("1m", "5m"),
        indicators=("ema", "rsi", "atr", "fibonacci", "swings"),
        prompt_rules=(
            "Playbook: Retracement. Identify the last impulse swing and Fib levels "
            "(38.2, 50, 61.8). Prefer entries near 50 to 61.8 that agree with EMA trend. "
            "Stop beyond 78.6 or the swing extreme; target the prior high/low or extension. "
            "Neutral if price is mid-Fib with no reaction."
        ),
        risk=RiskProfile(
            stop_atr_min=1.0,
            stop_atr_max=2.5,
            min_reward_risk=1.5,
            target_r_min=2.0,
            review_near_stop_r=0.25,
            review_hold_min_r=-0.45,
            review_hold_max_r=1.00,
            review_exit_loss_r=-0.75,
            review_bank_target_frac=0.90,
            review_chop_band_r=0.18,
        ),
    )
)

_reg(
    Strategy(
        id="scalping",
        label="Scalping",
        summary="Short-TF momentum around VWAP with tight ATR stops.",
        primary_tf="5m",
        context_tfs=("15m",),
        incompatible_desk_tfs=("4h", "1d", "1D", "1w", "1W"),
        indicators=("vwap", "rsi", "stochastic", "atr", "ema", "relative_volume"),
        prompt_rules=(
            "Playbook: Scalping. Trade with 15m bias; use 5m for entry. Prefer reclaim "
            "or rejection of VWAP with RSI/Stoch confirmation. Tight stop (about 0.5 to "
            "1 ATR); target 1.5R or the next micro swing. Neutral when VWAP is flat and "
            "momentum is mixed."
        ),
        needs_orderbook=True,
        risk=RiskProfile(
            stop_atr_min=0.5,
            stop_atr_max=1.0,
            min_reward_risk=1.5,
            target_r_min=1.5,
            review_near_stop_r=0.45,
            review_hold_min_r=-0.25,
            review_hold_max_r=0.50,
            review_exit_loss_r=-0.40,
            review_bank_target_frac=0.75,
            review_chop_band_r=0.10,
        ),
    )
)

_reg(
    Strategy(
        id="ema_volatility",
        label="EMA Volatility",
        summary="EMA trend with Bollinger squeeze and ATR expansion.",
        primary_tf="15m",
        context_tfs=("1h",),
        incompatible_desk_tfs=("1m",),
        indicators=("ema", "bollinger", "atr", "adx", "rsi", "squeeze"),
        prompt_rules=(
            "Playbook: EMA Volatility. Prefer trades when EMA20/50 align and a Bollinger "
            "squeeze (narrow band width) has just expanded in the trend direction. "
            "Stop beyond the opposite band or 1 ATR; target 1.5R+. Neutral inside a "
            "tight squeeze with no expansion."
        ),
        risk=RiskProfile(
            stop_atr_min=0.75,
            stop_atr_max=1.5,
            min_reward_risk=1.5,
            target_r_min=1.5,
            review_near_stop_r=0.35,
            review_hold_min_r=-0.35,
            review_hold_max_r=0.70,
            review_exit_loss_r=-0.55,
            review_bank_target_frac=0.85,
            review_chop_band_r=0.15,
        ),
    )
)


def risk_public(risk: RiskProfile) -> dict[str, Any]:
    return asdict(risk)


def review_thresholds(strategy_id: str | None) -> dict[str, float]:
    """Live-review stance bands for a strategy id (desk if unknown)."""
    r = get_strategy(strategy_id).risk
    return {
        "near_stop_r": r.review_near_stop_r,
        "hold_min_r": r.review_hold_min_r,
        "hold_max_r": r.review_hold_max_r,
        "exit_loss_r": r.review_exit_loss_r,
        "bank_target_frac": r.review_bank_target_frac,
        "chop_band_r": r.review_chop_band_r,
    }


def list_strategies() -> list[dict[str, Any]]:
    """Public catalog for GET /api/strategies."""
    out = []
    for s in _STRATEGIES.values():
        out.append(
            {
                "id": s.id,
                "label": s.label,
                "summary": s.summary,
                "primary_tf": s.primary_tf,
                "context_tfs": list(s.context_tfs),
                "incompatible_desk_tfs": list(s.incompatible_desk_tfs),
                "indicators": list(s.indicators),
                "uses_desk_pipeline": s.uses_desk_pipeline,
                "risk": risk_public(s.risk),
            }
        )
    return out


def get_strategy(strategy_id: str | None) -> Strategy:
    sid = (strategy_id or "desk").strip().lower() or "desk"
    return _STRATEGIES.get(sid) or _STRATEGIES["desk"]


def resolve_timeframes(strategy: Strategy, desk_tf: str) -> tuple[str, list[str], bool]:
    """Return (primary_tf, context_tfs, overridden).

    Desk pipeline uses the desk TF. Named strategies always own their primary_tf
    and still return every context_tf (excluding a duplicate of primary).
    """
    from .binance_ta import normalize_timeframe

    desk = normalize_timeframe(desk_tf)
    if strategy.uses_desk_pipeline or strategy.primary_tf is None:
        primary = desk
        overridden = False
    else:
        primary = normalize_timeframe(strategy.primary_tf)
        overridden = primary != desk
    context = [
        normalize_timeframe(t)
        for t in strategy.context_tfs
        if normalize_timeframe(t) != primary
    ]
    return primary, context, overridden


def needed_timeframes(strategy: Strategy, desk_tf: str) -> list[str]:
    """Ordered unique list: primary then every context TF."""
    primary, context, _ = resolve_timeframes(strategy, desk_tf)
    out = [primary]
    for tf in context:
        if tf not in out:
            out.append(tf)
    return out


def strategy_public(strategy: Strategy) -> dict[str, Any]:
    return {
        "id": strategy.id,
        "label": strategy.label,
        "summary": strategy.summary,
        "primary_tf": strategy.primary_tf,
        "context_tfs": list(strategy.context_tfs),
        "uses_desk_pipeline": strategy.uses_desk_pipeline,
        "risk": risk_public(strategy.risk),
    }
