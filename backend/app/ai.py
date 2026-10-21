"""LLM layer: Claude (API key or Claude Code subscription), Cursor agents, or OpenAI."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .config import Settings, claude_cli, resolve_provider
from .schemas import ChatMessage, TradeLevels

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a crypto trading desk analyst. Be clear and brief — like gptchart.ai.

Hard rules:
- Max ~240 words of prose (not counting the JSON block).
- No markdown tables. No "data note" / outage essays. No walls of numbers.
- Use ONLY fields present in the snapshot. Skip missing fields — do not invent data.
- Bias must be exactly one of: Buy, Sell, Neutral.
- CRITICAL: Respect snapshot.confluence.bias as the preferred bias.
  * If confluence.score is between -2.4 and +2.4 → bias MUST be Neutral (range/wait).
  * If setup.trade_allowed is false OR setup.type is chop → bias MUST be Neutral (no trade).
  * You may keep Buy/Sell only when confluence agrees OR score |x|>=2.5.
  * Do NOT flip to the opposite of confluence.bias.
- Match plan style to setup.type: trend_continuation / breakout / mean_revert / chop.
- Give one primary trade plan with entry, stop_loss, take_profit as real prices near the snapshot price.
- Never use entry/stop/target = 0. Prefer snapshot.level_hints / pivots / S-R.
- Reward:risk must be at least 1.5:1 (|target-entry| >= 1.5 x |entry-stop|). Put the stop
  beyond structure but within ~2 ATR; if no target with 1.5R exists, bias MUST be Neutral.
- Weigh: setup, confluence, mtf, ADX, BB, VWAP, orderbook, liquidity map (long-cascade vs short-squeeze magnets), whales/funding/OI, regime.
- If liquidity.bias is Short-squeeze bias, favor longs only with confluence support; Long-cascade bias favors shorts/caution on longs.
- data_source binance_local is valid.
- Do not add disclaimers: no "not financial advice", no "I am not a financial adviser", no "do your own research" or risk-warning lines.

Full-analysis reply format (exactly this structure):

BIAS: Buy|Sell|Neutral
SETUP: chop|mean_revert|breakout|trend_continuation — trade ok? yes/no
SCORE: <confluence score>/10 — short note
TREND: Bullish|Bearish|Neutral — short note
MTF: 15m/1h/4h/1d one-liner
BOOK: orderbook bias / imbalance one-liner
LIQ: short-squeeze vs long-cascade | nearest long-liq / short-liq prices
FLOW: Whales … | Retail … | Funding … | OI … (one line)
REGIME: BTC … | risk mode …
ENTRY: <number or n/a>
STOP: <number or n/a>
TARGET: <number or n/a>
SUPPORT: <key support>
RESISTANCE: <key resistance>
R:R: <approx>
CONFIDENCE: <0-100>%

WHY:
- 4 short bullets max (setup/chop, MTF/confluence, book/whales, risk)

PLAN:
One sentence on the setup. One sentence on invalidation.

Then end with ONLY this JSON fence:
```json
{"bias":"Buy|Sell|Neutral","entry":0,"stop_loss":0,"take_profit":0,"support":0,"resistance":0,"support_2":0,"resistance_2":0,"trend":"Bullish","trend_line":"short note","ema20":0,"ema50":0,"confidence":0.0,"reasoning":"one short sentence"}
```
"""


def build_analysis_prompt(
    symbol: str,
    exchange: str,
    timeframe: str,
    market_block: str,
    custom_prompt: str | None = None,
) -> str:
    extra = f"\nTrader notes: {custom_prompt}" if custom_prompt else ""
    return f"""Full analysis: {exchange}:{symbol} · {timeframe}

Market snapshot (includes setup, confluence, MTF, orderbook, whales, regime):
{market_block}
{extra}

Follow BIAS/SETUP/SCORE/TREND/MTF/BOOK/LIQ/FLOW/REGIME/ENTRY/STOP/TARGET/SUPPORT/RESISTANCE.
Obey confluence + chop guardrails. Keep it scannable.
"""


def build_chat_prompt(
    symbol: str,
    exchange: str,
    timeframe: str,
    market_block: str,
    message: str,
    history: list[ChatMessage],
) -> str:
    hist = "\n".join(f"{m.role.upper()}: {m.content}" for m in history[-6:])
    hist_block = f"\nRecent chat:\n{hist}\n" if hist else ""
    return f"""Pair: {exchange}:{symbol} ({timeframe})

Snapshot:
{market_block}
{hist_block}
USER: {message}

Reply in under 120 words. If levels apply, lead with Bias / Entry / Stop / Target.
"""


def extract_levels(text: str) -> TradeLevels:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    raw = None
    if match:
        raw = match.group(1)
    else:
        match2 = re.search(
            r'\{\s*"bias"\s*:\s*"(Buy|Sell|Neutral)".*?\}',
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if match2:
            raw = match2.group(0)

    if not raw:
        bias = "Neutral"
        lower = text.lower()
        if re.search(r"\bbuy\b|\blong\b", lower) and not re.search(
            r"\bdo not buy\b|\bavoid buy\b", lower
        ):
            bias = "Buy"
        elif re.search(r"\bsell\b|\bshort\b", lower):
            bias = "Sell"
        return TradeLevels(bias=bias, reasoning="Parsed from narrative (no JSON block).")

    try:
        data = json.loads(raw)
        bias = str(data.get("bias", "Neutral")).title()
        if bias not in ("Buy", "Sell", "Neutral"):
            bias = "Neutral"
        return TradeLevels(
            bias=bias,  # type: ignore[arg-type]
            entry=_num(data.get("entry")),
            stop_loss=_num(data.get("stop_loss") or data.get("stopLoss")),
            take_profit=_num(data.get("take_profit") or data.get("takeProfit")),
            support=_num(data.get("support")),
            resistance=_num(data.get("resistance")),
            support_2=_num(data.get("support_2") or data.get("support2")),
            resistance_2=_num(data.get("resistance_2") or data.get("resistance2")),
            trend=str(data["trend"]) if data.get("trend") else None,
            trend_line=str(data["trend_line"]) if data.get("trend_line") else None,
            ema20=_num(data.get("ema20")),
            ema50=_num(data.get("ema50")),
            confidence=_confidence(data.get("confidence")),
            reasoning=str(data.get("reasoning") or ""),
        )
    except json.JSONDecodeError:
        return TradeLevels(bias="Neutral", reasoning="Could not parse levels JSON.")


def _num(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    # Model often emits 0 when data was missing — treat as absent
    if n == 0:
        return None
    return n


def _confidence(v: Any) -> float | None:
    """Accept 0–1 or 0–100 from the model; store as 0–1."""
    if v is None or v == "":
        return None
    try:
        n = float(str(v).strip().rstrip("%"))
    except (TypeError, ValueError):
        return None
    if n > 1:
        n = n / 100.0
    if n < 0:
        return None
    return min(n, 1.0)


def strip_json_fence(text: str) -> str:
    return re.sub(
        r"```json\s*\{.*?\}\s*```",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    ).strip()


def format_clear_brief(
    symbol: str,
    exchange: str,
    timeframe: str,
    levels: TradeLevels,
    raw_text: str,
) -> str:
    """Normalize model output into a short, scannable desk card."""
    body = strip_json_fence(raw_text)
    # If the model ignored the format, rebuild from levels + short excerpt
    conf = levels.confidence
    conf_pct = f"{int(round(conf * 100))}%" if conf is not None and conf <= 1 else (
        f"{int(conf)}%" if conf is not None else "—"
    )
    entry = _fmt_px(levels.entry)
    stop = _fmt_px(levels.stop_loss)
    target = _fmt_px(levels.take_profit)
    rr = _rr(levels.entry, levels.stop_loss, levels.take_profit)

    why = levels.reasoning.strip() if levels.reasoning else ""
    # Prefer model body if it already looks structured; else assemble
    if re.search(r"(?i)^BIAS\s*:", body, re.MULTILINE):
        cleaned = body
        # Drop trailing leftover JSON object if any
        cleaned = re.sub(
            r'\{\s*"bias"\s*:.*\}\s*$',
            "",
            cleaned,
            flags=re.DOTALL | re.IGNORECASE,
        ).strip()
        return cleaned

    lines = [
        f"{exchange}:{symbol} · {timeframe}",
        "",
        f"BIAS: {levels.bias}",
        f"TREND: {levels.trend or '—'} — {levels.trend_line or ''}".rstrip(" —"),
        f"ENTRY: {entry}",
        f"STOP: {stop}",
        f"TARGET: {target}",
        f"SUPPORT: {_fmt_px(levels.support)}"
        + (f" / {_fmt_px(levels.support_2)}" if levels.support_2 else ""),
        f"RESISTANCE: {_fmt_px(levels.resistance)}"
        + (f" / {_fmt_px(levels.resistance_2)}" if levels.resistance_2 else ""),
        f"EMA20/50: {_fmt_px(levels.ema20)} / {_fmt_px(levels.ema50)}",
        f"R:R: {rr}",
        f"CONFIDENCE: {conf_pct}",
        "",
        "WHY:",
        f"- {why}" if why else "- See plan below.",
    ]
    # Keep a short slice of model prose if useful
    prose = re.sub(r"(?i)^BIAS\s*:.*?(?=WHY:|PLAN:|$)", "", body, flags=re.DOTALL).strip()
    prose = re.sub(r"\n{3,}", "\n\n", prose)
    if prose and len(prose) < 600 and "BIAS:" not in prose[:40]:
        lines.extend(["", "PLAN:", prose[:500]])
    return "\n".join(lines)


def _fmt_px(v: float | None) -> str:
    if v is None:
        return "n/a"
    if abs(v) >= 1000:
        return f"{v:,.2f}"
    if abs(v) >= 1:
        return f"{v:.4g}"
    return f"{v:.6g}"


def _rr(entry: float | None, stop: float | None, target: float | None) -> str:
    if entry is None or stop is None or target is None:
        return "n/a"
    risk = abs(entry - stop)
    reward = abs(target - entry)
    if risk <= 0:
        return "n/a"
    return f"{reward / risk:.1f}:1"


async def generate_text(prompt: str, settings: Settings) -> tuple[str, str]:
    """Returns (text, provider_name)."""
    provider = resolve_provider(settings)
    if provider == "claude":
        text = await _claude_generate(prompt, settings)
        return text, "claude"
    if provider == "claude_code":
        text = await asyncio.to_thread(_claude_code_generate, prompt, settings)
        return text, "claude_code"
    if provider == "cursor":
        text = await _cursor_generate(prompt, settings)
        return text, "cursor"
    if provider == "openai":
        text = await _openai_generate(prompt, settings)
        return text, "openai"

    return (_offline_stub(prompt), "offline")


# Models that accept the server-side refusal fallback (`fallbacks: "default"`).
_CLAUDE_FALLBACK_MODELS = {
    "claude-fable-5-1",
    "claude-opus-5-5",
    "claude-opus-5",
    "claude-sonnet-5-5",
}


async def _claude_generate(prompt: str, settings: Settings) -> str:
    """Claude via the Anthropic Messages API (ANTHROPIC_API_KEY)."""
    import anthropic

    model = settings.anthropic_model.strip()
    request: dict[str, Any] = {
        "model": model,
        "max_tokens": 16000,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    effort = (settings.anthropic_effort or "").strip().lower()
    if effort:
        request["output_config"] = {"effort": effort}

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key.strip())
    try:
        if model in _CLAUDE_FALLBACK_MODELS:
            # A declined request is re-run on Anthropic's recommended fallback model.
            resp = await client.beta.messages.create(
                **request,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        else:
            resp = await client.messages.create(**request)
    except anthropic.AuthenticationError as exc:
        raise RuntimeError("Claude rejected ANTHROPIC_API_KEY — check backend/.env") from exc
    except anthropic.NotFoundError as exc:
        raise RuntimeError(f"Claude model not found: {model} (ANTHROPIC_MODEL)") from exc
    except anthropic.RateLimitError as exc:
        raise RuntimeError("Claude rate limit hit — wait a moment and retry") from exc
    except anthropic.APIStatusError as exc:
        raise RuntimeError(f"Claude API error {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise RuntimeError("Cannot reach the Claude API — check your network") from exc
    finally:
        await client.close()

    if resp.stop_reason == "refusal":
        raise RuntimeError("Claude declined this request")
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    if resp.stop_reason == "max_tokens":
        logger.warning("Claude reply hit max_tokens (request %s)", resp._request_id)
    return text


_NOT_LOGGED_IN = ("not logged in", "/login", "invalid api key", "oauth token", "authentication")


def _claude_code_generate(prompt: str, settings: Settings) -> str:
    """Claude through the local Claude Code CLI — billed to your Claude subscription.

    Runs `claude -p` headless with no tools, no MCP servers, no settings or
    CLAUDE.md files and no saved session, from an empty temp directory, so the
    model sees only our system prompt and the market snapshot. Blocking: call it
    via asyncio.to_thread (uvicorn's loop on Windows cannot spawn subprocesses).
    """
    cli = claude_cli(settings)
    if not cli:
        raise RuntimeError(
            "Claude Code CLI not found — install it (npm install -g @anthropic-ai/claude-code) "
            "or set CLAUDE_CODE_PATH in backend/.env"
        )

    env = os.environ.copy()
    # An API key in the environment would make the CLI bill the API instead of the plan.
    env.pop("ANTHROPIC_API_KEY", None)
    token = (settings.claude_code_oauth_token or "").strip()
    if token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token

    with tempfile.TemporaryDirectory(prefix="cca-claude-") as work:
        system_file = Path(work) / "system.md"
        system_file.write_text(SYSTEM_PROMPT, encoding="utf-8")
        cmd = [
            cli,
            "-p",
            "--output-format", "json",
            "--system-prompt-file", str(system_file),
            "--tools", "",
            "--strict-mcp-config",
            "--setting-sources", "",
            "--no-session-persistence",
        ]
        model = settings.claude_code_model.strip()
        if model:
            cmd += ["--model", model]
        effort = settings.claude_code_effort.strip().lower()
        if effort:
            cmd += ["--effort", effort]
        try:
            proc = subprocess.run(  # noqa: S603 — fixed argv, prompt goes in on stdin
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=work,
                env=env,
                timeout=settings.claude_code_timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Claude Code did not answer within {settings.claude_code_timeout}s (CLAUDE_CODE_TIMEOUT)"
            ) from exc

    out = (proc.stdout or "").strip()
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict) and not data.get("is_error") and data.get("result"):
        return str(data["result"])

    detail = str((data or {}).get("result") or proc.stderr or out or f"exit code {proc.returncode}").strip()
    if any(k in detail.lower() for k in _NOT_LOGGED_IN):
        raise RuntimeError(
            "Claude Code is not logged in — run `claude auth login`, or put a token from "
            "`claude setup-token` in CLAUDE_CODE_OAUTH_TOKEN"
        )
    raise RuntimeError(f"Claude Code error: {detail[-400:]}")


async def _cursor_generate(prompt: str, settings: Settings) -> str:
    """Run Cursor in a worker thread with its own event loop.

    Why: uvicorn's loop on Windows cannot create subprocesses for the SDK bridge
    (NotImplementedError), and the sync Agent.prompt fails too (WinError 10038).
    A fresh ProactorEventLoop in a worker thread works.
    """
    return await asyncio.to_thread(_cursor_generate_blocking, prompt, settings)


def _cursor_generate_blocking(prompt: str, settings: Settings) -> str:
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(_cursor_generate_async(prompt, settings))
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:  # noqa: BLE001
                pass
            loop.close()
            asyncio.set_event_loop(None)
    return asyncio.run(_cursor_generate_async(prompt, settings))


async def _cursor_generate_async(prompt: str, settings: Settings) -> str:
    from cursor_sdk import AgentOptions, AsyncAgent, AsyncClient, LocalAgentOptions

    workspace = str(Path(__file__).resolve().parents[1])
    full_prompt = f"{SYSTEM_PROMPT}\n\n---\n\n{prompt}"

    async with await AsyncClient.launch_bridge(workspace=workspace) as client:
        result = await AsyncAgent.prompt(
            full_prompt,
            AgentOptions(
                api_key=settings.cursor_api_key,
                model=settings.cursor_model,
                local=LocalAgentOptions(cwd=workspace),
            ),
            client=client,
        )

    if getattr(result, "status", None) == "error":
        raise RuntimeError(f"Cursor run error: {getattr(result, 'id', result)}")
    out = getattr(result, "result", None)
    if out is None:
        out = getattr(result, "text", None)
    return str(out if out is not None else result)


async def _openai_generate(prompt: str, settings: Settings) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content or ""


def _offline_stub(prompt: str) -> str:
    return (
        "No AI provider is selected or configured. Restart with start.ps1 / start.sh "
        "and pick one (Claude subscription, Claude API, Cursor or OpenAI), or set "
        "AI_PROVIDER and its key in backend/.env.\n\n"
        "Market context was still fetched successfully for this request — see the "
        "Market panel / API `market` field.\n\n"
        "```json\n"
        '{"bias":"Neutral","entry":null,"stop_loss":null,"take_profit":null,'
        '"confidence":0,"reasoning":"No LLM key configured"}\n'
        "```\n\n"
        f"(Prompt length received: {len(prompt)} chars)"
    )
