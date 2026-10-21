const TV_INTERVAL = {
  "1m": "1",
  "5m": "5",
  "15m": "15",
  "30m": "30",
  "1h": "60",
  "4h": "240",
  "1D": "D",
  "1d": "D",
};

const state = {
  history: [],
  busy: false,
  widget: null,
  symbol: "SOLUSDT",
  tvSymbol: "BINANCE:SOLUSDT",
  searchTimer: null,
  lastLevels: null,
  lastMarket: null,
};

const $ = (id) => document.getElementById(id);

function pair() {
  return {
    symbol: state.symbol,
    exchange: $("exchange").value,
    timeframe: $("timeframe").value,
  };
}

function tvSymbol() {
  return state.tvSymbol || `${$("exchange").value}:${state.symbol}`;
}

function fmtPx(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: 6 });
}

function fmtConf(c) {
  if (c == null || Number.isNaN(c)) return "—";
  const pct = c <= 1 ? Math.round(c * 100) : Math.round(c);
  return `${pct}%`;
}

function setActiveSymbol(symbol, exchange, tv) {
  const sym = String(symbol || "").trim().toUpperCase();
  const ex = (exchange || $("exchange").value || "BINANCE").toUpperCase();
  state.symbol = sym;
  state.tvSymbol = (tv || `${ex}:${sym}`).toUpperCase();
  $("exchange").value = ex;
  $("symbol").value = state.symbol;
  $("chatSymbol").value = state.symbol;
  hideSuggest("topSuggest");
  hideSuggest("chatSuggest");
  mountChart();
  $("input").placeholder = `Ask about ${state.symbol}… e.g. "Is this a long setup?"`;
}

function addBubble(role, content, levels, market) {
  const box = $("messages");
  const el = document.createElement("div");
  el.className = `bubble ${role}`;
  el.innerHTML = `<div class="who">${role === "user" ? "YOU" : "ANALYST"}</div>`;

  if (role === "assistant" && levels) {
    el.appendChild(buildTradeCard(levels));
    const scoreCard = buildScoreCard(market);
    if (scoreCard) el.appendChild(scoreCard);
    const setupCard = buildSetupCard(market);
    if (setupCard) el.appendChild(setupCard);
    const liqCard = buildLiquidityCard(market);
    if (liqCard) el.appendChild(liqCard);
    const flowCard = buildFlowCard(market);
    if (flowCard) el.appendChild(flowCard);
  }

  const body = document.createElement("div");
  body.className = "bubble-body";
  body.textContent = content;
  el.appendChild(body);
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
}

function buildTradeCard(levels) {
  const card = document.createElement("div");
  const bias = (levels.bias || "Neutral").toLowerCase();
  card.className = `trade-card bias-${bias}`;
  card.innerHTML = `
    <div class="trade-bias">${levels.bias || "—"}</div>
    <div class="trade-grid">
      <div><span>Entry</span><strong>${fmtPx(levels.entry)}</strong></div>
      <div><span>Stop</span><strong>${fmtPx(levels.stop_loss)}</strong></div>
      <div><span>Target</span><strong>${fmtPx(levels.take_profit)}</strong></div>
      <div><span>Confidence</span><strong>${fmtConf(levels.confidence)}</strong></div>
      <div><span>Support</span><strong>${fmtPx(levels.support)}</strong></div>
      <div><span>Resistance</span><strong>${fmtPx(levels.resistance)}</strong></div>
      <div><span>Trend</span><strong>${levels.trend || "—"}</strong></div>
      <div><span>EMA20</span><strong>${fmtPx(levels.ema20)}</strong></div>
    </div>
    ${
      levels.trend_line
        ? `<div class="trade-trendline">${levels.trend_line}</div>`
        : ""
    }
  `;
  return card;
}

function buildScoreCard(market) {
  const c = market && market.confluence;
  if (!c || c.score == null) return null;
  const mtf = market.mtf_local || {};
  const regime = market.regime || {};
  const book = market.orderbook || {};
  const el = document.createElement("div");
  el.className = "score-card";
  const score = Number(c.score);
  const cls = score >= 2.5 ? "buy" : score <= -2.5 ? "sell" : "neutral";
  el.innerHTML = `
    <div class="score-title">Confluence score</div>
    <div class="score-main ${cls}">
      <strong>${score >= 0 ? "+" : ""}${score}</strong>
      <span>/ 10 → ${c.bias || "—"}</span>
    </div>
    <div class="score-sub">${c.summary || ""}</div>
    <div class="score-sub"><strong>MTF</strong> ${mtf.summary || mtf.alignment || "—"}</div>
    <div class="score-sub"><strong>Regime</strong> ${regime.summary || "—"}</div>
    <div class="score-sub"><strong>Book</strong> ${book.available ? book.summary || book.bias : "—"}</div>
    <div class="score-sub"><strong>Liq</strong> ${(market.liquidity && market.liquidity.available) ? (market.liquidity.summary || market.liquidity.bias) : "—"}</div>
  `;
  return el;
}

function buildSetupCard(market) {
  const s = market && market.setup;
  if (!s || !s.type) return null;
  const el = document.createElement("div");
  el.className = "flow-card";
  const ok = s.trade_allowed !== false;
  el.innerHTML = `
    <div class="flow-title">Setup classifier</div>
    <div class="flow-grid">
      <div><span>Type</span><strong>${s.type}</strong></div>
      <div><span>Trade</span><strong class="${ok ? "wl-ok" : "wl-chop"}">${ok ? "allowed" : "blocked (chop)"}</strong></div>
      <div><span>Prefer</span><strong>${s.prefer_bias || "—"}</strong></div>
      <div><span>ADX</span><strong>${s.adx == null ? "—" : s.adx}</strong></div>
    </div>
    <div class="flow-summary">${s.summary || ""}</div>
  `;
  return el;
}

function buildLiquidityCard(market) {
  const liq = market && market.liquidity;
  if (!liq || !liq.available) return null;
  const nl = liq.nearest_long_liq || {};
  const ns = liq.nearest_short_liq || {};
  const cas = liq.cascade || {};
  const sq = cas.short_squeeze_trigger || {};
  const lc = cas.long_cascade_trigger || {};
  const el = document.createElement("div");
  el.className = "flow-card";
  el.innerHTML = `
    <div class="flow-title">Liquidity map · squeeze</div>
    <div class="flow-grid">
      <div><span>Bias</span><strong>${liq.bias || "—"}</strong></div>
      <div><span>Pts</span><strong>${liq.points == null ? "—" : (liq.points >= 0 ? "+" : "") + liq.points}</strong></div>
      <div><span>Longs</span><strong>${liq.long_share_pct == null ? "—" : liq.long_share_pct + "%"}</strong></div>
      <div><span>Shorts</span><strong>${liq.short_share_pct == null ? "—" : liq.short_share_pct + "%"}</strong></div>
      <div><span>Long-liq</span><strong>${fmtPx(nl.price)} (${nl.distance_pct ?? "—"}%)</strong></div>
      <div><span>Short-liq</span><strong>${fmtPx(ns.price)} (${ns.distance_pct ?? "—"}%)</strong></div>
      <div><span>Cascade</span><strong>${lc.move_pct != null ? lc.move_pct + "% @" + fmtPx(lc.price) : "—"}</strong></div>
      <div><span>Squeeze</span><strong>${sq.move_pct != null ? "+" + sq.move_pct + "% @" + fmtPx(sq.price) : "—"}</strong></div>
    </div>
    <div class="flow-summary">${liq.summary || ""}</div>
  `;
  return el;
}

function buildFlowCard(market) {
  const flow = market && market.flow;
  if (!flow || !flow.available) return null;
  const el = document.createElement("div");
  el.className = "flow-card";
  el.innerHTML = `
    <div class="flow-title">Whales & derivatives flow</div>
    <div class="flow-grid">
      <div><span>Whales</span><strong>${flow.whale_bias || "—"} (${flow.whale_long_pct ?? "—"}% L)</strong></div>
      <div><span>Retail</span><strong>${flow.retail_bias || "—"} (${flow.retail_long_pct ?? "—"}% L)</strong></div>
      <div><span>Funding</span><strong>${flow.funding_bias || "—"}</strong></div>
      <div><span>OI Δ</span><strong>${flow.oi_change_pct == null ? "—" : flow.oi_change_pct + "%"}</strong></div>
      <div><span>Taker</span><strong>${flow.taker_bias || "—"}</strong></div>
      <div><span>OI·Price</span><strong>${flow.oi_price_signal || "—"}</strong></div>
      <div><span>Basis</span><strong>${flow.basis_pct == null ? "—" : flow.basis_pct + "%"}</strong></div>
      <div><span>24h</span><strong>${flow.price_change_24h_pct == null ? "—" : flow.price_change_24h_pct + "%"}</strong></div>
    </div>
    <div class="flow-summary">${flow.summary || flow.positioning_divergence || ""}</div>
  `;
  return el;
}

function setLevels(levels, market) {
  const root = $("levels");
  if (!levels) {
    root.innerHTML = `<span class="pill">Bias —</span>`;
    renderStructureBoard(null, null);
    return;
  }
  const flow = market && market.flow;
  root.innerHTML = `
    <span class="pill ${(levels.bias || "neutral").toLowerCase()}">Bias ${levels.bias || "—"}</span>
    <span class="pill">S ${fmtPx(levels.support)}</span>
    <span class="pill">R ${fmtPx(levels.resistance)}</span>
    <span class="pill">Entry ${fmtPx(levels.entry)}</span>
    <span class="pill">SL ${fmtPx(levels.stop_loss)}</span>
    <span class="pill">TP ${fmtPx(levels.take_profit)}</span>
    ${
      flow && flow.available
        ? `<span class="pill">Whales ${flow.whale_bias || "—"}</span><span class="pill">Fund ${flow.funding_bias || "—"}</span>`
        : ""
    }
    ${
      market && market.confluence && market.confluence.score != null
        ? `<span class="pill">Score ${market.confluence.score >= 0 ? "+" : ""}${market.confluence.score}</span>`
        : ""
    }
    ${
      market && market.setup && market.setup.type
        ? `<span class="pill">${market.setup.type}${market.setup.trade_allowed === false ? " · chop" : ""}</span>`
        : ""
    }
    ${
      market && market.orderbook && market.orderbook.available
        ? `<span class="pill">Book ${market.orderbook.bias || "—"}</span>`
        : ""
    }
    ${
      market && market.liquidity && market.liquidity.available
        ? `<span class="pill">Liq ${market.liquidity.bias || "—"}</span>`
        : ""
    }
  `;
  renderStructureBoard(levels, flow, market);
}

function renderStructureBoard(levels, flow, market) {
  const root = $("structureLines");
  if (!levels) {
    root.innerHTML =
      '<div class="structure-empty">Run Full analysis to plot support / resistance / trend levels.</div>';
    return;
  }
  const rows = [
    { key: "Resistance 2", val: levels.resistance_2, color: "#f0a29a" },
    { key: "Resistance", val: levels.resistance, color: "#e57368" },
    { key: "Target", val: levels.take_profit, color: "#7de0b5" },
    { key: "EMA20", val: levels.ema20, color: "#6ec1ff" },
    { key: "Entry", val: levels.entry, color: "#f5d76e" },
    { key: "EMA50", val: levels.ema50, color: "#9b8cff" },
    { key: "Support", val: levels.support, color: "#5ecf9a" },
    { key: "Support 2", val: levels.support_2, color: "#3da87a" },
    { key: "Stop", val: levels.stop_loss, color: "#ff8a80" },
  ]
    .filter((r) => r.val != null && !Number.isNaN(r.val))
    .sort((a, b) => b.val - a.val);

  if (!rows.length) {
    root.innerHTML = '<div class="structure-empty">No structure levels returned.</div>';
    return;
  }

  let html = rows
    .map(
      (r) => `
      <div class="structure-row">
        <div class="structure-swatch" style="background:${r.color}"></div>
        <div>
          <span>${r.key}</span>
          <strong>${fmtPx(r.val)}</strong>
        </div>
      </div>`,
    )
    .join("");

  if (levels.trend_line || levels.trend) {
    html += `<div class="structure-note"><strong>${levels.trend || "Trend"}</strong><br/>${
      levels.trend_line || ""
    }</div>`;
  }
  if (flow && flow.available) {
    html += `<div class="structure-note"><strong>Flow</strong><br/>${
      flow.summary || ""
    }</div>`;
  }
  const conf = market && market.confluence;
  if (conf && conf.summary) {
    html += `<div class="structure-note"><strong>Score</strong><br/>${conf.summary}</div>`;
  }
  const setup = market && market.setup;
  if (setup && setup.summary) {
    html += `<div class="structure-note"><strong>Setup</strong><br/>${setup.summary}</div>`;
  }
  const book = market && market.orderbook;
  if (book && book.available && book.summary) {
    html += `<div class="structure-note"><strong>Book</strong><br/>${book.summary}</div>`;
  }
  const liq = market && market.liquidity;
  if (liq && liq.available) {
    const nl = liq.nearest_long_liq || {};
    const ns = liq.nearest_short_liq || {};
    html += `<div class="structure-note"><strong>Liquidity</strong><br/>${
      liq.summary || ""
    }<br/>Long-liq ${fmtPx(nl.price)} · Short-liq ${fmtPx(ns.price)}</div>`;
  }
  const mtf = market && market.mtf_local;
  if (mtf && mtf.summary) {
    html += `<div class="structure-note"><strong>MTF</strong><br/>${mtf.summary}</div>`;
  }
  root.innerHTML = html;
}

function mountChart() {
  $("tvLabel").textContent = tvSymbol();
  const el = $("tv_chart");
  el.innerHTML = "";
  if (!window.TradingView) return;
  const p = pair();
  state.widget = new TradingView.widget({
    autosize: true,
    symbol: tvSymbol(),
    interval: TV_INTERVAL[p.timeframe] || "60",
    timezone: "Etc/UTC",
    theme: "dark",
    style: "1",
    locale: "en",
    toolbar_bg: "#0e1612",
    enable_publishing: false,
    allow_symbol_change: false,
    container_id: "tv_chart",
    studies: ["MAExp@tv-basicstudies", "MAExp@tv-basicstudies"],
  });
}

function hideSuggest(id) {
  const el = $(id);
  el.hidden = true;
  el.innerHTML = "";
}

function showSuggest(suggestId, results, sourceInput) {
  const el = $(suggestId);
  if (!results.length) {
    el.hidden = false;
    el.innerHTML = `<div class="suggest-empty">No matches — try BTW, ZEC, or SOLUSDT.P</div>`;
    return;
  }
  el.hidden = false;
  el.innerHTML = results
    .map(
      (r) => `
      <button type="button" class="suggest-item" data-symbol="${r.symbol}" data-exchange="${r.exchange}" data-tv="${r.tv_symbol}">
        <strong>${r.symbol}</strong>
        <span>${r.label}</span>
      </button>`,
    )
    .join("");
  el.querySelectorAll(".suggest-item").forEach((btn) => {
    btn.addEventListener("mousedown", (e) => {
      e.preventDefault();
      setActiveSymbol(btn.dataset.symbol, btn.dataset.exchange, btn.dataset.tv);
    });
  });
}

async function runSearch(query, suggestId, sourceInput) {
  const q = query.trim();
  if (q.length < 1) {
    hideSuggest(suggestId);
    return;
  }
  try {
    const ex = $("exchange").value;
    const res = await fetch(
      `/api/symbols/search?q=${encodeURIComponent(q)}&exchange=${encodeURIComponent(ex)}&limit=20`,
    ).then((r) => r.json());
    showSuggest(suggestId, res.results || [], sourceInput);
  } catch {
    showSuggest(suggestId, [], sourceInput);
  }
}

function wireSearch(inputId, suggestId) {
  const input = $(inputId);
  input.addEventListener("input", () => {
    clearTimeout(state.searchTimer);
    state.searchTimer = setTimeout(() => {
      runSearch(input.value, suggestId, input);
    }, 180);
  });
  input.addEventListener("focus", () => {
    if (input.value.trim().length >= 1) runSearch(input.value, suggestId, input);
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const first = $(suggestId).querySelector(".suggest-item");
      if (first) {
        setActiveSymbol(first.dataset.symbol, first.dataset.exchange, first.dataset.tv);
      } else {
        setActiveSymbol(input.value);
      }
    }
    if (e.key === "Escape") hideSuggest(suggestId);
  });
  input.addEventListener("blur", () => {
    setTimeout(() => hideSuggest(suggestId), 150);
  });
}

async function refreshHealth() {
  try {
    const h = await fetch("/api/health").then((r) => r.json());
    $("provider").textContent = `Provider: ${h.ai_provider}`;
    $("health").textContent = h.tradingview_ready ? "TV lib ready" : "TV lib missing";
  } catch {
    $("provider").textContent = "Provider: backend offline";
    $("health").textContent = "offline";
  }
}

async function runAnalyze() {
  if (state.busy) return;
  const p = pair();
  state.busy = true;
  addBubble("user", `Full analysis for ${p.exchange}:${p.symbol} (${p.timeframe})`);
  addBubble("assistant", "Fetching market data and thinking…");
  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(p),
    }).then(async (r) => {
      const body = await r.text();
      if (!r.ok) throw new Error(_formatApiError(body));
      return JSON.parse(body);
    });
    $("messages").lastChild.remove();
    addBubble("assistant", res.analysis, res.levels, res.market);
    setLevels(res.levels, res.market);
    state.lastLevels = res.levels;
    state.lastMarket = res.market;
    state.history.push(
      { role: "user", content: `Full analysis for ${p.exchange}:${p.symbol}` },
      { role: "assistant", content: res.analysis },
    );
    if (res.market && res.market.recorded_signal_id) {
      refreshSignals();
    }
  } catch (err) {
    $("messages").lastChild.remove();
    addBubble("assistant", `Error: ${err.message || err}`);
  } finally {
    state.busy = false;
  }
}

async function runChat(message) {
  if (state.busy || !message.trim()) return;
  const p = pair();
  state.busy = true;
  addBubble("user", message);
  addBubble("assistant", "Fetching market data and thinking…");
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...p,
        message,
        history: state.history.slice(-8),
      }),
    }).then(async (r) => {
      const body = await r.text();
      if (!r.ok) throw new Error(_formatApiError(body));
      return JSON.parse(body);
    });
    $("messages").lastChild.remove();
    addBubble("assistant", res.reply);
    state.history.push(
      { role: "user", content: message },
      { role: "assistant", content: res.reply },
    );
  } catch (err) {
    $("messages").lastChild.remove();
    addBubble("assistant", `Error: ${err.message || err}`);
  } finally {
    state.busy = false;
  }
}

function _formatApiError(body) {
  try {
    const j = JSON.parse(body);
    if (typeof j.detail === "string") return j.detail;
    if (Array.isArray(j.detail)) {
      return j.detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
    }
    return body;
  } catch {
    return body || "Request failed";
  }
}

function wire() {
  addBubble(
    "assistant",
    "Search any coin in the box above the chat (try BTW or ZEC). Pick a result — chart and analysis sync together.",
  );
  wireSearch("symbol", "topSuggest");
  wireSearch("chatSymbol", "chatSuggest");
  $("exchange").addEventListener("change", () => {
    const ex = $("exchange").value;
    const bare = state.symbol.includes(":") ? state.symbol.split(":")[1] : state.symbol;
    state.tvSymbol = `${ex}:${bare}`;
    mountChart();
  });
  $("timeframe").addEventListener("change", () => mountChart());
  $("form").addEventListener("submit", (e) => {
    e.preventDefault();
    const text = $("input").value.trim();
    $("input").value = "";
    runChat(text);
  });
  $("input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      $("form").requestSubmit();
    }
  });
  $("analyzeBtn").addEventListener("click", runAnalyze);
  $("watchlistBtn").addEventListener("click", runWatchlist);
  $("refreshJournalBtn").addEventListener("click", refreshJournal);
  $("journalBtn").addEventListener("click", logToJournal);
  $("verifySignalsBtn").addEventListener("click", verifySignals);
  $("refreshSignalsBtn").addEventListener("click", refreshSignals);
  setActiveSymbol("SOLUSDT", "BINANCE");
  refreshHealth();
  refreshJournal();
  refreshSignals();
}

async function runWatchlist() {
  const body = $("watchlistBody");
  body.innerHTML = `<div class="tool-empty">Scoring… (may take ~20–40s)</div>`;
  try {
    const tf = $("timeframe").value;
    const res = await fetch(`/api/watchlist/score?timeframe=${encodeURIComponent(tf)}`).then(
      (r) => r.json(),
    );
    const rows = res.rows || [];
    if (!rows.length) {
      body.innerHTML = `<div class="tool-empty">No results</div>`;
      return;
    }
    body.innerHTML = rows
      .map((r) => {
        const q = r.quality ?? 0;
        const cls = !r.trade_allowed ? "wl-chop" : q >= 60 ? "wl-ok" : "wl-bad";
        return `<div class="wl-row">
          <strong class="${cls}">${r.symbol}</strong>
          <span>${r.bias || "—"}</span>
          <span>${r.setup || "—"}</span>
          <span>Q ${q} · ${r.confluence != null ? (r.confluence >= 0 ? "+" : "") + r.confluence : "—"}</span>
          <button type="button" data-sym="${r.symbol}">Open</button>
        </div>`;
      })
      .join("");
    body.querySelectorAll("button[data-sym]").forEach((btn) => {
      btn.addEventListener("click", () => setActiveSymbol(btn.dataset.sym));
    });
  } catch (err) {
    body.innerHTML = `<div class="tool-empty">Error: ${err.message || err}</div>`;
  }
}

async function refreshJournal() {
  try {
    const res = await fetch("/api/journal?limit=40").then((r) => r.json());
    const st = res.stats || {};
    const hr = st.hit_rate == null ? "—" : `${Math.round(st.hit_rate * 100)}%`;
    $("journalStats").textContent =
      `Hit-rate ${hr} · W${st.wins || 0}/L${st.losses || 0} · open ${st.open || 0}` +
      (st.avg_r != null ? ` · avg R ${st.avg_r}` : "");
    const entries = res.entries || [];
    const body = $("journalBody");
    if (!entries.length) {
      body.innerHTML = `<div class="tool-empty">No journal entries yet.</div>`;
      return;
    }
    body.innerHTML = entries
      .map((e) => {
        const open = e.status === "open";
        return `<div class="jr-row">
          <strong>${e.symbol}</strong>
          <span>${e.side} · ${e.setup || "—"}</span>
          <span>${e.status}</span>
          <span>${e.entry != null ? fmtPx(e.entry) : "—"}</span>
          <span>${
            open
              ? `<button type="button" data-win="${e.id}">W</button>
                 <button type="button" data-loss="${e.id}">L</button>
                 <button type="button" data-skip="${e.id}">×</button>`
              : e.r_multiple != null
                ? `${e.r_multiple}R`
                : ""
          }</span>
        </div>`;
      })
      .join("");
    body.querySelectorAll("[data-win]").forEach((b) =>
      b.addEventListener("click", () => closeJournal(b.dataset.win, "win")),
    );
    body.querySelectorAll("[data-loss]").forEach((b) =>
      b.addEventListener("click", () => closeJournal(b.dataset.loss, "loss")),
    );
    body.querySelectorAll("[data-skip]").forEach((b) =>
      b.addEventListener("click", () => closeJournal(b.dataset.skip, "skipped")),
    );
  } catch (err) {
    $("journalStats").textContent = `Journal offline: ${err.message || err}`;
  }
}

async function closeJournal(id, status) {
  let exit_price = null;
  if (status === "win" || status === "loss") {
    const raw = window.prompt("Exit price (optional)", "");
    if (raw != null && raw.trim()) exit_price = Number(raw);
  }
  await fetch(`/api/journal/${id}/close`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, exit_price }),
  });
  refreshJournal();
}

async function logToJournal() {
  const levels = state.lastLevels;
  const market = state.lastMarket;
  if (!levels) {
    addBubble("assistant", "Run Full analysis first, then Journal+ to log the plan.");
    return;
  }
  const p = pair();
  const setup = (market && market.setup && market.setup.type) || null;
  const conf = market && market.confluence ? market.confluence.score : null;
  try {
    await fetch("/api/journal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        symbol: p.symbol,
        timeframe: p.timeframe,
        side: levels.bias === "Sell" ? "Sell" : "Buy",
        setup,
        entry: levels.entry,
        stop_loss: levels.stop_loss,
        take_profit: levels.take_profit,
        confluence: conf,
        notes: levels.reasoning || "",
      }),
    }).then(async (r) => {
      if (!r.ok) throw new Error(await r.text());
      return r.json();
    });
    addBubble("assistant", `Logged ${p.symbol} ${levels.bias} to journal (${setup || "setup n/a"}).`);
    refreshJournal();
  } catch (err) {
    addBubble("assistant", `Journal error: ${err.message || err}`);
  }
}

function _fmtSignalStats(st) {
  const hr = st.hit_rate == null ? "—" : `${Math.round(st.hit_rate * 100)}%`;
  return `Hit-rate ${hr} · W${st.wins || 0}/L${st.losses || 0}/exp ${st.expired || 0} · open ${st.open || 0}` +
    (st.avg_r != null ? ` · avg R ${st.avg_r}` : "");
}

async function refreshSignals() {
  try {
    const res = await fetch("/api/signals?limit=40").then((r) => r.json());
    const st = res.stats || {};
    $("signalStats").textContent = _fmtSignalStats(st);
    const body = $("signalBody");
    const rows = res.signals || [];
    if (!rows.length) {
      body.innerHTML =
        `<div class="tool-empty">No archived signals yet. Full analysis with Buy/Sell auto-saves here.</div>`;
      return;
    }
    body.innerHTML = rows
      .map((s) => {
        const stCls =
          s.status === "win"
            ? "sg-win"
            : s.status === "loss"
              ? "sg-loss"
              : s.status === "expired"
                ? "sg-expired"
                : "sg-open";
        const when = (s.created_at || "").slice(5, 16).replace("T", " ");
        return `<div class="sg-row">
          <strong>${s.symbol}</strong>
          <span>${s.bias}</span>
          <span class="${stCls}">${s.status}${s.r_multiple != null ? ` ${s.r_multiple}R` : ""}</span>
          <span>${s.setup || "—"} · ${when}</span>
          <button type="button" data-sg="${s.id}">Check</button>
        </div>`;
      })
      .join("");
    body.querySelectorAll("[data-sg]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await fetch(`/api/signals/${btn.dataset.sg}/verify`, { method: "POST" });
        refreshSignals();
      });
    });
  } catch (err) {
    $("signalStats").textContent = `Signals offline: ${err.message || err}`;
  }
}

async function verifySignals() {
  $("signalStats").textContent = "Verifying open signals vs candles…";
  try {
    const res = await fetch("/api/signals/verify?only_open=true&limit=40", {
      method: "POST",
    }).then((r) => r.json());
    $("signalStats").textContent =
      `Checked ${res.checked || 0}, updated ${res.updated || 0} · ` +
      _fmtSignalStats(res.stats || {});
    refreshSignals();
  } catch (err) {
    $("signalStats").textContent = `Verify failed: ${err.message || err}`;
  }
}

wire();
