# User interface

There are two frontends with the same pages and behaviour:

- **Built-in UI**: `backend/app/static/` (`index.html`, `app.css`, `app.js`). Plain HTML, CSS and JavaScript with no build step, served by FastAPI at `/`.
- **React UI**: `frontend/` (Vite + React 19 + TypeScript, `npm run dev` on :5173). Components live in `src/components` and the pages in `src/pages`. It imports `backend/app/static/app.css` directly (`vite.config.ts` allows reading `..`), so **both UIs share one stylesheet** and a token change applies to both.

Its visual language is adapted from the **Unefy portal design system** (Portal Design Guide v2.x): Inter type, a single cool-grey neutral ramp, a separate *action* blue for interactive elements, a collapsible rail, a 52px top bar with global search, KPI strips, and widget cards.

## Layout

```
┌──────────┬───────────────────────────────────────────────────────────────┐
│ Chart AI │ Desk  [SOLUSDT ⌄] [BINANCE ⌄] [15m|1h|4h|1D]   [Search… Ctrl K] ☾ │  ← 52px top bar
│──────────│───────────────────────────────────────────────────────────────│
│ Desk     │ SOLUSDT                              [Log to journal] [Full ✦] │  ← page header
│ Watchlist│ BINANCE · 1h — confluence +4.7 / 10 — trend continuation      │
│ TRACK    │ ┌ Bias ┬ Confluence ┬ Setup ┬ Entry ┬ R:R ┬ Price ┐            │  ← KPI strip
│ Journal 1│ ┌ Chart ─────────────────┬ Levels ┐  ┌ Analyst ──────┐        │
│ Signals 2│ │ TradingView widget     │ Target │  │ trade card    │        │
│          │ └────────────────────────┴────────┘  │ reply …       │        │
│ ● Claude │ ┌ Confluence ┐ ┌ Setup & TFs ┐       │ [chips]       │        │
│ opus-5-5 │ ┌ Whales     ┐ ┌ Liquidity   ┐       │ [ask… ➤]      │        │
│     «    │                                      └───────────────┘        │
└──────────┴───────────────────────────────────────────────────────────────┘
```

| Page | Route | Contents |
|---|---|---|
| Desk | `#/desk` | Chart, structure levels, KPI strip, four insight cards, Analyst chat |
| Watchlist | `#/watchlist` | KPI strip + scored table ([feature](features/watchlist.md)) |
| Journal | `#/journal` | KPI strip + trades with Win / Loss / BE / Skip / Delete ([feature](features/journal.md)) |
| Signals | `#/signals` | KPI strip + archived signals with Check / Verify ([feature](features/signals.md)) |

The rail at 224px folds to 64px icons with the toggle at its foot (« / »). Below 900px it turns into a slide-in drawer opened by ☰. The AI provider chip at the bottom shows the active provider and model; the dot is green when a key is configured and amber when it isn't.

## Keyboard

| Keys | Action |
|---|---|
| Ctrl K / ⌘K | Open or close the pair search |
| ↑ ↓ · Enter · Esc | Move, open, close in the search |
| Enter / Shift+Enter | Send / new line in the chat |
| Esc | Close a dialog |

## Design tokens

Tokens are CSS custom properties on `:root` in `app.css`. **Don't write a hex value in a component rule.** Add or reuse a token instead.

| Group | Tokens |
|---|---|
| Neutrals | `--n0` (white) … `--n900` (near-black), one cool-grey ramp |
| Brand vs action | `--brand #12B6F8` is identity only (the logo mark). `--action #0B749E` is for everything clickable: buttons, links, focus rings, selected rows. Brand fails contrast as text on white; action passes. |
| Status | `--ok`, `--warn`, `--crit` and their `-surface` tints |
| Semantic surfaces | `--bg`, `--paper`, `--paper-2`, `--text`, `--text-2`, `--muted`, `--faint`, `--border`, `--divider` |
| Elevation | `--elev1/2/3` (cast from `--n900`, never pure black) |
| Radius | `--r-xs 2` · `--r-sm 6` · `--r-md 10` · `--r-lg 16` · `--r-full` |
| Type | `--font` Inter · `--mono` JetBrains Mono, for prices and IDs |
| Levels | `--lv-res`, `--lv-target`, `--lv-entry`, `--lv-ema20`, `--lv-ema50`, `--lv-support`, `--lv-stop` |

**Themes:** light is the default. Dark applies either from `prefers-color-scheme` or explicitly through `<html data-theme="dark">`; the moon/sun button stores the choice. Dark redefines the semantic tokens, including a lighter `--action` with dark `--on-action` ink so primary buttons keep their contrast. The TradingView widget is re-mounted in the matching theme.

## Conventions

These are carried over from the Unefy guide:

- **Direction ink belongs to direction only.** Green is Buy/win and red is Sell/loss; nothing else uses them. Pills always have a **glyph as well as a colour** (▲ ▼ ● ✓ ✕ ○), so they read in greyscale and for colour-blind users.
- **Missing data is an em dash** with the reason on hover (`na("…")` in `app.js`), never `0` and never blank.
- **One primary button per view.**
- **KPI strips** always have a note under the value (a number with no qualifier isn't useful), and they scroll sideways on a phone instead of wrapping.
- **Wide tables** scroll inside their card (`.table-wrap`) with a minimum width, so the page never scrolls horizontally.
- **Confirmations use the in-app dialog** (`askDialog`), never `window.confirm` or `prompt`.
- **Mobile (<600px):** body text 16px, buttons 48px tall.
- Model output is inserted with escaping (`esc()`), and only the leading `KEY:` labels are bolded.

## Browser storage

`localStorage` keys (all optional, wrapped in try/catch):

| Key | Holds |
|---|---|
| `cca_theme` | `light` / `dark` |
| `cca_rail_folded` | `1` / `0` |
| `cca_tf` | Last timeframe |
| `cca_recent` | Last 6 pairs |
