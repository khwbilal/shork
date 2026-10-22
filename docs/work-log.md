# Work log

The issue-first record for this repo ([ruleset](reference/ruleset.md) section 1). One item per unit of work, newest first, id `WL-nnn`. Log an item before its first code edit; a done item keeps its row with the outcome. Take the next free id from the top of the table. Never invent hours or dates: write "to fill in".

Items WL-001 to WL-014 were logged retroactively on 2026-10-21, when the ruleset was adopted (WL-015); their details come from [project-state.md](project-state.md).

| Id | Title | Status |
|---|---|---|
| WL-048 | Task Scheduler shows result 0 when a job fails | open |
| WL-047 | Convert the portal UI to MUI | in progress (A+B coded; UI check, phase C left) |
| WL-046 | Financial results for the last 8 quarters per instrument | open; after WL-028, WL-044 |
| WL-045 | Calendar: earnings dates for US stocks and Binance-related results | earnings part done; BNB burn and unlocks need a source |
| WL-044 | Instrument catalogue in the database, with autocomplete search | done |
| WL-043 | Remove "not financial advice" lines from AI replies and the UI | done |
| WL-042 | Hype radar: social and trending coins, daily at 16:30 PKT | open; after WL-028, WL-029 |
| WL-041 | Stocks and ETFs from Binance in search, chart and analysis | open; after WL-040 |
| WL-040 | Research: which stocks and ETFs Binance lists | done |
| WL-039 | Economic and crypto calendar, refreshed daily at 16:00 PKT | done (backend); page with WL-047 |
| WL-038 | Auto paper trades from the daily picks at 16:00 PKT | open; after WL-029, WL-037 |
| WL-037 | Top 10 picks per trading style, daily | open; after WL-028, WL-036 |
| WL-036 | Correlation and beta to BTC and ETH per coin | done (API and prompt); desk card with WL-047 |
| WL-035 | BTC and ETH pulse on the dashboard (1M, 1W, 1D, 1H, 15m) | backend done; widget with WL-047 |
| WL-034 | Analysis names the best strategies for this trade, with win rates | open; after WL-031, WL-033 |
| WL-033 | Backtester: "Bhalu trades", 50 per strategy per style | open; after WL-028, WL-031 |
| WL-032 | Notes per strategy | open; after WL-028, WL-031 |
| WL-031 | Strategy library: well-known strategies with text and diagrams | open |
| WL-030 | Daily database backup at 20:00 PKT | done |
| WL-029 | Scheduled jobs: .bat runner and Windows Task Scheduler | done |
| WL-028 | Database for journal, signals, trades and notes | done |
| WL-027 | Prompt block hard cut can run 14 characters over the 8k budget | done |
| WL-026 | Confluence guard turns a model confidence of 0.0 into 0.4 when the trade is blocked | done |
| WL-025 | Major bumps to decide: TypeScript 7, Vite 8, @vitejs/plugin-react 6 | assessed; awaiting decision |
| WL-024 | npm patch bump: vite 6.4.4 to 6.4.5 | done |
| WL-023 | Python minor and patch bumps (fastapi, pydantic-settings, websockets, httpx2) | done |
| WL-022 | Security: certifi CRITICAL GHSA-6q48-6c7w-9gw2 | done |
| WL-021 | Decide: may the confluence guard override an AI "Neutral"? | open; needs Sheryar |
| WL-020 | Writing-style sweep: no em dashes, en dashes or exclamation marks in docs | done |
| WL-019 | Lint tooling: ruff for Python, ESLint for the React UI | done |
| WL-018 | Automated tests (pytest) for guards, prompt block, ranking, env writer | done |
| WL-017 | Test the Claude API, Cursor and OpenAI providers with real keys | blocked; needs keys |
| WL-016 | One `/api/analyze` returned offline while `claude_code` was selected | open; not reproduced |
| WL-015 | Adopt the unefy way of working (ruleset, work log, decisions, incidents, agent) | done |
| WL-014 | Handoff document for the next session | done |
| WL-013 | `DESK OVERRIDE` line when the guards change the model's bias | done |
| WL-012 | Prompt snapshot was truncated and dropped confluence and setup | done |
| WL-011 | Restore the Cursor provider for the startup menu | done |
| WL-010 | Claude subscription provider and startup provider menu | done |
| WL-009 | React UI: full port of the redesign, one shared stylesheet | done |
| WL-008 | Symbol search ranking | done |
| WL-007 | Reward:risk: local levels and a 1:1 guard | done |
| WL-006 | Offline analyses are no longer archived as signals | done |
| WL-005 | Remove the Cursor provider | superseded by WL-011 |
| WL-004 | Install uv and the dependencies | done |
| WL-003 | Built-in UI redesign in the Unefy design language | done |
| WL-002 | Documentation folder | done |
| WL-001 | Claude API provider next to Cursor and OpenAI | done |

## Items

### WL-048: Task Scheduler shows result 0 when a job fails

- **Context:** found in WL-029. Tasks start the job through `conhost.exe --headless` so no window flashes; conhost always exits 0, so Task Scheduler's LastTaskResult reads 0 even when a job fails. The real exit code is in `job_runs`, `backend/data/logs/jobs.log` and `GET /api/jobs`. Claude kept the hidden window (2026-10-21): a visible PowerShell flash at every run is worse than a misleading Task Scheduler column nobody reads.
- **Acceptance:** the portal (WL-047) shows a failed or overdue job clearly (red state with glyph, last message); `docs/scheduled-jobs.md` says to read `/api/jobs`, not Task Scheduler.
- **Status:** open.

### WL-047: Convert the portal UI to MUI

- **Context:** Sheryar chose "everything MUI" (2026-10-21) when asked about the WL-044 autocomplete. The React UI (`frontend/`, React 19, strict TS) is custom on the shared `backend/app/static/app.css`; MUI cannot run in the no-build built-in UI (`backend/app/static/`). This supersedes decision 0002 (one stylesheet, two UIs) and changes ruleset 9.1 and 9.2, which needs Sheryar's ok on the exact diff (ruleset 0.1).
- **Acceptance:** MUI (current major with React 19 support) and its theme replace `app.css` in the React UI: light, dark and system modes; the palette carries the existing token values (`--action`, direction green and red, neutrals) so the look stays recognisable; layout (rail, top bar, Ctrl K), all four pages, dialogs (MUI Dialog instead of `askDialog`), the MUI Autocomplete for pair search (fed by WL-044); conventions kept: green and red only for direction with a glyph, missing data as an em dash with a tooltip reason, model output escaped; what happens to the built-in UI decided and done; new decision note; UI check desktop, phone, light and dark; gate green.
- **Progress at handover (2026-10-22):** phases A and B are coded and the gate is green: eslint 0, tsc 0, build 0, npm audit 0. That covers MUI 9.4.0 with emotion 11.14, the theme from the old tokens, the Drawer and AppBar shell, the Autocomplete search, all four pages, the Calendar page, the pulse strip, the correlation card, job status, `Na`, and the confirm helper. **Left:**
  1. The Playwright UI check: desktop and phone, light and dark, five pages, the "nvd" search, and a mocked analysis card.
  2. A visual review against the old look.
  3. Optional code-splitting: the bundle is 659 kB, which trips Vite's 500 kB warning.
  4. Phase C.
- **Open point for Sheryar:** failing jobs use red (as WL-048 asks), but ruleset 9.3 keeps red for Sell and loss. Either keep red for job failure, which needs a ruleset note, or switch it to warning.
- **Status:** in progress; phases A and B coded, UI check and phase C left.

### WL-046: Financial results for the last 8 quarters per instrument

- **Context:** Sheryar wants the last 8 quarters of financial results for each instrument. For **stocks and ETFs**: US filings from SEC EDGAR (free, official, no key; the XBRL "company facts" API gives quarterly revenue, net income, EPS, cash). ETFs file no earnings; for them show quarterly return and assets where available. For **crypto pairs** there are no company results; the closest equivalents are quarterly market results from Binance klines (return, high, low, volume per quarter) and, for tokens of a protocol, quarterly fees and revenue from DefiLlama (free). Data is cached in the database and refreshed weekly, not per page view.
- **Acceptance:** a `financials` table keyed by instrument and quarter; a Financials tab on the desk (both UIs) with 8 quarters, quarter-on-quarter change, and `na("reason")` where a figure does not exist; sources recorded per row; a failed source records `available: false`; tests on fixed EDGAR and kline samples; gate green.
- **Status:** open; after WL-028, WL-044.

### WL-045: Calendar: earnings dates for US stocks and Binance-related results

- **Context:** Sheryar wants upcoming financial results in the calendar (WL-039): US company earnings, and results related to Binance. Binance is a private company and publishes no earnings; the closest regular reports are the quarterly BNB auto-burn, Binance's proof-of-reserves updates, and earnings of listed crypto companies (for example Coinbase, MicroStrategy, miners) and of the stocks Binance lists (WL-040). Earnings dates need a source: free options with a key exist (for example Finnhub or Alpha Vantage earnings calendars); to be chosen in this item.
- **Acceptance:** source chosen and recorded (key by name in `.env`); the 16:00 job (WL-039) also stores earnings dates for the next 30 days with time (before or after market, in PKT) and the EPS estimate where given; BNB burn and proof-of-reserves dates added as Binance events; calendar filters by type (macro, earnings, crypto, Binance); instruments in the catalogue link to their events; gate green.
- **Status:** earnings part done 2026-10-21 (with WL-039). Open: BNB burn, proof-of-reserves and token unlocks need a source (CoinMarketCal has a free key); Sheryar to decide.
- **Outcome so far:** Nasdaq earnings for every Binance-listed stock or ETF (perps and bStocks) in the window, with session, PKT time, EPS forecast and links to the Binance symbols.

### WL-044: Instrument catalogue in the database, with autocomplete search

- **Context:** Sheryar wants every Binance crypto pair and stock instrument stored locally (name and symbol only, no detail) so search finds them instantly with an autocomplete, "like MUI". Today `symbols.py` loads Binance `exchangeInfo` plus the TradingView coin list into memory for 30 minutes on first search. Size: a few thousand rows (spot, USD-M perpetuals, and the stock instruments WL-040 finds). The project has no MUI: the React UI is custom on the shared `app.css` and the built-in UI has no build step (decision 0002, ruleset 9.1, 9.2), so the widget choice is Sheryar's (see status).
- **Acceptance:** an `instruments` table (symbol, name, base, quote, market, type crypto, stock or ETF, status, updated); a refresh job (WL-029) that adds new listings and marks delisted ones; search reads the table with a prefix index (SQLite FTS5) and keeps the current ranking (`<q>USDT` first, selected exchange first; tests stay green); an autocomplete box in both UIs: suggestions while typing, keyboard navigation, name and symbol highlighted, type badge; API documented (ruleset 8); UI check; gate green.
- **Status:** done 2026-10-21 (table, refresh and search API; the MUI Autocomplete lands with WL-047).
- **Outcome:** table `instruments` with an FTS5 index (migration 003). Job `instruments` runs daily at 15:30, and once at startup when the table is empty. 2,183 instruments, 154 of them with ticker-only names. Search reads the table for Binance and the coin list for other venues, with name matches, and keeps the ranking rules. Results add `type`, `name` and `market`. Found tokenized stocks (bStocks) on spot, which corrects WL-040. 130 tests passed at the time. Files: `backend/app/instruments.py` (new), `app/data/instrument_names.json` (new), `migrations/003_instruments.sql` (new), `symbols.py`, `jobs/__init__.py`, `main.py`, tests, `scripts/jobs/instruments.bat` (new), `register.ps1`. Docs: [Symbol search](features/symbol-search.md#instrument-catalogue), [Binance instruments](binance-instruments.md). No incidents.

### WL-043: Remove "not financial advice" lines from AI replies and the UI

- **Context:** Sheryar does not want to be told that the analysis is not financial advice. The text sits in the prompt rules (`ai.py`: "Not financial advice."), the `disclaimer` fields of `AnalyzeResponse` and `ChatResponse` (`schemas.py`), the chat footer in `static/index.html` and `ChatPanel.tsx`, and the docs (`README.md`, `docs/README.md`).
- **Acceptance:** the prompt no longer asks for the line and tells the model not to add disclaimers; the UI footers are removed in both UIs; the `disclaimer` field is removed from both responses with `api.ts` and `api-reference.md` updated (ruleset 8); docs lines removed; tests updated; gate green.
- **Status:** done 2026-10-22.
- **Outcome:** the prompt now tells the model not to add disclaimers (no "not financial advice", no "I am not a financial adviser", no risk-warning lines); `disclaimer` removed from `AnalyzeResponse`, `ChatResponse` and `api.ts`; the chat footer removed from both UIs and the unused `.disclaimer` CSS rule deleted; disclaimer lines removed from `README.md`, `docs/README.md`, `docs/mac-setup.md` and `features/analysis-and-chat.md`. Files: `backend/app/ai.py`, `schemas.py`, `static/index.html`, `static/app.css`, `frontend/src/components/ChatPanel.tsx`, `frontend/src/api.ts`. No incidents.

### WL-042: Hype radar: social and trending coins, daily at 16:30 PKT

- **Context:** Sheryar wants a section that spots coin hype on social media and other platforms early, so low caps can be bought before a rally, refreshed daily at 4:30 PM Pakistan time and visible in the sidebar. Free sources to check: CoinGecko trending, Binance volume and open-interest jumps, Reddit (free API with limits), DEX trending lists; X (Twitter) data needs a paid API, so it is out unless Sheryar wants to pay. Hype is a lead, not a signal: each entry also shows its confluence score and liquidity.
- **Acceptance:** job at 16:30 local stores a ranked list with the source of each mention, change versus yesterday, volume, market cap group and confluence; a Hype radar page with a rail entry (both UIs); sources that fail record `available: false`; no billable AI unless Sheryar enables it; gate green.
- **Status:** open; after WL-028, WL-029.

### WL-041: Stocks and ETFs from Binance in search, chart and analysis

- **Context:** follows WL-040. Today the symbol universe is Binance spot and USD-M crypto only. The analysis pipeline (whale flow, liquidation map) assumes crypto futures data; for stock instruments those sections may not exist and must show as missing, not zero.
- **Acceptance:** the instruments found in WL-040 appear in search with a type badge (crypto, stock, ETF); the chart opens them; analysis runs with unavailable sections marked `available: false` and `na()` in the UI; scanners in WL-037 can include or exclude them; tests for ranking; gate green.
- **Status:** open; after WL-040.

### WL-040: Research: which stocks and ETFs Binance lists

- **Context:** Sheryar trades on Binance and wants stocks and ETFs as well as crypto. What Binance offers for traditional assets (for example stock or index perpetuals on Futures, tokenized stocks, commodity pairs) has to be confirmed from Binance's own `exchangeInfo` and announcements before building, and region limits may apply to his account.
- **Acceptance:** a short findings note in `docs/`: which instruments exist, their symbols and market (spot, USD-M futures), whether klines and depth work through the same endpoints, and gaps; WL-041 is then scoped from it.
- **Status:** done 2026-10-21.
- **Outcome:** Binance USD-M futures `exchangeInfo` (checked 2026-10-21) lists 796 trading contracts, of which 225 carry the `TradFi` subtype with `contractType: TRADIFI_PERPETUAL`: `EQUITY` 187 (US stocks and ETFs such as TSLAUSDT, NVDAUSDT, AAPLUSDT, MSTRUSDT, COINUSDT, SPYUSDT, QQQUSDT, EWJUSDT), `HK_EQUITY` 15, `KR_EQUITY` 8, `CN_EQUITY` 2, `COMMODITY` 8 (XAU, XAG, XPT, XPD, copper, oil CL and BZ, natural gas), `FX` 1, `PREMARKET` 4 (pre-IPO). Spot has 1,387 trading pairs and no stocks. (Corrected by WL-044: spot lists tokenized stocks, the "bStocks" such as NVDABUSDT.) `exchangeInfo` gives no company names: US names come from the SEC `company_tickers.json` (free), the rest from a small mapping. Klines and depth use the normal futures endpoints. Findings page to write in the docs pass. No incidents.

### WL-039: Economic and crypto calendar, refreshed daily at 16:00 PKT

- **Context:** Sheryar wants a calendar of upcoming news for crypto and US markets (FOMC, CPI, jobs, earnings, token unlocks, listings), refreshed by a scheduled job at 4 PM Pakistan time. A free source must be chosen: candidates are a public macro calendar feed for US events, and CoinMarketCal or token-unlock data for crypto (some need a free key). Times shown in PKT.
- **Acceptance:** sources chosen and recorded (a key goes in `.env` by name, never printed); job at 16:00 local stores the next 14 days; a Calendar page (both UIs) with impact level and the affected assets; the snapshot flags a high-impact event within 24 hours so analyses can mention it; a failed source records `available: false`, never breaks the page; gate green.
- **First cut (Sheryar, 2026-10-21):** today plus 7 days, so the quality of the sources can be judged before widening to 14.
- **Status:** done (backend) 2026-10-21; the page lands with WL-047.
- **Outcome:** `calendar_feed.refresh(days=7)` runs as job `calendar` daily at 16:00, and once at startup when empty. Tables come from migration 004. `GET /api/calendar` is live, and `market.upcoming_events` reaches the prompt. Working sources (free, no key): ForexFactory weekly feed (current week only), Nasdaq earnings, Binance announcements. Not covered: BNB burn and token unlocks (no keyless source). The first run stored 39 events. 145 tests passed at the time. Files: `backend/app/calendar_feed.py` (new), `migrations/004_calendar.sql` (new), `jobs/__init__.py`, `main.py`, `market.py`, `schemas.py`, tests, `scripts/jobs/calendar.bat` (new), `register.ps1`. Docs: [Calendar](features/calendar.md). No incidents.

### WL-038: Auto paper trades from the daily picks at 16:00 PKT

- **Context:** Sheryar wants the Top 10 picks opened automatically at 4 PM Pakistan time and to see how they close, checked every few hours by a scheduled job instead of constantly. These are **paper trades** (simulated, no orders sent to Binance): the app has no Binance trading keys and real orders would be a separate decision. The signal tracker already marks wins, losses and expiry; this extends it.
- **Acceptance:** task at 16:00 local builds the picks and opens a paper trade for each (entry at the live price, stop and target from the pick); a task every 4 hours (proposal) checks the candles since the last check and closes trades that hit stop or target, or expire at the style's horizon; results per style and per strategy on a Paper trades page (both UIs): open, won, lost, expired, win rate, total R; gate green.
- **Status:** open; after WL-029, WL-037.

### WL-037: Top 10 picks per trading style, daily

- **Context:** Sheryar wants a daily Top 10 per style: scalping (highest risk, tight stop), day trading (medium risk), swing (days to weeks to a month). Picks should mix strong coins and low caps, longs and shorts as the trend prefers, and show each pick's move with BTC and ETH (WL-036). The watchlist scorer already ranks a fixed list; this item scans the Binance universe (volume and liquidity floor) and uses the confluence score, setup and strategy fit.
- **Acceptance:** a Picks page (both UIs) with three tabs of 10: pair, side, entry, stop, target, R:R, confluence, setup, best strategy, BTC and ETH correlation, coin group (major, large, meme, low cap); at most a stated share of low caps per list; deterministic ranking, AI optional (ruleset 6.3: a daily AI call spends plan usage, so ask Sheryar before enabling it); stored per day; gate green.
- **Status:** open; after WL-028, WL-036.

### WL-036: Correlation and beta to BTC and ETH per coin

- **Context:** Sheryar wants to know how much the traded coin moves with BTC and ETH, and to see it in the Top 10 picks (WL-037).
- **Acceptance:** for a coin and timeframe: correlation of returns and beta against BTC and ETH over a stated window (proposal: 30 days of 1h returns, plus 90 days of 1d); shown on the desk and in the snapshot (and so in the prompt); a function reused by WL-037; tests on fixed series; gate green.
- **Status:** done 2026-10-22 for the API and the prompt; the desk card lands with WL-047, the picks reuse in WL-037.
- **Outcome:** `backend/app/correlation.py` (`compute_correlation`), `GET /api/correlation/{symbol}`, `market.correlation` in the snapshot and a short form at the end of the prompt block. Live check: SOLUSDT 30d 1h vs BTC corr 0.847, beta 1.456. Files: `correlation.py` (new), `market.py`, `schemas.py`, `main.py`, `tests/test_correlation.py` (new, 12 tests). Docs: [API reference](api-reference.md#get-apicorrelationsymbol). No incidents.

### WL-035: BTC and ETH pulse on the dashboard (1M, 1W, 1D, 1H, 15m)

- **Context:** Sheryar wants live BTC and ETH values and indicators on the dashboard with a pulse per timeframe: monthly, weekly, daily, hourly and 15 minutes.
- **Acceptance:** a pulse strip for BTC and ETH: live price and 24h change, and per timeframe a trend direction, RSI, EMA position and a bias pill with a glyph (ruleset 9.3); refreshes on an interval without blocking the desk; Binance data only (no billable AI); both UIs; UI check; gate green.
- **Status:** backend done 2026-10-22; the widget lands with WL-047.
- **Outcome so far:** `GET /api/pulse` (`backend/app/pulse.py`), BTC and ETH over 1M, 1w, 1d, 1h, 15m with trend, RSI and bias, cached 20 s; `tests/test_pulse.py` (12 tests). Docs: [API reference](api-reference.md#get-apipulse).

### WL-034: Analysis names the best strategies for this trade, with win rates

- **Context:** Sheryar wants each trade suggestion to say which strategies fit this trade best and their win rate. The setup classifier already labels the tape (trend, breakout, range, chop); WL-033 provides win rates per strategy, style and coin group.
- **Acceptance:** `/api/analyze` returns the top 3 matching strategies with backtested win rate, sample size and why each fits; the prompt includes them so the AI reply names them; the desk card shows them in both UIs; a strategy with fewer than 20 backtest trades shows its win rate as `na("too few trades")`; API contract updated (ruleset 8); gate green.
- **Status:** open; after WL-031, WL-033.

### WL-033: Backtester: "Bhalu trades", 50 per strategy per style

- **Context:** Sheryar wants every strategy back-tested ("Bhalu trades", Bhalu being his name for the assistant): about 50 trades per strategy, split over scalping, day trading and swing, across coin groups (good coins such as BTC and ETH, normal large caps, meme coins, low-cap "shit coins"), with win rate in % and why losers failed. Candles come from Binance klines (free). Failure tags that can be computed from price data: divergence against the trade, stop hit at a liquidity sweep, profit taking at a level (rejection at resistance or support), volatility spike, against the higher-timeframe trend. "News" as a cause needs a historical news source; without one the tag is "large move with no technical cause (possible news)".
- **Acceptance:** a backtest engine that replays a strategy's rules bar by bar with fees and slippage; results per strategy x style x coin group: trades, win rate, average R, profit factor, max drawdown; every trade stored with entry, exit, R and a failure tag; a Backtests page (both UIs) with the table and a trade list per cell; runs offline from cached klines, no billable AI; tests for the engine on a fixed candle set; gate green.
- **Status:** open; after WL-028, WL-031.

### WL-032: Notes per strategy

- **Context:** Sheryar wants to keep his own notes on each strategy.
- **Acceptance:** add, edit and delete notes on a strategy page, with dates; stored in the database; text escaped (`esc()` / React); `askDialog()` for deletes; API documented (ruleset 8); both UIs; gate green.
- **Status:** open; after WL-028, WL-031.

### WL-031: Strategy library: well-known strategies with text and diagrams

- **Context:** Sheryar wants the world's common trading strategies in the app, each with an explanation, an example and pictures. Candidates: trend following (EMA cross), breakout and retest, range mean reversion, RSI divergence, VWAP reclaim, order-block and liquidity sweep (SMC), Bollinger squeeze, funding and open-interest squeeze, support and resistance flip, Fibonacci pullback, moving-average pullback, opening range breakout, momentum scalping, grid. Pictures are drawn by us as SVG diagrams (no copied images, so no licence question), styled with the `app.css` tokens and readable in light and dark.
- **Acceptance:** a Strategies page in both UIs (ruleset 9.1); each strategy has a name, style fit (scalp, day, swing), rules for entry, stop and exit, market conditions where it works and fails, a worked example and an SVG diagram; data in the backend (one source for both UIs); UI check desktop, phone, light and dark; gate green.
- **Status:** open.

### WL-030: Daily database backup at 20:00 PKT

- **Context:** Sheryar asked for a daily backup with a `.bat` and a cron-like schedule, into a new folder, named by date, at about 8 PM Pakistan time.
- **Acceptance:** task at 20:00 local (PKT) writes `backups/YYYY-MM-DD.<ext>` (SQLite online backup API, or `mysqldump` if WL-028 picks MySQL); a second run on the same day overwrites that day's file; retention rule decided (proposal: keep 30 daily); `backups/` stays out of any future git; a restore is tested once and the steps are documented; gate green.
- **Status:** done 2026-10-21.
- **Outcome:** job `backup` runs daily at 20:00 PKT. It uses the SQLite online backup API and an integrity check, then replaces `backups/YYYY-MM-DD.db`; the newest 30 copies are kept (Claude's proposal; Sheryar can change it). The first real run wrote `backups/2026-10-21.db` with the signal. A restore was tested once on a scratchpad copy and read the signal back. `BACKUP_DIR` overrides the folder. 115 tests passed at the time. Files: `backend/app/jobs/backup.py` (new), `scripts/jobs/backup.bat` (new). Docs: [Scheduled jobs](scheduled-jobs.md#backup). No incidents.

### WL-029: Scheduled jobs: .bat runner and Windows Task Scheduler

- **Context:** WL-030, WL-038, WL-039 and WL-042 run on a timetable. Windows has no cron; the Task Scheduler (`schtasks`) with a `.bat` per job is the equivalent. The machine time zone is Pakistan Standard Time (checked 2026-10-21), so times are set in local time. Jobs must run while the browser is closed, and a missed run (PC asleep) should run at next wake.
- **Acceptance:** `scripts/jobs/*.bat` (new folder, approved by Sheryar's request) call a Python entry point per job in `backend/.venv`; one `scripts/jobs/register.ps1` creates or updates every task (and a `-Remove` switch); each run appends to a job log with start, end and exit code; a job page or rail badge shows the last run per job; "run if missed" set; documented in a new `docs/scheduled-jobs.md`; gate green.
- **Status:** done 2026-10-21.
- **Outcome:** `python -m app.jobs <job>` with a registry, the `job_runs` table (migration 002), `backend/data/logs/jobs.log` and `GET /api/jobs`. `scripts/jobs/<job>.bat` plus `scripts/jobs/register.ps1` create user-level tasks under `\CryptoChartAI\`, with no window, only while logged on, and catch-up after sleep. Found WL-048 (Task Scheduler always shows result 0). Files: `backend/app/jobs/` (new), `migrations/002_job_runs.sql` (new), `main.py`, `schemas.py`, `config.py`, `.env.example`, tests, `scripts/jobs/` (new), `.gitignore`. Docs: [Scheduled jobs](scheduled-jobs.md). No incidents.

### WL-028: Database for journal, signals, trades and notes

- **Context:** Sheryar asked for a small database ("maybe MySQL") for journals, trades and the rest. Today `journal.py` and `signals.py` write `backend/data/journal.json` and `signals.json`. Most of the items below (WL-030, WL-032, WL-033, WL-037, WL-038, WL-039, WL-042) need tables. MySQL means installing and running a server (winget, admin rights, a service, a password in `.env`); SQLite is one file in `backend/data/`, ships with Python, and is trivial to back up. Recommendation: SQLite, behind a small repository layer so MySQL stays a later swap.
- **Acceptance:** engine decided and recorded in `docs/decisions/`; schema with migrations for journal, signals, paper trades, strategy notes, backtest runs, picks, calendar events and hype snapshots (tables added by the items that need them); journal and signals read and write the database, and any existing JSON is imported once; endpoints keep their shapes (ruleset 8); tests for the repository layer; gate green.
- **Engine (reassessed 2026-10-21, after WL-044 to WL-046 were added; Sheryar asked Claude to choose):** SQLite. The largest tables stay small: a few thousand instruments, 8 quarters of financials for a few hundred stocks, a few thousand backtest trades, one calendar month of events. SQLite handles millions of rows; WAL mode lets the server read while a scheduled job writes; FTS5 gives the prefix search the autocomplete needs; a backup is one file (WL-030). MySQL would only pay off with several users, several machines or remote access, none of which applies (the server stays on `127.0.0.1`). The repository layer keeps a later move to MySQL to one module. Decision note to write in this item.
- **Status:** done 2026-10-21.
- **Outcome:** SQLite (decision [0007](decisions/0007-sqlite.md)) with stdlib `sqlite3`, WAL mode and numbered migrations in `backend/app/migrations/`. Journal and signals moved from JSON with the same function signatures and return shapes. The one real signal was imported, and `signals.json` was renamed to `signals.json.imported`. `DB_PATH` overrides the file; tests use a temp file. 107 tests passed at the time; ruff, compileall and the smoke test exit 0. Files: `backend/app/db.py` (new), `migrations/001_init.sql` (new), `journal.py`, `signals.py`, `main.py` (lifespan hook), `config.py`, `backend/.env.example`, `tests/conftest.py`, `tests/test_db.py` (new). Docs: [Database](database.md). No incidents.

### WL-027: Prompt block hard cut can run 14 characters over the 8k budget

- **Context:** found by the WL-018 tests. When `market.context_to_prompt_block` hits its hard cut it returns `max_chars` characters plus the " …[truncated]" marker, so the block can be 14 characters longer than the budget. Harmless in practice (typical size is about 4.5k), but the budget is meant to be a cap. The test in `backend/tests/test_prompt_block.py` pins the current length.
- **Acceptance:** the output, marker included, never exceeds `max_chars`; the pinning test is updated; pytest green.
- **Status:** done 2026-10-22.
- **Outcome:** the hard cut keeps `max_chars - len(marker)` characters plus the marker and is capped at `max_chars`; budgets smaller than the marker are capped too. Files: `backend/app/market.py`, `backend/tests/test_prompt_block.py`. Docs: [Analysis pipeline](analysis-pipeline.md#from-snapshot-to-prompt). No incidents.

### WL-026: Confluence guard turns a model confidence of 0.0 into 0.4 when the trade is blocked

- **Context:** found by the WL-018 tests. In `main._apply_confluence_guardrail`, the blocked-trade branch caps confidence with `min(conf_val or 0.4, 0.4)`; a model confidence of 0.0 is falsy and becomes 0.4. Related to the policy question in WL-021, but a plain bug on its own.
- **Acceptance:** 0.0 stays 0.0, a missing confidence still defaults to 0.4; a test pins both; pytest green.
- **Status:** done 2026-10-22.
- **Outcome:** the blocked-trade branch now uses `0.4 if conf_val is None else min(conf_val, 0.4)`; 0.0 stays 0.0. New test `test_trade_not_allowed_keeps_zero_confidence`. Files: `backend/app/main.py`, `backend/tests/test_guards.py`. Docs: [AI providers](ai-providers.md#what-happens-to-the-reply). No incidents.

### WL-025: Major bumps to decide: TypeScript 7, Vite 8, @vitejs/plugin-react 6

- **Context:** `npm outdated` on 2026-10-21: typescript 5.7.3 (latest 7.0.2), vite 6.4.4 (latest 8.3.5), @vitejs/plugin-react 4.7.0 (latest 6.1.2). Majors are asked first (ruleset 7.3). Vite is now 6.4.5 (WL-024). Python: `tradingview-mcp-server` 0.8.1 (the latest installed) pins `tradingview-screener==3.0.0` (latest 3.2.2) and `mcp<2` (latest 2.3.0), and `pandas` 2 to 3 comes in through those; none of the three can move until that parent releases a version that allows them. Check its releases at each version check.
- **Acceptance:** Sheryar decides per package; each accepted major becomes its own item with the gate green.
- **Assessment (2026-10-21):** each candidate was installed in a throwaway copy of `frontend/` in the session scratchpad (the real tree untouched) and put through the React gate.

  | Candidate | `tsc -b` | build | `npm audit` | Finding |
  |---|---|---|---|---|
  | Baseline (TS 5.7.3, Vite 6.4.5) | 0 | 0, 1.38 s | 0 | JS 271.9 kB, CSS 23.5 kB |
  | Vite 8.3.5 + plugin-react 6.1.2 | 0 | 0, **0.27 s** | 0 | JS 268.6 kB, CSS 23.2 kB; dev server in a browser: rail, KPI strip, Ctrl K search through the `/api` proxy, navigation and dark theme work, no page errors |
  | TypeScript 6.0.3 | 0 | 0 | 0 | build output byte-identical to baseline |
  | TypeScript 7.0.2 | 0 | 0 | 0 | build output byte-identical to baseline |

  - **plugin-react 6 requires Vite 8** (peer `vite ^8.0.0`); the two move together. Vite 8 replaces esbuild and Rollup with Rolldown and Oxc, uses Lightning CSS to minify, and raises the default browser targets to Chrome 111, Firefox 114, Safari 16.4. Our `vite.config.ts` uses none of the renamed options (`build.rollupOptions`, `esbuild`, `optimizeDeps.esbuildOptions`), and our CSS already needs `color-mix()` (Chrome 111, Safari 16.2), so the new targets change nothing for us; `color-mix`, `prefers-color-scheme` and `data-theme` rules all survive the new minifier. plugin-react 6 drops its `babel` option, which we do not use. Node 24 meets both (`^20.19.0 || >=22.12.0`).
  - **TypeScript 6** deprecates `target: es5`, `downlevelIteration`, `moduleResolution: node10`, `baseUrl` as a lookup root and others, and defaults `strict` to true and `types` to `[]`. Our `tsconfig.json` uses none of the deprecated options and already sets `strict`.
  - **TypeScript 7** (the Go-native compiler) turns the 6.0 deprecations into errors and ships without the programmatic API that tools embed. **Blocker found:** `typescript-eslint` 8.72.0 (latest) declares peer `typescript >=4.8.4 <6.1.0`, so TS 7 would block the ESLint step planned in WL-019. unefy-platform caps TypeScript at 6.x for the same reason.
  - **Recommendation:** take Vite 8 together with plugin-react 6, and TypeScript 6.0.3; hold TypeScript 7 until typescript-eslint supports it.
  - Hit a non-obvious failure while testing: [incident WL-025](incidents/WL-025.md) (stopped test servers kept running).
- **Status:** assessed; awaiting Sheryar's decision.

### WL-024: npm patch bump: vite 6.4.4 to 6.4.5

- **Context:** `npm outdated` on 2026-10-21. Patch inside the major, so it goes ahead without asking (ruleset 7.3).
- **Acceptance:** `npm install vite@6.4.5`; React gate green; `npm audit` clean.
- **Outcome (2026-10-21):** `npm update vite` (exit 0) moved vite 6.4.4 to 6.4.5 inside the existing `^6.0.0` range; `package.json` unchanged, only vite's entry changed in `package-lock.json`. Gate: `npx tsc -b` exit 0, `npm run build` exit 0 (`dist` removed afterwards), `npm audit` exit 0 with 0 vulnerabilities. The dev server starts and serves `/` and `src/main.tsx` (200), and the shared stylesheet `backend/app/static/app.css` loads through `fs.allow` (200). Trivy exit 0. Changed file: `frontend/package-lock.json` (backups of both npm files in the session scratchpad). No incidents.
- **Status:** done.

### WL-023: Python minor and patch bumps

- **Context:** `uv pip list --outdated` on 2026-10-21: fastapi 0.147.0 to 0.157.0, pydantic-settings 2.16.0 to 2.16.1, websockets 17.2 to 17.3, tradingview-screener 3.0.0 to 3.2.2 (transitive), httpx2 / httpcore2 2.14 to 2.16 (transitive of `anthropic`). certifi is handled by WL-022.
- **Acceptance:** `uv lock --upgrade-package` per direct package (transitives through their parent), `uv sync`, backend gate and smoke test green.
- **Outcome (2026-10-21):** `uv lock --upgrade-package` for exactly these six packages (the majors `mcp` and `pandas` excluded), exit 0; `uv sync` exit 0. Installed: fastapi 0.157.0, pydantic-settings 2.16.1, websockets 17.3, httpx2 and httpcore2 2.16.0. **tradingview-screener stays 3.0.0:** `tradingview-mcp-server` 0.8.1 pins it (`==3.0.0`), so it moves only with that parent (see WL-025). uv now resolves httpx2 / httpcore2 per Python version (2.16 on 3.11 and later, which we run; 2.14 kept for 3.10, still allowed by `requires-python`), so the lock lists 79 packages instead of 77. Gate: `compileall` exit 0; `choose_provider --keep` exit 0 (pydantic-settings loads `.env`); smoke test with `AI_PROVIDER=none`: health, `/`, static assets, Swagger and `openapi.json` 200; chat with an empty message 400 and analyze without a symbol 422 (validation unchanged); search 200; analyze SOLUSDT 1h 200 offline, no signal archived; journal add, close (200), bad status (422), delete (200), delete again (404); signals 200. Test journal data removed. Trivy exit 0. Changed file: `backend/uv.lock` (backup in the session scratchpad). No incidents.
- **Status:** done.

### WL-022: Security: certifi CRITICAL GHSA-6q48-6c7w-9gw2

- **Context:** the Trivy scan on 2026-10-21 (ruleset 7.2) reported `certifi` 2026.10.18 in `backend/uv.lock`: CRITICAL, fixed in 2026.10.19 (bundles emSign root CAs with compromised keys). certifi is transitive (httpx, requests); every HTTPS call to Binance, TradingView, Yahoo and the AI APIs trusts its CA bundle.
- **Acceptance:** `uv lock --upgrade-package certifi` gives 2026.10.19 or later; `uv sync`; backend gate and smoke test green; the Trivy scan exits 0.
- **Outcome (2026-10-21):** `uv lock --upgrade-package certifi` moved certifi 2026.10.18 to 2026.10.19; no other package changed in `backend/uv.lock` (diff checked). `uv sync` exit 0. Gate: `compileall` exit 0; an HTTPS call to Binance returned 200 with the new bundle; smoke test with `AI_PROVIDER=none`: `/api/health` 200, `/api/analyze` ETHUSDT 1h 200 with TradingView, flow, order book and liquidity all loaded over HTTPS, `provider: "offline"`, no signal archived. Trivy scan exit 0, 0 findings in `uv.lock` and `package-lock.json`. Changed file: `backend/uv.lock` (backup of the old one in the session scratchpad). No incidents.
- **Status:** done.

### WL-021: Decide: may the confluence guard override an AI "Neutral"?

- **Context:** `main.py:_apply_confluence_guardrail` upgrades a model's Neutral to the confluence bias when |score| is 3.5 or more. This is the original author's design; WL-013 made it visible with `DESK OVERRIDE`. An AI "no trade" may carry information the score lacks. The WL-018 tests also show that when the confluence bias is Neutral and |score| is 2.5 or more, the model's Buy or Sell passes through unchanged; include that case in the decision.
- **Acceptance:** Sheryar decides: keep, remove the upgrade, or make it a setting. The decision gets a note in `docs/decisions/`.
- **Status:** open; needs Sheryar.

### WL-020: Writing-style sweep of the docs

- **Context:** ruleset section 3 bans em dashes, en dashes and exclamation marks in project text. The docs written before the ruleset (2026-10-21) use em dashes widely.
- **Acceptance:** `grep -rn "—\|–\|!" docs README.md CLAUDE.md` finds only code samples and literal UI strings; meaning unchanged; links still resolve.
- **Status:** done 2026-10-21.
- **Outcome:** about 45 dashes replaced in 10 files: number ranges read "x to y", headings use ": ", empty table cells read "none" (or "derived from the rows above"). Kept on purpose: code samples, the literal UI string in the `ui.md` layout sketch, the literal character in the project-state gotchas, and this item's own grep pattern. No exclamation marks found. 137 relative links and anchors checked, 0 broken. Files: `docs/ai-providers.md`, `analysis-pipeline.md`, `configuration.md`, `getting-started.md`, `mac-setup.md`, `project-state.md`, `README.md`, `troubleshooting.md`, `features/flow-and-liquidity.md`, `features/watchlist.md`. No incidents.

### WL-019: Lint tooling

- **Context:** no linter is configured for Python or TypeScript, so the gate has no lint step (ruleset 6.2).
- **Acceptance:** ruff added to the backend dev dependencies with a minimal config and the code clean; ESLint 9 for `frontend/` with the React hooks rules and the code clean; both steps added to the gate in the ruleset and `wl-worker.md`.
- **Status:** done 2026-10-21.
- **Outcome:** ruff (default rules E4, E7, E9, F; lint only, no formatter) in the backend dev group, and an ESLint 9 flat config for `frontend/` (`npm run lint`). Both clean, with no `noqa` and no warnings. Ruff fixes, behaviour unchanged: a renamed local in `binance_ta._pivots`, an unused variable in `confluence.py`, the repeated `bb_squeeze` key merged in `market.condense_market_context` (same value and position, prompt JSON identical), a dead block in `symbols.search_symbols`. Gate: ruff, pytest, compileall, eslint, tsc, build, npm audit (0 vulnerabilities) and the offline smoke test all exit 0. Files: `backend/pyproject.toml`, `uv.lock`, `backend/app/binance_ta.py`, `confluence.py`, `market.py`, `symbols.py`, `frontend/eslint.config.js` (new), `frontend/package.json`, `package-lock.json`. Docs: [Tests and lint](testing-and-lint.md). Surprise: the edits turned five LF files into CRLF; converted back (gotcha recorded there). Gate rows added to the ruleset (1.1) and `wl-worker.md` after Sheryar's ok.

### WL-018: Automated tests

- **Context:** no tests exist. The logic most worth pinning: `config.resolve_provider`, `main._apply_reward_risk_guard`, `market.context_to_prompt_block` (order and budget), `symbols.search_symbols` ranking, `choose_provider.set_env_values`. Tests must not call live or billable services.
- **Acceptance:** pytest in the backend dev dependencies; tests for the five units pass offline; `pytest` added to the gate.
- **Status:** done 2026-10-21.
- **Outcome:** 95 offline tests in `backend/tests/` for the five units, passing in under a second; pytest in the backend dev group, `[tool.pytest.ini_options]` in `pyproject.toml`. An autouse fixture isolates env vars, `.env` and the network. No app code changed. Findings logged as WL-026 and WL-027, and a policy case added to WL-021. Docs: [Tests and lint](testing-and-lint.md). Gate row added in ruleset 1.1. No incidents.

### WL-017: Test the Claude API, Cursor and OpenAI providers

- **Context:** only `claude_code` and `none` have run for real. The Claude API path was checked up to authentication (a fake key gets the expected 401 message); Cursor and OpenAI are the original author's code and untested.
- **Acceptance:** one real analysis per provider, each returning a parsed plan; any failure becomes its own item.
- **Status:** blocked; needs keys from Sheryar.

### WL-016: One `/api/analyze` returned offline while `claude_code` was selected

- **Context:** see [incident WL-016](incidents/WL-016.md). The first analysis after a server start returned `provider: "offline"` while `/api/health` in the same process said `claude_code`; retries worked.
- **Acceptance:** reproduced and fixed, or closed after a week of normal use with no recurrence (the server now logs the provider per request and warns when a selected provider is not configured).
- **Status:** open; not reproduced.

### WL-015: Adopt the unefy way of working

- **Context:** Sheryar asked that sessions on this repo follow the unefy-platform rules.
- **Acceptance:** an adapted ruleset, this work log, decision notes, incident reports and template, a `wl-worker` agent, hub links, and `CLAUDE.md` and memory pointing at them.
- **Outcome:** [ruleset.md](reference/ruleset.md) 1.0, [decisions](decisions/Decisions.md) 0001 to 0006, [incidents](incidents/README.md), `.claude/agents/wl-worker.md`. The first version and security check logged WL-022 to WL-025. No incidents.
- **Status:** done.

### WL-001 to WL-014

Logged retroactively. What was built, how it was verified and which files changed is in [project-state.md](project-state.md). Incidents: [WL-012](incidents/WL-012.md). WL-007 noted its root cause in project-state (target pinned to the swing high).
