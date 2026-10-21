/* Crypto Chart AI — built-in UI (no build step). */

const TV_INTERVAL = { "15m": "15", "1h": "60", "4h": "240", "1D": "D" };
const PAGES = { desk: "Desk", watchlist: "Watchlist", journal: "Journal", signals: "Signals" };

const ICONS = {
  activity: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  chart: '<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  book: '<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>',
  bookPlus: '<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/><path d="M12 7v6M9 10h6"/>',
  target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
  chevronsLeft: '<path d="m11 17-5-5 5-5M18 17l-5-5 5-5"/>',
  chevronDown: '<path d="m6 9 6 6 6-6"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
  moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
  sparkles: '<path d="M12 3l1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2Z"/>',
  gauge: '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
  layers: '<path d="m12 2 10 5-10 5L2 7Z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/>',
  waves: '<path d="M2 6c.6.5 1.2 1 2.5 1C7 7 7 5 9.5 5c2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>',
  droplet: '<path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5S5 13 5 15a7 7 0 0 0 7 7z"/>',
  message: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  send: '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  trash: '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>',
  inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  arrowRight: '<path d="M5 12h14M12 5l7 7-7 7"/>',
};

const state = {
  symbol: "SOLUSDT",
  exchange: "BINANCE",
  tvSymbol: "BINANCE:SOLUSDT",
  timeframe: "1h",
  history: [],
  busy: false,
  lastLevels: null,
  lastMarket: null,
  searchTimer: null,
  paletteItems: [],
  paletteIndex: 0,
};

const $ = (id) => document.getElementById(id);

/* ─── Small helpers ──────────────────────────────────────────────────── */

function icon(name, size) {
  const body = ICONS[name] || "";
  return `<svg class="icon${size === "sm" ? " sm" : ""}" viewBox="0 0 24 24" aria-hidden="true">${body}</svg>`;
}

function hydrateIcons(root = document) {
  root.querySelectorAll("[data-icon]").forEach((el) => {
    const svg = icon(el.dataset.icon, el.dataset.size);
    if (el.tagName === "SPAN" && !el.childNodes.length) {
      el.outerHTML = svg;
    } else {
      el.insertAdjacentHTML("afterbegin", svg);
      el.removeAttribute("data-icon");
    }
  });
}

function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

/** No data is an em dash with the reason on hover — never a zero or a blank. */
function na(reason = "Not available") {
  return `<span class="na" title="${esc(reason)}">—</span>`;
}

function isNum(n) {
  return n != null && n !== "" && !Number.isNaN(Number(n));
}

function fmtPx(n, reason) {
  if (!isNum(n)) return na(reason);
  const v = Number(n);
  const digits = Math.abs(v) >= 1000 ? 2 : Math.abs(v) >= 1 ? 4 : 6;
  return v.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function fmtSigned(n, digits = 1) {
  if (!isNum(n)) return na();
  const v = Number(n);
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}`;
}

function fmtPct(n, digits = 1) {
  if (!isNum(n)) return na();
  return `${fmtSigned(n, digits)}%`;
}

function fmtConf(c) {
  if (!isNum(c)) return na();
  const v = Number(c);
  return `${Math.round(v <= 1 ? v * 100 : v)}%`;
}

function fmtWhen(iso) {
  if (!iso) return na();
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return na();
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function rr(entry, stop, target) {
  if (!isNum(entry) || !isNum(stop) || !isNum(target)) return null;
  const risk = Math.abs(entry - stop);
  return risk > 0 ? Math.abs(target - entry) / risk : null;
}

function biasClass(bias) {
  const b = String(bias || "").toLowerCase();
  if (b === "buy" || b === "long") return "buy";
  if (b === "sell" || b === "short") return "sell";
  return "";
}

const GLYPH = { buy: "▲", sell: "▼", "": "●" };

/** Direction pill — glyph plus ink, so it survives greyscale. */
function biasPill(bias) {
  if (!bias) return na();
  const cls = biasClass(bias);
  return `<span class="pill ${cls}"><span class="g">${GLYPH[cls]}</span>${esc(bias)}</span>`;
}

const STATUS_PILL = {
  win: ["win", "✓"],
  loss: ["loss", "✕"],
  open: ["info", "○"],
  expired: ["", "◷"],
  be: ["", "="],
  skipped: ["", "–"],
  invalid: ["warn", "!"],
};

const TREND_BIAS = { Bullish: "Buy", Bearish: "Sell" };

function trendPill(trend) {
  const cls = biasClass(TREND_BIAS[trend]);
  return `<span class="pill ${cls}"><span class="g">${GLYPH[cls]}</span>${esc(trend || "Neutral")}</span>`;
}

function statusPill(status) {
  const [cls, g] = STATUS_PILL[status] || ["", "●"];
  return `<span class="pill ${cls}"><span class="g">${g}</span>${esc(status || "—")}</span>`;
}

function emptyState(text, iconName = "inbox") {
  return `<div class="empty">${icon(iconName)}${esc(text)}</div>`;
}

function toast(text) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = text;
  $("toasts").appendChild(el);
  setTimeout(() => el.remove(), 3800);
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    ...opts,
    headers: opts.body ? { "Content-Type": "application/json" } : undefined,
  });
  const body = await res.text();
  if (!res.ok) throw new Error(apiError(body) || res.statusText);
  return body ? JSON.parse(body) : null;
}

function apiError(body) {
  try {
    const j = JSON.parse(body);
    if (typeof j.detail === "string") return j.detail;
    if (Array.isArray(j.detail)) return j.detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
    return body;
  } catch {
    return body;
  }
}

function store(key, value) {
  try {
    if (value === undefined) return localStorage.getItem(key);
    localStorage.setItem(key, value);
  } catch {
    return null;
  }
  return value;
}

function setBusy(btn, busy, label) {
  if (!btn) return;
  if (busy) {
    btn.dataset.label = btn.innerHTML;
    btn.innerHTML = `<span class="spinner"></span>${esc(label || "Working…")}`;
    btn.disabled = true;
  } else {
    if (btn.dataset.label) btn.innerHTML = btn.dataset.label;
    btn.disabled = false;
  }
}

function kpiStrip(rootId, tiles) {
  $(rootId).innerHTML = tiles
    .map(
      (t) => `
      <div class="kpi" role="listitem">
        <div class="kpi-label">${esc(t.label)}</div>
        <div class="kpi-value ${t.cls || ""}">${t.value}${t.unit ? `<span class="unit">${esc(t.unit)}</span>` : ""}</div>
        <div class="kpi-note" title="${esc(t.noteTitle || "")}">${t.note}</div>
      </div>`,
    )
    .join("");
}

/* ─── Theme & rail ───────────────────────────────────────────────────── */

function effectiveTheme() {
  const t = document.documentElement.dataset.theme;
  if (t === "light" || t === "dark") return t;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function paintThemeButton() {
  const btn = $("themeBtn");
  const dark = effectiveTheme() === "dark";
  btn.innerHTML = icon(dark ? "sun" : "moon");
  btn.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
}

function toggleTheme() {
  const next = effectiveTheme() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  store("cca_theme", next);
  paintThemeButton();
  mountChart();
}

function setFolded(folded) {
  $("shell").classList.toggle("folded", folded);
  $("railToggle").setAttribute("aria-label", folded ? "Expand navigation" : "Collapse navigation");
  store("cca_rail_folded", folded ? "1" : "0");
}

/* ─── Routing ────────────────────────────────────────────────────────── */

function route() {
  const name = (location.hash.replace(/^#\/?/, "") || "desk").split("/")[0];
  const page = PAGES[name] ? name : "desk";
  document.querySelectorAll("[data-page]").forEach((el) => {
    el.hidden = el.dataset.page !== page;
  });
  document.querySelectorAll(".nav-item").forEach((a) => {
    if (a.dataset.route === page) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  $("pageTitle").textContent = PAGES[page];
  $("shell").classList.remove("nav-open");
  if (page === "journal") refreshJournal();
  if (page === "signals") refreshSignals();
}

/* ─── Pair / chart ───────────────────────────────────────────────────── */

function setActiveSymbol(symbol, exchange, tv) {
  const sym = String(symbol || "").trim().toUpperCase();
  if (!sym) return;
  const ex = String(exchange || state.exchange || "BINANCE").toUpperCase();
  const changed = sym !== state.symbol || ex !== state.exchange;
  state.symbol = sym;
  state.exchange = ex;
  state.tvSymbol = String(tv || `${ex}:${sym}`).toUpperCase();
  $("exchange").value = ex;
  $("scopeSymbol").textContent = sym;
  $("deskTitle").textContent = sym;
  $("input").placeholder = `Ask about ${sym}…`;
  rememberRecent(sym, ex, state.tvSymbol);
  if (changed) resetAnalysis(`Switched to ${ex}:${sym}.`);
  mountChart();
}

function setTimeframe(tf) {
  if (!TV_INTERVAL[tf]) return;
  const changed = tf !== state.timeframe;
  state.timeframe = tf;
  store("cca_tf", tf);
  document.querySelectorAll("#timeframe button").forEach((b) => {
    b.setAttribute("aria-pressed", String(b.dataset.tf === tf));
  });
  if (changed) {
    resetAnalysis(`Timeframe set to ${tf}.`);
    mountChart();
  }
}

function mountChart() {
  $("tvLabel").textContent = state.tvSymbol;
  const el = $("tv_chart");
  el.innerHTML = "";
  if (!window.TradingView) {
    el.innerHTML = emptyState("TradingView chart library did not load. Check your connection.", "chart");
    return;
  }
  const dark = effectiveTheme() === "dark";
  new TradingView.widget({
    autosize: true,
    symbol: state.tvSymbol,
    interval: TV_INTERVAL[state.timeframe] || "60",
    timezone: "Etc/UTC",
    theme: dark ? "dark" : "light",
    style: "1",
    locale: "en",
    toolbar_bg: dark ? "#14191D" : "#FFFFFF",
    enable_publishing: false,
    allow_symbol_change: false,
    hide_side_toolbar: false,
    container_id: "tv_chart",
    studies: ["MAExp@tv-basicstudies"],
  });
}

/* ─── Desk rendering ─────────────────────────────────────────────────── */

const RUN_HINT = "Run a full analysis";

function resetAnalysis(note) {
  state.lastLevels = null;
  state.lastMarket = null;
  state.history = [];
  $("journalBtn").disabled = true;
  renderDesk(null, null);
  if (note && $("messages").children.length) addMessage("assistant", note, { quiet: true });
}

function renderDesk(levels, market) {
  renderDeskHeader(levels, market);
  renderDeskKpis(levels, market);
  renderLevels(levels, market);
  renderConfluence(market);
  renderSetup(market);
  renderFlow(market);
  renderLiquidity(market);
}

function currentPrice(market) {
  const coin = (market && market.coin_analysis) || {};
  return (coin.price_data || {}).current_price ?? (market && market.yahoo_price && market.yahoo_price.price);
}

function renderDeskHeader(levels, market) {
  const sub = $("deskSubtitle");
  if (!levels || !market) {
    sub.textContent = `${state.exchange} · ${state.timeframe} — run a full analysis to score this pair.`;
    $("dataSource").textContent = "";
    return;
  }
  const conf = market.confluence || {};
  const setup = market.setup || {};
  const parts = [`${state.exchange} · ${state.timeframe}`];
  if (isNum(conf.score)) parts.push(`confluence ${fmtSigned(conf.score)} / 10`);
  if (setup.type) parts.push(`${setup.type.replace(/_/g, " ")}${setup.trade_allowed === false ? " (no trade)" : ""}`);
  sub.textContent = parts.join(" — ");
  const src = market.data_source === "binance_local" ? "Binance (local TA)" : market.data_source === "tradingview" ? "TradingView TA" : market.data_source || "";
  $("dataSource").textContent = src ? `Data: ${src}` : "";
}

function renderDeskKpis(levels, market) {
  if (!levels || !market) {
    kpiStrip("deskKpis", [
      { label: "Bias", value: na(RUN_HINT), note: RUN_HINT },
      { label: "Confluence", value: na(RUN_HINT), note: "Score −10 to +10" },
      { label: "Setup", value: na(RUN_HINT), note: "Chop filter" },
      { label: "Entry", value: na(RUN_HINT), note: "Stop · Target" },
      { label: "Reward : risk", value: na(RUN_HINT), note: "Confidence" },
      { label: "Price", value: na(RUN_HINT), note: "24h change" },
    ]);
    return;
  }
  const conf = market.confluence || {};
  const setup = market.setup || {};
  const flow = market.flow || {};
  const ratio = rr(levels.entry, levels.stop_loss, levels.take_profit);
  const chg = flow.price_change_24h_pct ?? (market.yahoo_price || {}).change_pct;
  const cls = biasClass(levels.bias);
  kpiStrip("deskKpis", [
    {
      label: "Bias",
      cls,
      value: `${GLYPH[cls]} ${esc(levels.bias || "Neutral")}`,
      note: esc(levels.trend ? `Trend ${levels.trend}` : "Trend —"),
    },
    {
      label: "Confluence",
      cls: biasClass(conf.bias),
      value: isNum(conf.score) ? fmtSigned(conf.score) : na(),
      unit: "/ 10",
      note: `Prefers ${esc(conf.bias || "—")}`,
    },
    {
      label: "Setup",
      cls: "text",
      value: setup.type ? esc(setup.type.replace(/_/g, " ")) : na(),
      note: setup.trade_allowed === false ? "Blocked by chop filter" : "Trade allowed",
    },
    {
      label: "Entry",
      value: fmtPx(levels.entry),
      note: `SL ${fmtPx(levels.stop_loss)} · TP ${fmtPx(levels.take_profit)}`,
    },
    {
      label: "Reward : risk",
      value: ratio == null ? na("Needs entry, stop and target") : ratio.toFixed(1),
      unit: ratio == null ? "" : ": 1",
      note: `Confidence ${fmtConf(levels.confidence)}`,
    },
    {
      label: "Price",
      value: fmtPx(currentPrice(market)),
      note: `24h ${fmtPct(chg, 2)}`,
    },
  ]);
}

const LEVEL_ROWS = [
  ["Resistance 2", "resistance_2", "--lv-res"],
  ["Resistance", "resistance", "--lv-res"],
  ["Target", "take_profit", "--lv-target"],
  ["EMA 20", "ema20", "--lv-ema20"],
  ["Entry", "entry", "--lv-entry"],
  ["EMA 50", "ema50", "--lv-ema50"],
  ["Support", "support", "--lv-support"],
  ["Support 2", "support_2", "--lv-support"],
  ["Stop", "stop_loss", "--lv-stop"],
];

function renderLevels(levels, market) {
  const root = $("levelsBoard");
  if (!levels) {
    root.innerHTML = `<div class="overline">Structure levels</div>${emptyState("Levels appear here after a full analysis.", "layers")}`;
    return;
  }
  const rows = LEVEL_ROWS.map(([label, key, color]) => ({ label, val: levels[key], color })).filter((r) => isNum(r.val));
  const px = currentPrice(market);
  if (isNum(px)) rows.push({ label: "Last price", val: px, color: "--text", price: true });
  rows.sort((a, b) => b.val - a.val);
  root.innerHTML =
    `<div class="overline">Structure levels</div>` +
    (rows.length
      ? rows
          .map(
            (r) => `
          <div class="level-row${r.price ? " price" : ""}">
            <i class="swatch" style="background:var(${r.color})"></i>
            <div><span>${esc(r.label)}</span><strong>${fmtPx(r.val)}</strong></div>
          </div>`,
          )
          .join("")
      : emptyState("No structure levels returned."));
}

function renderConfluence(market) {
  const c = market && market.confluence;
  if (!c || !isNum(c.score)) {
    $("confBias").innerHTML = "";
    $("confBody").innerHTML = emptyState("Weighted score from MTF, momentum, structure, flow, regime, book and liquidity.", "gauge");
    return;
  }
  const score = Number(c.score);
  $("confBias").innerHTML = biasPill(c.bias);
  const comps = Object.entries(c.components || {}).filter(([k]) => k !== "note_chop");
  const names = { mtf: "MTF", orderbook: "Order book" };
  $("confBody").innerHTML = `
    <div class="kpi-value ${biasClass(c.bias)}">${fmtSigned(score)}<span class="unit">/ 10 · confidence ${fmtConf(c.confidence)}</span></div>
    <div class="gauge" title="Neutral zone −2.5 to +2.5">
      <div class="zone"></div>
      <div class="needle" style="left:${((Math.max(-10, Math.min(10, score)) + 10) / 20) * 100}%"></div>
    </div>
    <div class="gauge-scale"><span>−10 Sell</span><span>Neutral</span><span>Buy +10</span></div>
    <div class="bars">
      ${comps
        .map(([k, v]) => {
          const n = Number(v) || 0;
          const w = Math.min(50, (Math.abs(n) / 3) * 50);
          return `<div class="bar-row">
            <span class="name">${esc(names[k] || k)}</span>
            <span class="bar-track"><i class="bar-fill ${n >= 0 ? "pos" : "neg"}" style="width:${w}%"></i></span>
            <span class="val">${fmtSigned(n)}</span>
          </div>`;
        })
        .join("")}
    </div>`;
}

function renderSetup(market) {
  const s = market && market.setup;
  const mtf = (market && market.mtf_local) || {};
  if (!s || !s.type) {
    $("setupPill").innerHTML = "";
    $("setupBody").innerHTML = emptyState("Chop · mean-revert · breakout · trend continuation, plus 15m → 1d alignment.", "layers");
    return;
  }
  $("setupPill").innerHTML =
    s.trade_allowed === false
      ? `<span class="pill warn"><span class="g">!</span>No trade</span>`
      : `<span class="pill info"><span class="g">✓</span>Trade allowed</span>`;
  const frames = Object.entries(mtf.timeframes || {});
  $("setupBody").innerHTML = `
    <dl class="dl">
      <div><dt>Type</dt><dd>${esc(s.type.replace(/_/g, " "))}</dd></div>
      <div><dt>Prefers</dt><dd>${s.prefer_bias ? biasPill(s.prefer_bias) : na("No preference")}</dd></div>
      <div><dt>ADX</dt><dd>${isNum(s.adx) ? Number(s.adx).toFixed(1) : na()}</dd></div>
      <div><dt>MTF alignment</dt><dd>${esc((s.mtf_alignment || mtf.alignment || "—").replace(/_/g, " "))}</dd></div>
    </dl>
    ${
      frames.length
        ? `<div class="mtf-list">${frames
            .map(
              ([tf, f]) => `<div class="mtf-row">
                <span class="tf">${esc(tf)}</span>
                <span class="meta">RSI ${isNum(f.rsi) ? Number(f.rsi).toFixed(0) : "—"} · MACD ${esc(f.macd || "—")} · ADX ${isNum(f.adx) ? Number(f.adx).toFixed(0) : "—"}</span>
                ${trendPill(f.trend)}
              </div>`,
            )
            .join("")}</div>`
        : ""
    }
    ${s.summary ? `<div class="summary-line">${esc(s.summary)}</div>` : ""}`;
}

function renderFlow(market) {
  const f = market && market.flow;
  if (!f || !f.available) {
    $("flowBody").innerHTML = emptyState(
      market ? "No futures data for this pair (spot-only or unlisted on Binance Futures)." : "Top-trader positioning, funding, open interest and taker flow.",
      "waves",
    );
    return;
  }
  $("flowBody").innerHTML = `
    <dl class="dl">
      <div><dt>Whales (top traders)</dt><dd>${biasPill(f.whale_bias)} <span class="card-sub">${isNum(f.whale_long_pct) ? `${f.whale_long_pct}% long` : ""}</span></dd></div>
      <div><dt>Retail</dt><dd>${biasPill(f.retail_bias)} <span class="card-sub">${isNum(f.retail_long_pct) ? `${f.retail_long_pct}% long` : ""}</span></dd></div>
      <div><dt>Funding</dt><dd>${esc(f.funding_bias || "—")} <span class="card-sub">${isNum(f.funding_apr_est) ? `${f.funding_apr_est}% APR` : ""}</span></dd></div>
      <div><dt>Open interest Δ</dt><dd>${fmtPct(f.oi_change_pct, 2)}</dd></div>
      <div><dt>Taker flow</dt><dd>${esc(f.taker_bias || "—")}</dd></div>
      <div><dt>OI · price</dt><dd title="${esc(f.oi_price_signal || "")}">${esc(f.oi_price_signal || "—")}</dd></div>
      <div><dt>Basis</dt><dd>${fmtPct(f.basis_pct, 3)}</dd></div>
      <div><dt>24h change</dt><dd>${fmtPct(f.price_change_24h_pct, 2)}</dd></div>
    </dl>
    ${f.summary ? `<div class="summary-line">${esc(f.summary)}</div>` : ""}`;
}

function renderLiquidity(market) {
  const liq = (market && market.liquidity) || {};
  const book = (market && market.orderbook) || {};
  if (!liq.available && !book.available) {
    $("liqBody").innerHTML = emptyState("Estimated liquidation clusters (long cascade vs short squeeze) and depth imbalance.", "droplet");
    return;
  }
  const nl = liq.nearest_long_liq || {};
  const ns = liq.nearest_short_liq || {};
  const cas = liq.cascade || {};
  const lc = cas.long_cascade_trigger || {};
  const sq = cas.short_squeeze_trigger || {};
  $("liqBody").innerHTML = `
    <dl class="dl">
      <div><dt>Liquidity bias</dt><dd>${esc(liq.bias || "—")}</dd></div>
      <div><dt>Longs / shorts</dt><dd>${isNum(liq.long_share_pct) ? `${liq.long_share_pct}% / ${liq.short_share_pct}%` : na()}</dd></div>
      <div><dt>Nearest long-liq</dt><dd>${fmtPx(nl.price)} <span class="card-sub">${isNum(nl.distance_pct) ? `${nl.distance_pct}%` : ""}</span></dd></div>
      <div><dt>Nearest short-liq</dt><dd>${fmtPx(ns.price)} <span class="card-sub">${isNum(ns.distance_pct) ? `+${ns.distance_pct}%` : ""}</span></dd></div>
      <div><dt>Cascade trigger</dt><dd>${isNum(lc.price) ? `${fmtPx(lc.price)} <span class="card-sub">${lc.move_pct}%</span>` : na()}</dd></div>
      <div><dt>Squeeze trigger</dt><dd>${isNum(sq.price) ? `${fmtPx(sq.price)} <span class="card-sub">+${sq.move_pct}%</span>` : na()}</dd></div>
      <div><dt>Order book</dt><dd>${book.available ? esc(book.bias || "—") : na("Depth unavailable")}</dd></div>
      <div><dt>Book imbalance</dt><dd>${book.available && isNum(book.imbalance) ? fmtPct(book.imbalance * 100, 1) : na()}</dd></div>
    </dl>
    ${liq.summary ? `<div class="summary-line">${esc(liq.summary)}</div>` : ""}`;
}

/* ─── Chat ───────────────────────────────────────────────────────────── */

/** Bold the leading `KEY:` of each line in the analyst's desk card. */
function formatAnalysis(text) {
  return esc(text)
    .split("\n")
    .map((line) => line.replace(/^([A-Z][A-Z0-9/:&' ]{1,18}):/, "<strong>$1:</strong>"))
    .join("\n");
}

function tradeCard(levels) {
  const cls = biasClass(levels.bias);
  const ratio = rr(levels.entry, levels.stop_loss, levels.take_profit);
  return `<div class="trade-card ${cls}">
    <div class="head">${biasPill(levels.bias)}<span class="card-sub">Confidence ${fmtConf(levels.confidence)}</span></div>
    <div class="grid">
      <div><span>Entry</span><strong>${fmtPx(levels.entry)}</strong></div>
      <div><span>Stop</span><strong>${fmtPx(levels.stop_loss)}</strong></div>
      <div><span>Target</span><strong>${fmtPx(levels.take_profit)}</strong></div>
      <div><span>Support</span><strong>${fmtPx(levels.support)}</strong></div>
      <div><span>Resistance</span><strong>${fmtPx(levels.resistance)}</strong></div>
      <div><span>R : R</span><strong>${ratio == null ? na() : `${ratio.toFixed(1)} : 1`}</strong></div>
    </div>
  </div>`;
}

function addMessage(role, text, opts = {}) {
  const box = $("messages");
  const el = document.createElement("div");
  el.className = `msg ${opts.error ? "assistant error" : role}`;
  const who = role === "user" ? "You" : opts.provider ? `Analyst · ${PROVIDER_LABEL[opts.provider] || opts.provider}` : "Analyst";
  let html = opts.quiet ? "" : `<div class="who">${esc(who)}</div>`;
  if (opts.levels) html += tradeCard(opts.levels);
  if (opts.thinking) {
    html += `<div class="bubble thinking"><span class="dots"><i></i><i></i><i></i></span>${esc(text)}</div>`;
  } else {
    html += `<div class="bubble">${role === "assistant" ? formatAnalysis(text) : esc(text)}</div>`;
  }
  el.innerHTML = html;
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
  return el;
}

function setChatBusy(busy) {
  state.busy = busy;
  $("sendBtn").disabled = busy;
  if (busy) setBusy($("analyzeBtn"), true, "Analysing…");
  else setBusy($("analyzeBtn"), false);
}

async function runAnalyze() {
  if (state.busy) return;
  const p = { symbol: state.symbol, exchange: state.exchange, timeframe: state.timeframe };
  setChatBusy(true);
  addMessage("user", `Full analysis for ${p.exchange}:${p.symbol} (${p.timeframe})`);
  const pending = addMessage("assistant", "Pulling market data and thinking…", { thinking: true });
  try {
    const res = await api("/api/analyze", { method: "POST", body: JSON.stringify(p) });
    pending.remove();
    state.lastLevels = res.levels;
    state.lastMarket = res.market;
    addMessage("assistant", res.analysis, { levels: res.levels, provider: res.provider });
    renderDesk(res.levels, res.market);
    $("journalBtn").disabled = false;
    state.history.push(
      { role: "user", content: `Full analysis for ${p.exchange}:${p.symbol}` },
      { role: "assistant", content: res.analysis },
    );
    if (res.provider === "offline") toast("No AI selected — showing the deterministic plan only. Restart and pick one.");
    if (res.market && res.market.recorded_signal_id) {
      toast("Signal archived for later verification.");
      refreshSignals();
    }
  } catch (err) {
    pending.remove();
    addMessage("assistant", `Error: ${err.message || err}`, { error: true });
  } finally {
    setChatBusy(false);
  }
}

async function runChat(message) {
  if (state.busy || !message.trim()) return;
  setChatBusy(true);
  addMessage("user", message);
  const pending = addMessage("assistant", "Thinking…", { thinking: true });
  try {
    const res = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        symbol: state.symbol,
        exchange: state.exchange,
        timeframe: state.timeframe,
        message,
        history: state.history.slice(-8),
      }),
    });
    pending.remove();
    addMessage("assistant", res.reply, { provider: res.provider });
    state.history.push({ role: "user", content: message }, { role: "assistant", content: res.reply });
  } catch (err) {
    pending.remove();
    addMessage("assistant", `Error: ${err.message || err}`, { error: true });
  } finally {
    setChatBusy(false);
  }
}

function greet() {
  $("messages").innerHTML = "";
  addMessage(
    "assistant",
    "Pick a pair with Ctrl K, then run a full analysis. I'll pull TradingView + Binance context, score it, and give you a plan with entry, stop and target. Ask follow-ups below.",
  );
}

/* ─── Search palette ─────────────────────────────────────────────────── */

function recents() {
  try {
    return JSON.parse(store("cca_recent") || "[]");
  } catch {
    return [];
  }
}

function rememberRecent(symbol, exchange, tv) {
  const list = recents().filter((r) => r.symbol !== symbol);
  list.unshift({ symbol, exchange, tv_symbol: tv });
  store("cca_recent", JSON.stringify(list.slice(0, 6)));
}

function openPalette() {
  $("palette").hidden = false;
  const input = $("paletteInput");
  input.value = "";
  renderPaletteDefault();
  setTimeout(() => input.focus(), 0);
}

function closePalette() {
  $("palette").hidden = true;
}

function renderPaletteDefault() {
  const items = recents().map((r) => ({ kind: "pair", symbol: r.symbol, exchange: r.exchange, tv: r.tv_symbol, label: r.exchange, group: "Recent" }));
  Object.entries(PAGES).forEach(([key, label]) => items.push({ kind: "page", key, label, group: "Go to" }));
  showPaletteItems(items);
}

function showPaletteItems(items, emptyText) {
  state.paletteItems = items;
  state.paletteIndex = 0;
  const list = $("paletteList");
  if (!items.length) {
    list.innerHTML = emptyState(emptyText || "No matches — try BTC, ZEC or SOLUSDT.P", "search");
    return;
  }
  let group = null;
  list.innerHTML = items
    .map((it, i) => {
      const head = it.group !== group ? `<div class="group">${esc(it.group)}</div>` : "";
      group = it.group;
      const main =
        it.kind === "page"
          ? `${icon("arrowRight", "sm")}<strong>${esc(it.label)}</strong>`
          : `<strong>${esc(it.symbol)}</strong><span>${esc(it.label || "")}</span>${it.exchange ? `<span class="chip tag">${esc(it.exchange)}</span>` : ""}`;
      return `${head}<button type="button" class="palette-item" role="option" data-i="${i}" aria-selected="${i === 0}">${main}</button>`;
    })
    .join("");
}

function movePalette(delta) {
  const n = state.paletteItems.length;
  if (!n) return;
  state.paletteIndex = (state.paletteIndex + delta + n) % n;
  $("paletteList")
    .querySelectorAll(".palette-item")
    .forEach((b) => {
      const on = Number(b.dataset.i) === state.paletteIndex;
      b.setAttribute("aria-selected", String(on));
      if (on) b.scrollIntoView({ block: "nearest" });
    });
}

function choosePalette(i) {
  const it = state.paletteItems[i];
  if (!it) {
    const raw = $("paletteInput").value.trim();
    if (raw) setActiveSymbol(raw);
    closePalette();
    return;
  }
  closePalette();
  if (it.kind === "page") {
    location.hash = `#/${it.key}`;
    return;
  }
  setActiveSymbol(it.symbol, it.exchange, it.tv);
  if (!location.hash.startsWith("#/desk") && location.hash) location.hash = "#/desk";
}

async function searchPalette(q) {
  if (!q.trim()) {
    renderPaletteDefault();
    return;
  }
  state.paletteItems = [];
  $("paletteList").innerHTML = emptyState("Searching… the first search loads the Binance pair list.", "search");
  try {
    const res = await api(`/api/symbols/search?q=${encodeURIComponent(q)}&exchange=${encodeURIComponent(state.exchange)}&limit=20`);
    if ($("paletteInput").value !== q) return;
    showPaletteItems(
      (res.results || []).map((r) => ({ kind: "pair", symbol: r.symbol, exchange: r.exchange, tv: r.tv_symbol, label: r.label, group: "Pairs" })),
    );
  } catch {
    showPaletteItems([], "Search is unavailable — is the backend running?");
  }
}

/* ─── Dialog ─────────────────────────────────────────────────────────── */

function askDialog({ title, text, label, okLabel = "Confirm", danger = false, input = false }) {
  return new Promise((resolve) => {
    $("dialogTitle").textContent = title;
    $("dialogText").textContent = text || "";
    $("dialogField").hidden = !input;
    $("dialogLabel").textContent = label || "";
    $("dialogInput").value = "";
    const ok = $("dialogOk");
    ok.textContent = okLabel;
    ok.className = `btn ${danger ? "danger" : "primary"}`;
    $("dialog").hidden = false;
    setTimeout(() => (input ? $("dialogInput") : ok).focus(), 0);

    const finish = (value) => {
      $("dialog").hidden = true;
      $("dialogForm").onsubmit = null;
      $("dialogCancel").onclick = null;
      resolve(value);
    };
    $("dialogForm").onsubmit = (e) => {
      e.preventDefault();
      finish(input ? $("dialogInput").value.trim() : true);
    };
    $("dialogCancel").onclick = () => finish(null);
  });
}

/* ─── Watchlist ──────────────────────────────────────────────────────── */

function renderWatchlistEmpty() {
  kpiStrip("wlKpis", [
    { label: "Scored", value: na("Not scored yet"), note: "Pairs in the list" },
    { label: "Actionable", value: na("Not scored yet"), note: "Trade allowed, quality ≥ 55" },
    { label: "Top pick", value: na("Not scored yet"), note: "Highest quality" },
    { label: "Timeframe", value: esc(state.timeframe), note: "From the top bar" },
  ]);
  $("wlTable").innerHTML = emptyState("Scoring takes 20–40 seconds. Use the button above.", "list");
}

async function runWatchlist() {
  const btn = $("watchlistBtn");
  setBusy(btn, true, "Scoring…");
  $("wlTable").innerHTML = emptyState("Scoring the watchlist… this takes 20–40 seconds.", "clock");
  try {
    const res = await api(`/api/watchlist/score?timeframe=${encodeURIComponent(state.timeframe)}`);
    const rows = res.rows || [];
    const top = rows[0];
    $("wlSubtitle").textContent = `${rows.length} pairs scored on ${res.timeframe}, ${res.actionable_count || 0} actionable.`;
    kpiStrip("wlKpis", [
      { label: "Scored", value: String(rows.length), note: `On ${esc(res.timeframe)}` },
      { label: "Actionable", value: String(res.actionable_count || 0), note: "Trade allowed, quality ≥ 55" },
      { label: "Top pick", value: top ? esc(top.symbol) : na(), note: top ? `Quality ${top.quality} · ${esc(top.bias || "—")}` : "—" },
      { label: "Timeframe", value: esc(res.timeframe), note: "From the top bar" },
    ]);
    if (!rows.length) {
      $("wlTable").innerHTML = emptyState("No results.");
      return;
    }
    $("wlTable").innerHTML = `<table class="data">
      <thead><tr>
        <th>Pair</th><th>Quality</th><th>Bias</th><th class="num">Confluence</th><th>Setup</th><th>MTF</th><th>Book</th><th>Liquidity</th><th class="num">Price</th><th></th>
      </tr></thead>
      <tbody>${rows
        .map(
          (r) => `<tr>
          <td class="sym">${esc(r.symbol)}</td>
          <td><span class="quality"><span class="track"><i style="width:${Number(r.quality) || 0}%"></i></span>${esc(r.quality ?? 0)}</span></td>
          <td>${r.error ? na(r.error) : biasPill(r.bias)}</td>
          <td class="num">${fmtSigned(r.confluence)}</td>
          <td>${r.setup ? `<span class="chip">${esc(r.setup.replace(/_/g, " "))}</span>${r.trade_allowed === false ? ' <span class="pill warn"><span class="g">!</span>chop</span>' : ""}` : na()}</td>
          <td>${r.mtf_alignment ? esc(r.mtf_alignment.replace(/_/g, " ").toLowerCase()) : na()}</td>
          <td>${r.book_bias ? esc(r.book_bias) : na("Depth unavailable")}</td>
          <td>${r.liq_bias ? esc(r.liq_bias) : na("No futures data")}</td>
          <td class="num">${fmtPx(r.price)}</td>
          <td><div class="row-actions"><button class="btn compact" type="button" data-open="${esc(r.symbol)}">Open</button></div></td>
        </tr>`,
        )
        .join("")}</tbody></table>`;
    $("wlTable")
      .querySelectorAll("[data-open]")
      .forEach((b) =>
        b.addEventListener("click", () => {
          setActiveSymbol(b.dataset.open, "BINANCE");
          location.hash = "#/desk";
        }),
      );
  } catch (err) {
    $("wlTable").innerHTML = emptyState(`Scoring failed: ${err.message || err}`);
  } finally {
    setBusy(btn, false);
  }
}

/* ─── Journal ────────────────────────────────────────────────────────── */

async function refreshJournal() {
  try {
    const res = await api("/api/journal?limit=100");
    const st = res.stats || {};
    const entries = res.entries || [];
    $("navJournalCount").textContent = st.open ? String(st.open) : "";
    $("jrSubtitle").textContent = entries.length
      ? `${st.total || entries.length} trades logged, ${st.open || 0} still open.`
      : "Trades you logged from the desk.";
    kpiStrip("jrKpis", [
      { label: "Hit rate", value: isNum(st.hit_rate) ? `${Math.round(st.hit_rate * 100)}%` : na("No closed trades yet"), note: `${st.closed || 0} closed trades` },
      { label: "Wins / losses", value: `${st.wins || 0} / ${st.losses || 0}`, note: `${st.breakeven || 0} breakeven` },
      { label: "Open", value: String(st.open || 0), note: "Awaiting an outcome" },
      { label: "Average R", value: isNum(st.avg_r) ? fmtSigned(st.avg_r, 2) : na("Needs exit prices"), note: "Per closed trade" },
    ]);
    if (!entries.length) {
      $("jrTable").innerHTML = emptyState("Nothing logged yet. Run a full analysis on the desk, then use Log to journal.", "book");
      return;
    }
    $("jrTable").innerHTML = `<table class="data">
      <thead><tr><th>Logged</th><th>Pair</th><th>Side</th><th>Setup</th><th class="num">Entry</th><th class="num">Stop</th><th class="num">Target</th><th>Status</th><th class="num">R</th><th></th></tr></thead>
      <tbody>${entries
        .map((e) => {
          const open = e.status === "open";
          const actions = open
            ? `<button class="btn compact" type="button" data-close="${esc(e.id)}" data-status="win">Win</button>
               <button class="btn compact" type="button" data-close="${esc(e.id)}" data-status="loss">Loss</button>
               <button class="btn compact" type="button" data-close="${esc(e.id)}" data-status="be">BE</button>
               <button class="btn compact" type="button" data-close="${esc(e.id)}" data-status="skipped" title="Skipped">${icon("x", "sm")}</button>`
            : `<button class="btn compact" type="button" data-del="${esc(e.id)}" title="Delete">${icon("trash", "sm")}</button>`;
          return `<tr>
            <td>${fmtWhen(e.created_at)}</td>
            <td class="sym">${esc(e.symbol)} <span class="card-sub">${esc(e.timeframe || "")}</span></td>
            <td>${biasPill(e.side)}</td>
            <td>${e.setup ? `<span class="chip">${esc(e.setup.replace(/_/g, " "))}</span>` : na()}</td>
            <td class="num">${fmtPx(e.entry)}</td>
            <td class="num">${fmtPx(e.stop_loss)}</td>
            <td class="num">${fmtPx(e.take_profit)}</td>
            <td>${statusPill(e.status)}</td>
            <td class="num">${isNum(e.r_multiple) ? fmtSigned(e.r_multiple, 2) : na(open ? "Still open" : "No exit price")}</td>
            <td><div class="row-actions">${actions}</div></td>
          </tr>`;
        })
        .join("")}</tbody></table>`;
    $("jrTable")
      .querySelectorAll("[data-close]")
      .forEach((b) => b.addEventListener("click", () => closeJournal(b.dataset.close, b.dataset.status)));
    $("jrTable")
      .querySelectorAll("[data-del]")
      .forEach((b) => b.addEventListener("click", () => deleteJournal(b.dataset.del)));
  } catch (err) {
    $("jrTable").innerHTML = emptyState(`Journal unavailable: ${err.message || err}`);
  }
}

async function closeJournal(id, status) {
  let exit_price = null;
  if (status === "win" || status === "loss" || status === "be") {
    const raw = await askDialog({
      title: `Close as ${status === "be" ? "breakeven" : status}`,
      text: "Add the exit price to compute the R multiple, or leave it blank.",
      label: "Exit price (optional)",
      okLabel: "Close trade",
      input: true,
    });
    if (raw === null) return;
    if (raw) {
      exit_price = Number(raw.replace(/,/g, ""));
      if (Number.isNaN(exit_price)) {
        toast("Exit price must be a number.");
        return;
      }
    }
  }
  try {
    await api(`/api/journal/${encodeURIComponent(id)}/close`, { method: "POST", body: JSON.stringify({ status, exit_price }) });
    toast(`Trade closed as ${status}.`);
  } catch (err) {
    toast(`Could not close trade: ${err.message || err}`);
  }
  refreshJournal();
}

async function deleteJournal(id) {
  const ok = await askDialog({ title: "Delete this entry?", text: "It is removed from the journal and its stats.", okLabel: "Delete", danger: true });
  if (!ok) return;
  try {
    await api(`/api/journal/${encodeURIComponent(id)}`, { method: "DELETE" });
    toast("Entry deleted.");
  } catch (err) {
    toast(`Could not delete: ${err.message || err}`);
  }
  refreshJournal();
}

async function logToJournal() {
  const levels = state.lastLevels;
  const market = state.lastMarket;
  if (!levels) return;
  const setup = (market && market.setup && market.setup.type) || null;
  try {
    await api("/api/journal", {
      method: "POST",
      body: JSON.stringify({
        symbol: state.symbol,
        timeframe: state.timeframe,
        side: levels.bias === "Sell" ? "Sell" : "Buy",
        setup,
        entry: levels.entry,
        stop_loss: levels.stop_loss,
        take_profit: levels.take_profit,
        confluence: market && market.confluence ? market.confluence.score : null,
        notes: levels.reasoning || "",
      }),
    });
    toast(`Logged ${state.symbol} ${levels.bias === "Sell" ? "Sell" : "Buy"} to the journal.`);
    refreshJournal();
  } catch (err) {
    toast(`Journal error: ${err.message || err}`);
  }
}

/* ─── Signals ────────────────────────────────────────────────────────── */

function signalKpis(st) {
  kpiStrip("sgKpis", [
    { label: "Hit rate", value: isNum(st.hit_rate) ? `${Math.round(st.hit_rate * 100)}%` : na("No decided signals yet"), note: "Target before stop" },
    { label: "Wins / losses", value: `${st.wins || 0} / ${st.losses || 0}`, note: `${st.expired || 0} expired` },
    { label: "Open", value: String(st.open || 0), note: "Neither level hit yet" },
    { label: "Average R", value: isNum(st.avg_r) ? fmtSigned(st.avg_r, 2) : na("No closed signals"), note: `${st.total || 0} archived` },
  ]);
}

async function refreshSignals() {
  try {
    const res = await api("/api/signals?limit=100");
    const st = res.stats || {};
    const rows = res.signals || [];
    $("navSignalCount").textContent = st.open ? String(st.open) : "";
    signalKpis(st);
    if (!rows.length) {
      $("sgTable").innerHTML = emptyState("No archived signals yet. A full analysis with a Buy or Sell bias saves one here.", "target");
      return;
    }
    $("sgTable").innerHTML = `<table class="data">
      <thead><tr><th>Created</th><th>Pair</th><th>Bias</th><th>Setup</th><th class="num">Entry</th><th class="num">Stop</th><th class="num">Target</th><th class="num">Score</th><th>Status</th><th class="num">R</th><th></th></tr></thead>
      <tbody>${rows
        .map(
          (s) => `<tr>
          <td>${fmtWhen(s.created_at)}</td>
          <td class="sym">${esc(s.symbol)} <span class="card-sub">${esc(s.timeframe || "")}</span></td>
          <td>${biasPill(s.bias)}</td>
          <td>${s.setup ? `<span class="chip">${esc(s.setup.replace(/_/g, " "))}</span>` : na()}</td>
          <td class="num">${fmtPx(s.entry)}</td>
          <td class="num">${fmtPx(s.stop_loss)}</td>
          <td class="num">${fmtPx(s.take_profit)}</td>
          <td class="num">${fmtSigned(s.confluence)}</td>
          <td title="${esc(s.outcome || "")}">${statusPill(s.status)}</td>
          <td class="num">${isNum(s.r_multiple) ? fmtSigned(s.r_multiple, 2) : na(s.status === "open" ? "Still open" : "Not decided")}</td>
          <td><div class="row-actions"><button class="btn compact" type="button" data-sg="${esc(s.id)}">Check</button></div></td>
        </tr>`,
        )
        .join("")}</tbody></table>`;
    $("sgTable")
      .querySelectorAll("[data-sg]")
      .forEach((btn) =>
        btn.addEventListener("click", async () => {
          setBusy(btn, true, "…");
          try {
            const r = await api(`/api/signals/${encodeURIComponent(btn.dataset.sg)}/verify`, { method: "POST" });
            toast(`${r.signal.symbol}: ${r.signal.status} (${r.signal.outcome || "checked"})`);
          } catch (err) {
            toast(`Check failed: ${err.message || err}`);
          }
          refreshSignals();
        }),
      );
  } catch (err) {
    $("sgTable").innerHTML = emptyState(`Signals unavailable: ${err.message || err}`);
  }
}

async function verifySignals() {
  const btn = $("verifySignalsBtn");
  setBusy(btn, true, "Verifying…");
  try {
    const res = await api("/api/signals/verify?only_open=true&limit=50", { method: "POST" });
    toast(`Checked ${res.checked || 0} signals, ${res.updated || 0} updated.`);
  } catch (err) {
    toast(`Verify failed: ${err.message || err}`);
  } finally {
    setBusy(btn, false);
  }
  refreshSignals();
}

/* ─── Health ─────────────────────────────────────────────────────────── */

const PROVIDER_LABEL = {
  claude: "Claude API",
  claude_code: "Claude subscription",
  cursor: "Cursor",
  openai: "OpenAI",
  offline: "No AI",
  none: "No AI",
};

async function refreshHealth() {
  const chip = $("providerChip");
  try {
    const h = await api("/api/health");
    const on = h.ai_provider && h.ai_provider !== "none";
    chip.className = `provider-chip ${on ? "on" : "off"}`;
    $("providerName").textContent = PROVIDER_LABEL[h.ai_provider] || h.ai_provider;
    $("providerModel").textContent = on ? h.ai_model || "" : "Pick one in start.ps1 / start.sh";
    chip.title = `AI: ${PROVIDER_LABEL[h.ai_provider] || h.ai_provider}${h.ai_model ? ` (${h.ai_model})` : ""} · TradingView lib ${h.tradingview_ready ? "ready" : "missing"}`;
  } catch {
    chip.className = "provider-chip off";
    $("providerName").textContent = "Backend offline";
    $("providerModel").textContent = "Start the API on :8000";
  }
}

/* ─── Wiring ─────────────────────────────────────────────────────────── */

function autoGrow(t) {
  t.style.height = "auto";
  t.style.height = `${Math.min(t.scrollHeight, 140)}px`;
}

function wire() {
  hydrateIcons();
  paintThemeButton();
  setFolded(store("cca_rail_folded") === "1");

  $("themeBtn").addEventListener("click", toggleTheme);
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (!document.documentElement.dataset.theme) {
      paintThemeButton();
      mountChart();
    }
  });
  $("railToggle").addEventListener("click", () => setFolded(!$("shell").classList.contains("folded")));
  $("menuBtn").addEventListener("click", () => $("shell").classList.add("nav-open"));
  $("scrim").addEventListener("click", () => $("shell").classList.remove("nav-open"));

  $("exchange").addEventListener("change", () => setActiveSymbol(state.symbol, $("exchange").value));
  $("timeframe").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-tf]");
    if (b) setTimeframe(b.dataset.tf);
  });

  $("scopePair").addEventListener("click", openPalette);
  $("searchTrigger").addEventListener("click", openPalette);
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      if ($("palette").hidden) openPalette();
      else closePalette();
    }
    if (e.key === "Escape") {
      if (!$("palette").hidden) closePalette();
      if (!$("dialog").hidden) $("dialogCancel").click();
    }
  });
  $("palette").addEventListener("mousedown", (e) => {
    if (e.target === $("palette")) closePalette();
  });
  $("paletteInput").addEventListener("input", (e) => {
    clearTimeout(state.searchTimer);
    const q = e.target.value;
    state.searchTimer = setTimeout(() => searchPalette(q), 160);
  });
  $("paletteInput").addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      movePalette(1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      movePalette(-1);
    } else if (e.key === "Enter") {
      e.preventDefault();
      choosePalette(state.paletteItems.length ? state.paletteIndex : -1);
    }
  });
  $("paletteList").addEventListener("click", (e) => {
    const b = e.target.closest(".palette-item");
    if (b) choosePalette(Number(b.dataset.i));
  });

  $("analyzeBtn").addEventListener("click", runAnalyze);
  $("journalBtn").addEventListener("click", logToJournal);
  $("clearChat").addEventListener("click", () => {
    state.history = [];
    greet();
  });
  $("form").addEventListener("submit", (e) => {
    e.preventDefault();
    const text = $("input").value.trim();
    if (!text) return;
    $("input").value = "";
    autoGrow($("input"));
    runChat(text);
  });
  $("input").addEventListener("input", (e) => autoGrow(e.target));
  $("input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      $("form").requestSubmit();
    }
  });
  $("suggestions").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (b) runChat(b.textContent);
  });

  $("watchlistBtn").addEventListener("click", runWatchlist);
  $("refreshJournalBtn").addEventListener("click", refreshJournal);
  $("verifySignalsBtn").addEventListener("click", verifySignals);
  $("refreshSignalsBtn").addEventListener("click", refreshSignals);

  const tf = store("cca_tf");
  state.timeframe = TV_INTERVAL[tf] ? tf : "1h";
  document.querySelectorAll("#timeframe button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.tf === state.timeframe)));

  const last = recents()[0];
  setActiveSymbol(last ? last.symbol : "SOLUSDT", last ? last.exchange : "BINANCE", last ? last.tv_symbol : undefined);
  renderDesk(null, null);
  greet();
  renderWatchlistEmpty();
  window.addEventListener("hashchange", route);
  route();
  refreshHealth();
  refreshJournal();
  refreshSignals();
}

wire();
