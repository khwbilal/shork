# Project state & handoff

**Last updated:** 2026-10-22. Read this first when picking the project back up. It records what has been built, why, how it was verified, and what is still open. The rest of `docs/` describes *how things work*; this page describes *where things stand*.

> ⚠ **This folder is not a git repository**, so there is no history to diff or revert against. The user chose to **leave git out for now** (2026-10-21): don't initialise it or suggest it. Back up a file (e.g. to the scratchpad) before a risky edit instead.

## What the project is

A local crypto analysis desk: a TradingView chart plus an AI analyst. The FastAPI backend (`backend/app/`) builds a market snapshot (TradingView TA with a Binance fallback, MTF, whale flow, order book, liquidation map), scores it deterministically (confluence −10…+10 and a setup classifier), and asks an AI for a trade plan that the backend then **enforces** against that score. There are two frontends with the same features and one shared stylesheet. Start with [README](README.md) for the doc map.

## Work done so far (sessions on 2026-10-21)

### 1. AI providers: four, chosen at startup

| `AI_PROVIDER` | What it uses | Status |
|---|---|---|
| `claude_code` | **The user's Claude Pro subscription**, via the local Claude Code CLI (`claude -p`) | ✅ Verified with 3 real analyses. **This is the user's current choice** (`backend/.env`). |
| `claude` | Anthropic API, `ANTHROPIC_API_KEY`, `claude-opus-5-5`, effort `medium`, `fallbacks: "default"` refusal fallback | ⚠ Code verified up to auth (a fake key returns the right 401 message). **Never run with a real key**, because the user hasn't provided one. |
| `cursor` | `cursor-sdk`, `CURSOR_API_KEY` | ⚠ Original author's code, restored as-is. **Not tested** (no key). |
| `openai` | OpenAI Chat Completions | ⚠ Original author's code, **not tested** (no key). |
| `none` | No AI: deterministic plan only, `provider: "offline"` | ✅ Verified |

- **Startup menu:** `backend/app/choose_provider.py`, called by `start.ps1` / `start.sh` after `uv sync`. It shows readiness per provider, asks for missing keys (hidden input, validated, written to `.env`) or offers `claude auth login` / a `claude setup-token` token, and saves `AI_PROVIDER`. Flags: `-Keep` / `--keep`, `-Provider X` / `--provider X`. With no TTY it keeps the `.env` value. Verified by simulated input (pick → skip → re-pick, and pasting a key) and by running `start.ps1 -Keep` for real.
- **The Claude subscription call** (`ai.py:_claude_code_generate`) runs from an empty temp directory with `--tools "" --strict-mcp-config --setting-sources "" --no-session-persistence --system-prompt-file`, with the prompt on stdin. It strips `ANTHROPIC_API_KEY` from the child environment so the plan is always what gets billed. It's blocking, so it runs through `asyncio.to_thread`.
- **Decision history:** session 1 added Claude API next to Cursor. Session 2 removed Cursor at the user's request. Session 3 brought Cursor back because the user wanted it in the startup menu, and added the subscription option ("use my claude tokens").

### 2. Analysis-quality fixes (all providers)

- **Snapshot truncation (the most impactful fix):** `market.py:context_to_prompt_block` used to pretty-print about 6.5k characters and cut at 5k, which **dropped `confluence` and `setup`**, so the AI never saw the score it was meant to respect. It now uses compact JSON, drops empty values, puts the decision fields first, caps at 8k, and drops low-value sections whole. Typical size is now about 4.5k. Verified: Claude now quotes the score ("SCORE: 8.6/10").
- **Reward:risk:**
  - `binance_ta.py` local levels: stop ATR bands and min target R come from each strategy's `RiskProfile` (desk default 0.75 to 2 ATR, 2R). Live-review stance bands are strategy-owned too (WL-053).
  - `main.py:_apply_reward_risk_guard`: a Buy/Sell with levels on the wrong side of entry, or below 1:1, becomes Neutral.
  - The prompt asks for at least 1.5R.
  - **All strategies** (WL-054): Desk can run every pack with `optimize_mode` `local_score` / `majority_vote` / `ai_ensemble`; packs land in `multi_analysis_json`; detail at `#/signals/{id}`; live review may append revised SL/TP without changing the original plan.
- **`DESK OVERRIDE:` line:** added to the reply when the guardrails change the model's bias, so the text and the plan never disagree silently.
- **Offline plans are no longer archived as signals.** Only real AI calls go into the track record.
- **Symbol search:** `<q>USDT` ranks first, the selected exchange's pairs come before other venues, and the bogus `ALL:` pseudo-exchange from the TradingView coin list is dropped.

### 3. UI redesign (inspired by `C:\IT22\unefy-platform`)

- The built-in UI (`backend/app/static/`, no build step) was rebuilt in Unefy's design language: tokens on `:root`, `--action` vs `--brand`, a 224/64px collapsible rail, a 52px top bar, Ctrl K palette, KPI strips, widget cards, glyph + colour pills, em dash for missing data, light/dark/system themes, an in-app dialog instead of `prompt()`, mobile layout. See [ui.md](ui.md).
- **React UI** (`frontend/`, Vite + React 19 + strict TS): a full port with the same four pages. It **imports `backend/app/static/app.css`** (`vite.config.ts` has `fs.allow: [".."]`), so one stylesheet serves both UIs.
- Verified with Playwright screenshots (Unefy's `node_modules/playwright`), desktop and phone, light and dark: no page errors and no horizontal overflow.

### 4. Docs and tooling

- `docs/` was created: 21 pages, all links checked (66 relative links, 0 broken). `mac-setup.md` moved into `docs/`.
- `CLAUDE.md` (project notes for Claude Code) and `.mcp.json` (TradingView MCP for Claude Code) were added. `.cursor/` was deleted in session 2 and not restored; only the IDE config is gone, the Cursor *provider* is back.
- `uv` 0.13.4 is installed with the official installer and is on the user PATH. `backend/.venv` uses Python 3.13 with all dependencies, and `frontend/node_modules` is installed.

### 5. Tests, lint and docs style (session 4, 2026-10-21)

- **WL-018:** 95 offline pytest tests in `backend/tests/`. They cover provider choice, both guards, the prompt block, symbol ranking and the `.env` writer, and run in under a second.
- **WL-019:** ruff (default rules, lint only) for the backend and ESLint 9 for `frontend/`. Both are clean. Four small fixes kept behaviour the same, including a repeated `bb_squeeze` key in `market.condense_market_context`. See [Tests and lint](testing-and-lint.md).
- **WL-020:** em and en dashes swept from the docs. Links were checked: 137, 0 broken.
- **New bugs found by the tests:** WL-026 (a confidence of 0.0 becomes 0.4 when the trade is blocked) and WL-027 (the prompt block can be 14 characters over budget). A policy case was added to WL-021.
- **Gate:** pytest, ruff and ESLint joined the gate (ruleset 1.1, approved by Sheryar).

### 6. Database, jobs, catalogue and calendar (session 5, 2026-10-21)

Sheryar asked for a database, a daily backup, Binance stocks in the database, MUI, and a calendar, then logged a long plan as WL-028 to WL-048.

- **WL-028:** SQLite at `backend/data/app.db` holds journal and signals ([Database](database.md), [decision 0007](decisions/0007-sqlite.md)). The one real signal was imported from JSON.
- **WL-029 and WL-030:** scheduled jobs through Task Scheduler. The `backup` job runs daily at 20:00 to `backups/YYYY-MM-DD.db` and keeps 30 copies. A restore was tested ([Scheduled jobs](scheduled-jobs.md)).
- **WL-040 and WL-044:** 2,183 Binance instruments with names are stored in the database: crypto, 180 stock perps, 32 ETFs, commodities, and the bStocks on spot ([Binance instruments](binance-instruments.md)). Search finds them by name. The `instruments` job runs daily at 15:30.
- **WL-039, plus part of WL-045:** the calendar covers today plus 7 days, with US macro, earnings of Binance-listed stocks and Binance announcements. The `calendar` job runs daily at 16:00 ([Calendar](features/calendar.md)). It has no page yet.
- **Decided by Sheryar:** SQLite; MUI everywhere (option 2). The MUI conversion (WL-047) waits on Sheryar's ok to the ruleset diff that retires the built-in UI.
- **Done on 2026-10-22:** WL-026 and WL-027 (bug fixes), WL-043 (no disclaimers anywhere), WL-036 (`/api/correlation`, in the snapshot and the prompt), the WL-035 backend (`/api/pulse`). 170 tests pass.
- **Ruleset 1.2** (approved 2026-10-22): React + MUI is the only portal ([decision 0008](decisions/0008-react-mui-only.md)). The built-in UI in `backend/app/static/` is frozen until WL-047 removes it.

### Resume here (next session)

1. **WL-047 phases A and B** (the MUI portal in `frontend/`) were stopped at a safe point at handover. Read the WL-047 entry in the work log for the checklist of what is done and what is left, then continue. Backups of the pre-MUI frontend and static UI are in the scratchpad folder `backup-wl047` (session scratchpad; it may be gone, so in that case the old UI still lives in `backend/app/static/`).
2. **WL-047 phase C:** FastAPI serves `frontend/dist` at `/`, the start scripts run `npm run build` first, `backend/app/static/` is removed, `ui.md` is rewritten for MUI, and the CLAUDE.md and ruleset paths are checked.
3. Then the functional items in order: WL-031 strategies, WL-033 backtester, WL-034, WL-037 picks, WL-038 paper trades, WL-042 hype radar, WL-041 stocks in analysis, WL-046 financials, and WL-032 notes.
- **Leave alone:** PIDs 8208 and 25772 (`python.exe -`) belong to a separate project of Sheryar's.
- **Working style:** Sheryar wants short updates and less talk (memory `less-talk`).

## Current local state

- `backend/.env` exists with `AI_PROVIDER=claude_code` and **no API keys** (all key fields are blank). Don't print or commit its contents.
- `backend/data/app.db` (SQLite, migrations 001 to 004) holds 1 real signal (SOLUSDT, open), 0 journal rows, 2,183 instruments and the calendar. `signals.json.imported` is the original file.
- `backups/2026-10-21.db` is the first backup.
- Task Scheduler folder `\CryptoChartAI\` has three tasks: `instruments` at 15:30, `calendar` at 16:00 and `backup` at 20:00. Read `GET /api/jobs` for results, not the Task Scheduler column (WL-048).
- The user is logged into Claude Code with a **Pro** plan (`claude auth status`). The CLI is at `…\AppData\Roaming\npm-global\claude.CMD`.

## How to verify things quickly

```bash
cd backend
.venv/Scripts/python.exe -m compileall -q app            # syntax
.venv/Scripts/python.exe -m pytest -q                    # 95 offline tests
.venv/Scripts/python.exe -m ruff check app tests         # Python lint
(cd ../frontend && npm run lint)                         # ESLint
node --check app/static/app.js                           # built-in UI
(cd ../frontend && npx tsc -b && npm run build)          # React UI, strict TS
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8765   # then:
curl -s http://127.0.0.1:8765/api/health
curl -s -X POST http://127.0.0.1:8765/api/analyze -H "Content-Type: application/json" -d '{"symbol":"BTCUSDT","timeframe":"4h"}'
```

- `/api/analyze` with `AI_PROVIDER=claude_code` spends real plan usage (about 30 to 40 s per call). Use `AI_PROVIDER=none` for pipeline-only checks.
- The server logs `analyze <pair> <tf> via <provider> -> <bias>` and warns when a pinned provider isn't configured.
- Interactive menu test without a TTY: patch `builtins.input`, `getpass.getpass` and `sys.stdin.isatty`, then call `choose_provider.main([])`. Back up `.env` first and restore it afterwards.

## Gotchas learned the hard way (Windows)

- **Stopped test servers keep running** ([incident WL-025](incidents/WL-025.md)). Stopping a background task ends only its `bash.exe` wrapper; `npx` / `node vite.js` and uvicorn's `--reload` worker (`spawn_main`, whose command line has no "uvicorn") survive and keep the port. After every test server, check `Get-NetTCPConnection -LocalPort <port> -State Listen` and stop the whole tree. Prefer test backends without `--reload`.
- Vite binds to `localhost` (IPv6) only. Browse to `http://localhost:5173`, not `127.0.0.1:5173`.
- The Python console is cp1252. Non-ASCII output (`→`, `—`) can crash prints or turn into `�` / `\u2192` in logs, so set `PYTHONIOENCODING=utf-8` for ad-hoc scripts. The chooser and log lines are kept ASCII on purpose.
- `claude.CMD` takes empty-string arguments (`--tools ""`) correctly; this was verified.
- Uvicorn's event loop on Windows can't spawn subprocesses. Any subprocess-based provider must run in a thread (`asyncio.to_thread`); Cursor also needs its own Proactor loop.
- Long bash heredocs with backticks or quotes broke the Bash tool. For big scripted edits, write a `.js` file to the scratchpad and run it.
- In Playwright, `text=Full analysis` also matches greeting text (case-insensitive substring). Use `button.btn.primary`.
- TradingView's public TA often rate-limits (`JSONDecodeError` retries in the log). The Binance fallback handles it, so this is normal.
- VS Code copies PATH when it starts. After uv was installed, its terminals still could not find `uv` until VS Code was reopened. `start.ps1` and the full path `%USERPROFILE%\.local\bin\uv.exe` both work in the meantime.
- Agent edits turned LF source files into CRLF (WL-019). After edits, `file backend/app/*.py | grep CRLF` should print nothing.

## Open issues / ideas for next time

Open work is tracked in the **[work log](work-log.md)**. That table is authoritative; this summary was taken on 2026-10-21:

| Item | What | Status |
|---|---|---|
| WL-022 | certifi CRITICAL (Trivy), fixed by a lock bump to 2026.10.19; Trivy now clean | done 2026-10-21 |
| WL-023, WL-024 | Python and npm patch/minor bumps: fastapi 0.157, vite 6.4.5 and others | done 2026-10-21 |
| WL-025 | Majors: Vite 8 + plugin-react 6 and TS 6 pass in trials; TS 7 blocked by typescript-eslint | assessed; awaiting decision |
| WL-047 | Convert the portal to MUI (calendar page, autocomplete, pulse widget, job status) | in progress; approved (ruleset 1.2) |
| WL-048 | Task Scheduler shows 0 when a job fails | open |
| WL-045 | BNB burn, token unlocks: need a keyed source (CoinMarketCal) | needs Sheryar |
| WL-031 to WL-038, WL-041, WL-042, WL-046 | Strategies, backtests, picks, paper trades, stocks in analysis, hype radar, financials | open; see the work log for order and dependencies |
| WL-026, WL-027, WL-043, WL-036 | Two bug fixes, no disclaimers, correlation | done 2026-10-22 |
| WL-035 | BTC and ETH pulse: backend done, widget in WL-047 | partly done |
| WL-021 | May the confluence guard override an AI "Neutral"? Also: a Neutral bias with a strong score lets the model's Buy or Sell pass | needs Sheryar |
| WL-020 | Writing-style sweep of the docs | done 2026-10-21 |
| WL-019, WL-018 | Lint tooling (ruff, ESLint) and 95 pytest tests; in the gate since ruleset 1.1 | done 2026-10-21 |
| WL-017 | Claude API, Cursor, OpenAI untested with real keys | blocked; needs keys |
| WL-016 | One unexplained offline response ([incident](incidents/WL-016.md)) | open; not reproduced |

Standing notes: expired-signal R is marked to market and journal R needs an exit price (documented, fine). There is no auth, so the server must stay on `127.0.0.1`; the subscription provider is for personal local use only.

## Way of working

Since WL-015 every session follows [reference/ruleset.md](reference/ruleset.md) (adapted from unefy-platform, see [decision 0006](decisions/0006-unefy-way-of-working.md)): issue first in the work log, the main chat does every item (no sub agents since ruleset 1.3), docs pass last, real exit codes, no git.

## Files changed or added (high level)

| Area | Files |
|---|---|
| Providers & startup | `backend/app/config.py`, `ai.py`, `choose_provider.py` (new), `start.ps1`, `start.sh`, `backend/.env.example`, `backend/pyproject.toml` (+`anthropic`, `cursor-sdk`), `uv.lock` |
| Analysis fixes | `backend/app/main.py`, `market.py`, `binance_ta.py`, `symbols.py`, `schemas.py` (`ai_model` in health) |
| Built-in UI | `backend/app/static/index.html`, `app.css`, `app.js` (rewritten) |
| React UI | `frontend/src/**` (rewritten), `index.html`, `vite.config.ts`, `package.json` (dropped `react-markdown`) |
| Docs & meta | `docs/**` (new), `README.md`, `CLAUDE.md` (new), `.mcp.json` (new), `.gitignore` |
| Database, jobs, catalogue, calendar (session 5) | `backend/app/db.py`, `migrations/001-004`, `jobs/`, `instruments.py`, `calendar_feed.py`, `app/data/instrument_names.json` (all new); `journal.py`, `signals.py`, `symbols.py`, `market.py`, `main.py`, `schemas.py`, `config.py`, `.env.example`; `scripts/jobs/` (new), `backups/` (new), `.gitignore`; docs `database.md`, `scheduled-jobs.md`, `binance-instruments.md`, `features/calendar.md`, `decisions/0007-sqlite.md` (new) |
| Tests & lint (session 4) | `backend/tests/**` (new), `backend/pyproject.toml` (dev group: pytest, ruff), `uv.lock`, `frontend/eslint.config.js` (new), `frontend/package.json`, `package-lock.json`, lint fixes in `backend/app/binance_ta.py`, `confluence.py`, `market.py`, `symbols.py`; `docs/testing-and-lint.md` (new) |
