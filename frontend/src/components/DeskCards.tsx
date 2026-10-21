import type { Market, TradeLevels } from "../api";
import { biasClass, currentPrice, fmtConf, fmtPct, fmtPx, fmtSigned, humanize, isNum } from "../lib/format";
import { BiasPill, Card, EmptyState, Na, TrendPill, V } from "./ui";

const LEVEL_ROWS: [string, keyof TradeLevels, string][] = [
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

export function LevelsBoard({ levels, market }: Readonly<{ levels: TradeLevels | null; market: Market | null }>) {
  if (!levels) {
    return (
      <div className="levels-board">
        <div className="overline">Structure levels</div>
        <EmptyState text="Levels appear here after a full analysis." icon="layers" />
      </div>
    );
  }
  const rows = LEVEL_ROWS.map(([label, key, color]) => ({ label, val: levels[key], color, price: false })).filter(
    (r): r is { label: string; val: number; color: string; price: boolean } => isNum(r.val),
  );
  const px = currentPrice(market);
  if (isNum(px)) rows.push({ label: "Last price", val: px, color: "--text", price: true });
  rows.sort((a, b) => b.val - a.val);
  return (
    <div className="levels-board">
      <div className="overline">Structure levels</div>
      {rows.length ? (
        rows.map((r) => (
          <div className={`level-row${r.price ? " price" : ""}`} key={r.label}>
            <i className="swatch" style={{ background: `var(${r.color})` }} />
            <div>
              <span>{r.label}</span>
              <strong>{fmtPx(r.val)}</strong>
            </div>
          </div>
        ))
      ) : (
        <EmptyState text="No structure levels returned." />
      )}
    </div>
  );
}

const COMPONENT_NAMES: Record<string, string> = { mtf: "MTF", orderbook: "Order book" };

export function ConfluenceCard({ market }: Readonly<{ market: Market | null }>) {
  const c = market?.confluence;
  if (!c || !isNum(c.score)) {
    return (
      <Card title="Confluence" icon="gauge">
        <EmptyState
          text="Weighted score from MTF, momentum, structure, flow, regime, book and liquidity."
          icon="gauge"
        />
      </Card>
    );
  }
  const score = Number(c.score);
  const comps = Object.entries(c.components ?? {}).filter(([k]) => k !== "note_chop");
  const needle = ((Math.max(-10, Math.min(10, score)) + 10) / 20) * 100;
  return (
    <Card title="Confluence" icon="gauge" right={<BiasPill bias={c.bias} />}>
      <div className={`kpi-value ${biasClass(c.bias)}`}>
        {fmtSigned(score)}
        <span className="unit">/ 10 · confidence {fmtConf(c.confidence) ?? "—"}</span>
      </div>
      <div className="gauge" title="Neutral zone −2.5 to +2.5">
        <div className="zone" />
        <div className="needle" style={{ left: `${needle}%` }} />
      </div>
      <div className="gauge-scale">
        <span>−10 Sell</span>
        <span>Neutral</span>
        <span>Buy +10</span>
      </div>
      <div className="bars">
        {comps.map(([k, v]) => {
          const n = Number(v) || 0;
          return (
            <div className="bar-row" key={k}>
              <span className="name">{COMPONENT_NAMES[k] ?? k}</span>
              <span className="bar-track">
                <i className={`bar-fill ${n >= 0 ? "pos" : "neg"}`} style={{ width: `${Math.min(50, (Math.abs(n) / 3) * 50)}%` }} />
              </span>
              <span className="val">{fmtSigned(n)}</span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

export function SetupCard({ market }: Readonly<{ market: Market | null }>) {
  const s = market?.setup;
  if (!s?.type) {
    return (
      <Card title="Setup & timeframes" icon="layers">
        <EmptyState text="Chop · mean-revert · breakout · trend continuation, plus 15m → 1d alignment." icon="layers" />
      </Card>
    );
  }
  const frames = Object.entries(market?.mtf_local?.timeframes ?? {});
  const pill =
    s.trade_allowed === false ? (
      <span className="pill warn">
        <span className="g">!</span>No trade
      </span>
    ) : (
      <span className="pill info">
        <span className="g">✓</span>Trade allowed
      </span>
    );
  return (
    <Card title="Setup & timeframes" icon="layers" right={pill}>
      <dl className="dl">
        <div>
          <dt>Type</dt>
          <dd>{humanize(s.type)}</dd>
        </div>
        <div>
          <dt>Prefers</dt>
          <dd>{s.prefer_bias ? <BiasPill bias={s.prefer_bias} /> : <Na reason="No preference" />}</dd>
        </div>
        <div>
          <dt>ADX</dt>
          <dd>{isNum(s.adx) ? Number(s.adx).toFixed(1) : <Na />}</dd>
        </div>
        <div>
          <dt>MTF alignment</dt>
          <dd>{humanize(s.mtf_alignment ?? market?.mtf_local?.alignment) || <Na />}</dd>
        </div>
      </dl>
      {frames.length ? (
        <div className="mtf-list">
          {frames.map(([tf, f]) => (
            <div className="mtf-row" key={tf}>
              <span className="tf">{tf}</span>
              <span className="meta">
                RSI {isNum(f.rsi) ? Number(f.rsi).toFixed(0) : "—"} · MACD {f.macd ?? "—"} · ADX{" "}
                {isNum(f.adx) ? Number(f.adx).toFixed(0) : "—"}
              </span>
              <TrendPill trend={f.trend} />
            </div>
          ))}
        </div>
      ) : null}
      {s.summary ? <div className="summary-line">{s.summary}</div> : null}
    </Card>
  );
}

function Dd({ label, children }: Readonly<{ label: string; children: React.ReactNode }>) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

export function FlowCard({ market }: Readonly<{ market: Market | null }>) {
  const f = market?.flow;
  if (!f?.available) {
    return (
      <Card title="Whales & derivatives" icon="waves">
        <EmptyState
          text={
            market
              ? "No futures data for this pair (spot-only or unlisted on Binance Futures)."
              : "Top-trader positioning, funding, open interest and taker flow."
          }
          icon="waves"
        />
      </Card>
    );
  }
  return (
    <Card title="Whales & derivatives" icon="waves">
      <dl className="dl">
        <Dd label="Whales (top traders)">
          <BiasPill bias={f.whale_bias} />{" "}
          <span className="card-sub">{isNum(f.whale_long_pct) ? `${f.whale_long_pct}% long` : ""}</span>
        </Dd>
        <Dd label="Retail">
          <BiasPill bias={f.retail_bias} />{" "}
          <span className="card-sub">{isNum(f.retail_long_pct) ? `${f.retail_long_pct}% long` : ""}</span>
        </Dd>
        <Dd label="Funding">
          {f.funding_bias ?? "—"}{" "}
          <span className="card-sub">{isNum(f.funding_apr_est) ? `${f.funding_apr_est}% APR` : ""}</span>
        </Dd>
        <Dd label="Open interest Δ">
          <V value={fmtPct(f.oi_change_pct, 2)} />
        </Dd>
        <Dd label="Taker flow">{f.taker_bias ?? <Na />}</Dd>
        <Dd label="OI · price">
          <span title={f.oi_price_signal}>{f.oi_price_signal ?? <Na />}</span>
        </Dd>
        <Dd label="Basis">
          <V value={fmtPct(f.basis_pct, 3)} />
        </Dd>
        <Dd label="24h change">
          <V value={fmtPct(f.price_change_24h_pct, 2)} />
        </Dd>
      </dl>
      {f.summary ? <div className="summary-line">{f.summary}</div> : null}
    </Card>
  );
}

export function LiquidityCard({ market }: Readonly<{ market: Market | null }>) {
  const liq = market?.liquidity ?? {};
  const book = market?.orderbook ?? {};
  if (!liq.available && !book.available) {
    return (
      <Card title="Liquidity & order book" icon="droplet">
        <EmptyState
          text="Estimated liquidation clusters (long cascade vs short squeeze) and depth imbalance."
          icon="droplet"
        />
      </Card>
    );
  }
  const nl = liq.nearest_long_liq ?? {};
  const ns = liq.nearest_short_liq ?? {};
  const lc = liq.cascade?.long_cascade_trigger ?? {};
  const sq = liq.cascade?.short_squeeze_trigger ?? {};
  return (
    <Card title="Liquidity & order book" icon="droplet">
      <dl className="dl">
        <Dd label="Liquidity bias">{liq.bias ?? <Na />}</Dd>
        <Dd label="Longs / shorts">
          {isNum(liq.long_share_pct) ? `${liq.long_share_pct}% / ${liq.short_share_pct}%` : <Na />}
        </Dd>
        <Dd label="Nearest long-liq">
          <V value={fmtPx(nl.price)} /> <span className="card-sub">{isNum(nl.distance_pct) ? `${nl.distance_pct}%` : ""}</span>
        </Dd>
        <Dd label="Nearest short-liq">
          <V value={fmtPx(ns.price)} /> <span className="card-sub">{isNum(ns.distance_pct) ? `+${ns.distance_pct}%` : ""}</span>
        </Dd>
        <Dd label="Cascade trigger">
          {isNum(lc.price) ? (
            <>
              {fmtPx(lc.price)} <span className="card-sub">{lc.move_pct}%</span>
            </>
          ) : (
            <Na />
          )}
        </Dd>
        <Dd label="Squeeze trigger">
          {isNum(sq.price) ? (
            <>
              {fmtPx(sq.price)} <span className="card-sub">+{sq.move_pct}%</span>
            </>
          ) : (
            <Na />
          )}
        </Dd>
        <Dd label="Order book">{book.available ? (book.bias ?? "—") : <Na reason="Depth unavailable" />}</Dd>
        <Dd label="Book imbalance">
          {book.available && isNum(book.imbalance) ? fmtPct(book.imbalance * 100, 1) : <Na />}
        </Dd>
      </dl>
      {liq.summary ? <div className="summary-line">{liq.summary}</div> : null}
    </Card>
  );
}
