# AI providers

Four providers can write the analysis. All of them get the same system prompt and the same market snapshot, and their output goes through the same parsing and guardrails. The only thing that changes is who writes the prose and who pays for it.

| Provider | `AI_PROVIDER` | Credentials | Billed to |
|---|---|---|---|
| **Claude subscription** | `claude_code` | Your Claude Code login, or `CLAUDE_CODE_OAUTH_TOKEN` | Your Claude Pro / Max plan usage |
| **Claude API** | `claude` | `ANTHROPIC_API_KEY` | Anthropic API, per token |
| **Cursor** | `cursor` | `CURSOR_API_KEY` | Your Cursor plan |
| **OpenAI** | `openai` | `OPENAI_API_KEY` | OpenAI API, per token |
| No AI | `none` | none | none (market data and the deterministic plan only) |

Code: `backend/app/ai.py` (`generate_text` and one function per provider), `backend/app/config.py` (`resolve_provider`), `backend/app/choose_provider.py` (the startup menu).

## Choosing a provider at startup

`start.ps1` / `start.sh` install dependencies, then ask which AI to use:

```
  Crypto Chart AI - which AI should analyse?

  1) Claude subscription  your Claude Code login (Pro / Max plan)      [ready ] logged in (pro)   <- current
  2) Claude API           ANTHROPIC_API_KEY, billed per token          [setup ] needs key
  3) Cursor               CURSOR_API_KEY, Cursor agents                [setup ] needs key
  4) OpenAI               OPENAI_API_KEY                               [setup ] needs key
  5) No AI                market data and the deterministic plan only  [ready ] always available

Choose 1-5 (Enter = 1, q = quit):
```

- **Enter** keeps the current choice. **q** quits without starting.
- If the provider you pick isn't ready, the menu asks for what's missing: a key (typed hidden, then validated and saved to `backend/.env`), or for the Claude subscription, a sign-in (`claude auth login`) or a pasted `claude setup-token` token. Press Enter to skip and choose again.
- The choice is saved as `AI_PROVIDER` in `backend/.env`, so the next start offers it as the default.

Skip the menu:

```powershell
.\start.ps1 -Provider claude_code     # or claude | cursor | openai | none
.\start.ps1 -Keep                     # use AI_PROVIDER from backend\.env
```

```bash
./start.sh --provider claude_code
./start.sh --keep
```

The menu also runs on its own: `cd backend && uv run python -m app.choose_provider`. When it isn't run from a terminal (CI, a service), it keeps the `.env` value.

You can also switch by editing `AI_PROVIDER` in `backend/.env`. The server re-reads it on every request, so no restart is needed. `auto` picks the first configured provider in the order Claude API → Claude subscription (only when `CLAUDE_CODE_OAUTH_TOKEN` is set, so it never spends plan usage unasked) → Cursor → OpenAI.

`GET /api/health` reports the active provider and model, and so does the chip at the bottom of the rail in the UI.

## Claude subscription (Claude Code)

Uses **your Claude plan** instead of an API key, by running the Claude Code CLI headless on your own machine.

```bash
AI_PROVIDER=claude_code
CLAUDE_CODE_OAUTH_TOKEN=        # optional: from `claude setup-token`; blank = the CLI's own login
CLAUDE_CODE_MODEL=              # blank = your plan's default; or opus / sonnet / a full model id
CLAUDE_CODE_EFFORT=medium
CLAUDE_CODE_PATH=               # blank = find `claude` on PATH
CLAUDE_CODE_TIMEOUT=300         # seconds
```

**Setup:** install the CLI (`npm install -g @anthropic-ai/claude-code`) and sign in once with `claude auth login`. Check it with `claude auth status`. The startup menu does both checks and offers to sign you in.

**How each request runs** (`_claude_code_generate`):

```
claude -p --output-format json --system-prompt-file <tmp>/system.md
       --tools "" --strict-mcp-config --setting-sources "" --no-session-persistence
       [--model …] [--effort …]          # prompt goes in on stdin
```

- It runs from an empty temporary directory with **no tools, no MCP servers, no settings or CLAUDE.md files, and no saved session**. The model sees only the desk prompt and the market snapshot, and can't touch your files.
- `ANTHROPIC_API_KEY` is removed from the CLI's environment, so the call can't silently bill the API instead of your plan.
- A full analysis takes about 30 to 40 seconds and a short chat reply 5 to 15 seconds. It counts toward your plan's usage limits like any Claude Code message.
- Errors: `Claude Code is not logged in` (run `claude auth login` or set a token), `Claude Code CLI not found`, or `did not answer within …s` (raise `CLAUDE_CODE_TIMEOUT`).

> This uses your personal subscription on your own computer. Don't use it to serve other people. A shared deployment should use the Claude API.

## Claude API

```bash
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-opus-5-5
ANTHROPIC_EFFORT=medium
```

1. Create a key at [console.anthropic.com → Settings → API keys](https://console.anthropic.com/settings/keys) and add credit to the workspace.
2. Paste it into `backend/.env`. That's all.

### What the request looks like

Each analysis or chat turn is one call to the Messages API through the official `anthropic` Python SDK (`AsyncAnthropic`):

- `system` is the desk-analyst prompt (format rules plus the confluence guardrails).
- `messages` has one user turn: the pair, the condensed market snapshot (compact JSON, ≤ 8,000 chars, decision fields first), and either the analysis instructions or your question with the last 6 chat turns.
- `max_tokens` is 16,000. Replies are short, so this is only a ceiling.
- `output_config.effort` comes from `ANTHROPIC_EFFORT`. Claude Opus 5.5 always uses adaptive thinking, and effort controls how hard it thinks.
- **Refusal fallback**: on models that support it (`claude-opus-5-5`, `claude-opus-5`, `claude-sonnet-5-5`, `claude-fable-5-1`), the request goes through the beta endpoint with `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`). If a safety classifier declines a request, Anthropic re-runs it on its recommended fallback model inside the same call. If the whole chain still refuses, the API returns `502 AI error: Claude declined this request`.

### Choosing a model and effort

| Goal | Setting |
|---|---|
| Best analysis (default) | `claude-opus-5-5`, effort `medium` |
| Deeper reasoning on hard tapes | `claude-opus-5-5`, effort `high` |
| Faster and cheaper | `claude-sonnet-5-5`, effort `low` or `medium` |
| Cheapest, high volume | `claude-haiku-5-5`, effort `low` |

Pricing per million tokens (input / output) is about $4 / $20 for Opus 5.5, $2 / $10 for Sonnet 5.5, and $0.10 / $0.50 for Haiku 5.5. A full analysis sends roughly 2k to 3k input tokens.

### Errors you might see

The API returns `502` with one of these messages:

| Message | Cause |
|---|---|
| `Claude rejected ANTHROPIC_API_KEY` | Wrong, revoked, or mistyped key |
| `Claude model not found: …` | Typo in `ANTHROPIC_MODEL`, or your account has no access to that model |
| `Claude rate limit hit` | Too many requests per minute. Wait and retry. |
| `Claude API error 400: …` | Usually an `ANTHROPIC_EFFORT` value the model doesn't accept. Clear it. |
| `Cannot reach the Claude API` | Network, proxy, or firewall problem |

## Cursor

```bash
AI_PROVIDER=cursor
CURSOR_API_KEY=crsr_...
CURSOR_MODEL=composer-2.5
```

Create a key at [cursor.com/dashboard/integrations](https://cursor.com/dashboard/integrations). Uses `cursor-sdk`, which starts a local bridge subprocess. On Windows that subprocess needs a Proactor event loop, so the call runs in a worker thread with its own loop (`_cursor_generate_blocking`).

## OpenAI

```bash
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Uses Chat Completions with `temperature=0.3`.

## Offline mode (no key)

With no configured provider, `/api/analyze` still fetches the full market snapshot and returns a deterministic plan. The plan's levels come from the local technical analysis, and its bias comes from the confluence score. The reply explains that no key is set, and `provider` is `"offline"`. This is handy for checking the data pipeline without spending credits.

Offline plans are **not** archived as [signals](features/signals.md). The track record only holds calls an AI actually made.

## What happens to the reply

The provider only writes text. The backend then:

1. **Parses** the JSON block the prompt asks for (`extract_levels`). If there isn't one, it falls back to a keyword scan.
2. **Fills gaps** in entry, stop, target, support, resistance and EMAs from the local `suggested_levels` (`_fill_levels_from_market`).
3. **Applies the guardrail** (`_apply_confluence_guardrail`). The AI's bias is overridden when it disagrees with the deterministic [confluence score](features/confluence-score.md):
   - Setup blocked by the chop filter → **Neutral**, confidence capped at 40%.
   - |score| < 2.5 → **Neutral**.
   - The opposite side of a Buy or Sell confluence is never allowed.
   - |score| ≥ 3.5 with an AI answer of Neutral → upgraded to the confluence bias.
   - Confidence is the average of the AI's figure and the confluence figure.
4. **Checks reward:risk** (`_apply_reward_risk_guard`). A Buy or Sell becomes **Neutral** if its levels are on the wrong side of the entry (a Buy needs stop < entry < target) or if it pays less than **1:1**. The prompt also asks the model for at least 1.5:1, with the stop beyond structure but within about 2 ATR.
5. **Formats** the desk card (`format_clear_brief`). If steps 3 or 4 changed the model's bias, a `DESK OVERRIDE:` line is added at the top of the reply, so the text and the plan never disagree silently.

The AI explains and plans; it cannot overturn the score.
