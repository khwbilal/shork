import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import CompareArrows from "@mui/icons-material/CompareArrows";
import LayersOutlined from "@mui/icons-material/LayersOutlined";
import SpeedOutlined from "@mui/icons-material/SpeedOutlined";
import WaterDropOutlined from "@mui/icons-material/WaterDropOutlined";
import WavesOutlined from "@mui/icons-material/WavesOutlined";
import type { ReactNode } from "react";
import type { CorrelationStat, Market, TradeLevels } from "../api";
import { biasClass, currentPrice, fmtConf, fmtFixed, fmtPct, fmtPx, fmtSigned, humanize, isNum } from "../lib/format";
import { BiasPill, EmptyState, Na, Num, Pill, SectionCard, TrendPill, V, monoSx } from "./ui";

type LevelColor = "res" | "target" | "entry" | "ema20" | "ema50" | "support" | "stop";

const LEVEL_ROWS: [string, keyof TradeLevels, LevelColor][] = [
  ["Resistance 2", "resistance_2", "res"],
  ["Resistance", "resistance", "res"],
  ["Target", "take_profit", "target"],
  ["EMA 20", "ema20", "ema20"],
  ["Entry", "entry", "entry"],
  ["EMA 50", "ema50", "ema50"],
  ["Support", "support", "support"],
  ["Support 2", "support_2", "support"],
  ["Stop", "stop_loss", "stop"],
];

type LevelRow = { label: string; val: number; color: string; price: boolean };

export function LevelsBoard({ levels, market }: Readonly<{ levels: TradeLevels | null; market: Market | null }>) {
  const heading = (
    <Typography variant="overline" component="div" sx={{ color: "text.secondary", mb: 1 }}>
      Structure levels
    </Typography>
  );
  if (!levels) {
    return (
      <Box>
        {heading}
        <EmptyState text="Levels appear here after a full analysis." icon={<LayersOutlined />} />
      </Box>
    );
  }
  const rows: LevelRow[] = [];
  for (const [label, key, color] of LEVEL_ROWS) {
    const val = levels[key];
    if (isNum(val)) rows.push({ label, val: Number(val), color: `levels.${color}`, price: false });
  }
  const px = currentPrice(market);
  if (isNum(px)) rows.push({ label: "Last price", val: px, color: "text.primary", price: true });
  rows.sort((a, b) => b.val - a.val);
  return (
    <Box>
      {heading}
      {rows.length ? (
        <Stack spacing={0.5}>
          {rows.map((r) => (
            <Stack
              key={r.label}
              direction="row"
             
              spacing={1}
              sx={{ alignItems: "center",
                px: 1,
                py: 0.5,
                borderRadius: 1,
                bgcolor: r.price ? "surface.action" : "transparent",
                fontWeight: r.price ? 700 : 400,
              }}
            >
              <Box component="i" aria-hidden sx={{ width: 4, height: 18, borderRadius: 1, bgcolor: r.color, flexShrink: 0 }} />
              <Typography variant="caption" sx={{ flex: 1, color: "text.secondary" }}>
                {r.label}
              </Typography>
              <Num sx={{ fontSize: "0.8125rem", fontWeight: 600 }}>{fmtPx(r.val)}</Num>
            </Stack>
          ))}
        </Stack>
      ) : (
        <EmptyState text="No structure levels returned." />
      )}
    </Box>
  );
}

const COMPONENT_NAMES: Record<string, string> = { mtf: "MTF", orderbook: "Order book" };

function directionColor(bias: string | null | undefined): string {
  const cls = biasClass(bias);
  if (cls === "buy") return "success.main";
  if (cls === "sell") return "error.main";
  return "text.primary";
}

export function ConfluenceCard({ market }: Readonly<{ market: Market | null }>) {
  const c = market?.confluence;
  if (!c || !isNum(c.score)) {
    return (
      <SectionCard title="Confluence" icon={<SpeedOutlined />}>
        <EmptyState text="Weighted score from MTF, momentum, structure, flow, regime, book and liquidity." icon={<SpeedOutlined />} />
      </SectionCard>
    );
  }
  const score = Number(c.score);
  const comps = Object.entries(c.components ?? {}).filter(([k]) => k !== "note_chop");
  const needle = ((Math.max(-10, Math.min(10, score)) + 10) / 20) * 100;
  return (
    <SectionCard title="Confluence" icon={<SpeedOutlined />} right={<BiasPill bias={c.bias} />}>
      <Box sx={[monoSx, { fontSize: "1.5rem", fontWeight: 700, color: directionColor(c.bias) }]}>
        {fmtSigned(score)}
        <Box component="span" sx={{ fontSize: "0.75rem", color: "text.secondary", fontWeight: 500, ml: 0.75 }}>
          / 10 · confidence {fmtConf(c.confidence) ?? <Na />}
        </Box>
      </Box>
      <Tooltip title="Neutral zone −2.5 to +2.5">
        <Box sx={{ position: "relative", height: 8, borderRadius: 4, bgcolor: "divider", mt: 1.5, mb: 0.5 }}>
          <Box sx={{ position: "absolute", left: "37.5%", width: "25%", top: 0, bottom: 0, bgcolor: "grey.500", opacity: 0.35 }} />
          <Box
            sx={{
              position: "absolute",
              left: `${String(needle)}%`,
              top: -4,
              width: 3,
              height: 16,
              ml: "-1.5px",
              borderRadius: 1,
              bgcolor: "text.primary",
            }}
          />
        </Box>
      </Tooltip>
      <Stack direction="row" sx={{ justifyContent: "space-between", color: "text.secondary", mb: 1.5 }}>
        <Typography variant="caption">−10 Sell</Typography>
        <Typography variant="caption">Neutral</Typography>
        <Typography variant="caption">Buy +10</Typography>
      </Stack>
      <Stack spacing={0.75}>
        {comps.map(([k, v]) => {
          const val = Number(v) || 0;
          const width = Math.min(50, (Math.abs(val) / 3) * 50);
          return (
            <Box key={k} sx={{ display: "grid", gridTemplateColumns: "88px minmax(0, 1fr) 44px", alignItems: "center", gap: 1 }}>
              <Typography variant="caption" noWrap sx={{ color: "text.secondary", textTransform: "capitalize" }}>
                {COMPONENT_NAMES[k] ?? k}
              </Typography>
              <Box sx={{ position: "relative", height: 6, bgcolor: "action.hover", borderRadius: 3 }}>
                <Box sx={{ position: "absolute", left: "50%", top: -2, bottom: -2, width: "1px", bgcolor: "divider" }} />
                <Box
                  sx={{
                    position: "absolute",
                    top: 0,
                    bottom: 0,
                    borderRadius: 3,
                    width: `${String(width)}%`,
                    left: val >= 0 ? "50%" : `${String(50 - width)}%`,
                    bgcolor: val >= 0 ? "success.main" : "error.main",
                  }}
                />
              </Box>
              <Num sx={{ fontSize: "0.75rem", textAlign: "right" }}>{fmtSigned(val)}</Num>
            </Box>
          );
        })}
      </Stack>
    </SectionCard>
  );
}

function Dl({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <Box component="dl" sx={{ m: 0, display: "grid", gridTemplateColumns: { xs: "minmax(0, 1fr)", sm: "repeat(2, minmax(0, 1fr))" }, gap: 1.5 }}>
      {children}
    </Box>
  );
}

function Dd({ label, children }: Readonly<{ label: string; children: ReactNode }>) {
  return (
    <Box sx={{ minWidth: 0 }}>
      <Typography component="dt" variant="caption" sx={{ color: "text.secondary", display: "block" }}>
        {label}
      </Typography>
      <Box component="dd" sx={{ m: 0, mt: 0.25, typography: "body2", fontWeight: 500, display: "flex", alignItems: "center", gap: 0.75, flexWrap: "wrap" }}>
        {children}
      </Box>
    </Box>
  );
}

function Sub({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <Typography component="span" variant="caption" sx={{ color: "text.secondary" }}>
      {children}
    </Typography>
  );
}

function Summary({ text }: Readonly<{ text?: string }>) {
  if (!text) return null;
  return (
    <Typography variant="caption" component="p" sx={{ color: "text.secondary", mt: 1.5, mb: 0, pt: 1.5, borderTop: 1, borderColor: "divider" }}>
      {text}
    </Typography>
  );
}

export function SetupCard({ market }: Readonly<{ market: Market | null }>) {
  const s = market?.setup;
  if (!s?.type) {
    return (
      <SectionCard title="Setup & timeframes" icon={<LayersOutlined />}>
        <EmptyState text="Chop, mean revert, breakout or trend continuation, plus 15m to 1d alignment." icon={<LayersOutlined />} />
      </SectionCard>
    );
  }
  const frames = Object.entries(market?.mtf_local?.timeframes ?? {});
  const pill =
    s.trade_allowed === false ? <Pill glyph="!" label="No trade" tone="warn" /> : <Pill glyph="✓" label="Trade allowed" tone="info" />;
  const alignment = humanize(s.mtf_alignment ?? market?.mtf_local?.alignment);
  return (
    <SectionCard title="Setup & timeframes" icon={<LayersOutlined />} right={pill}>
      <Dl>
        <Dd label="Type">{humanize(s.type)}</Dd>
        <Dd label="Prefers">{s.prefer_bias ? <BiasPill bias={s.prefer_bias} /> : <Na reason="No preference" />}</Dd>
        <Dd label="ADX">
          <V value={fmtFixed(s.adx, 1)} />
        </Dd>
        <Dd label="MTF alignment">{alignment || <Na />}</Dd>
      </Dl>
      {frames.length ? (
        <Stack spacing={0.75} sx={{ mt: 2 }}>
          {frames.map(([tf, f]) => (
            <Stack key={tf} direction="row" spacing={1} sx={{ alignItems: "center" }}>
              <Num sx={{ width: 36, fontWeight: 600, fontSize: "0.8125rem" }}>{tf}</Num>
              <Typography variant="caption" sx={{ flex: 1, color: "text.secondary", minWidth: 0 }} noWrap>
                RSI <V value={fmtFixed(f.rsi, 0)} /> · MACD {f.macd ?? <Na />} · ADX <V value={fmtFixed(f.adx, 0)} />
              </Typography>
              <TrendPill trend={f.trend} />
            </Stack>
          ))}
        </Stack>
      ) : null}
      <Summary text={s.summary} />
    </SectionCard>
  );
}

export function FlowCard({ market }: Readonly<{ market: Market | null }>) {
  const f = market?.flow;
  if (!f?.available) {
    return (
      <SectionCard title="Whales & derivatives" icon={<WavesOutlined />}>
        <EmptyState
          text={
            market
              ? "No futures data for this pair (spot only, or not listed on Binance Futures)."
              : "Top-trader positioning, funding, open interest and taker flow."
          }
          icon={<WavesOutlined />}
        />
      </SectionCard>
    );
  }
  return (
    <SectionCard title="Whales & derivatives" icon={<WavesOutlined />}>
      <Dl>
        <Dd label="Whales (top traders)">
          <BiasPill bias={f.whale_bias} />
          {isNum(f.whale_long_pct) ? <Sub>{f.whale_long_pct}% long</Sub> : null}
        </Dd>
        <Dd label="Retail">
          <BiasPill bias={f.retail_bias} />
          {isNum(f.retail_long_pct) ? <Sub>{f.retail_long_pct}% long</Sub> : null}
        </Dd>
        <Dd label="Funding">
          {f.funding_bias ?? <Na />}
          {isNum(f.funding_apr_est) ? <Sub>{f.funding_apr_est}% APR</Sub> : null}
        </Dd>
        <Dd label="Open interest Δ">
          <V value={fmtPct(f.oi_change_pct, 2)} />
        </Dd>
        <Dd label="Taker flow">{f.taker_bias ?? <Na />}</Dd>
        <Dd label="OI · price">{f.oi_price_signal ?? <Na />}</Dd>
        <Dd label="Basis">
          <V value={fmtPct(f.basis_pct, 3)} />
        </Dd>
        <Dd label="24h change">
          <V value={fmtPct(f.price_change_24h_pct, 2)} />
        </Dd>
      </Dl>
      <Summary text={f.summary} />
    </SectionCard>
  );
}

export function LiquidityCard({ market }: Readonly<{ market: Market | null }>) {
  const liq = market?.liquidity ?? {};
  const book = market?.orderbook ?? {};
  if (!liq.available && !book.available) {
    return (
      <SectionCard title="Liquidity & order book" icon={<WaterDropOutlined />}>
        <EmptyState text="Estimated liquidation clusters (long cascade vs short squeeze) and depth imbalance." icon={<WaterDropOutlined />} />
      </SectionCard>
    );
  }
  const nl = liq.nearest_long_liq ?? {};
  const ns = liq.nearest_short_liq ?? {};
  const lc = liq.cascade?.long_cascade_trigger ?? {};
  const sq = liq.cascade?.short_squeeze_trigger ?? {};
  return (
    <SectionCard title="Liquidity & order book" icon={<WaterDropOutlined />}>
      <Dl>
        <Dd label="Liquidity bias">{liq.bias ?? <Na />}</Dd>
        <Dd label="Longs / shorts">
          {isNum(liq.long_share_pct) ? <Num>{`${String(liq.long_share_pct)}% / ${String(liq.short_share_pct)}%`}</Num> : <Na />}
        </Dd>
        <Dd label="Nearest long liquidation">
          <V value={fmtPx(nl.price)} />
          {isNum(nl.distance_pct) ? <Sub>{nl.distance_pct}%</Sub> : null}
        </Dd>
        <Dd label="Nearest short liquidation">
          <V value={fmtPx(ns.price)} />
          {isNum(ns.distance_pct) ? <Sub>+{ns.distance_pct}%</Sub> : null}
        </Dd>
        <Dd label="Cascade trigger">
          {isNum(lc.price) ? (
            <>
              <Num>{fmtPx(lc.price)}</Num> <Sub>{lc.move_pct}%</Sub>
            </>
          ) : (
            <Na />
          )}
        </Dd>
        <Dd label="Squeeze trigger">
          {isNum(sq.price) ? (
            <>
              <Num>{fmtPx(sq.price)}</Num> <Sub>+{sq.move_pct}%</Sub>
            </>
          ) : (
            <Na />
          )}
        </Dd>
        <Dd label="Order book">{book.available ? (book.bias ?? <Na />) : <Na reason="Depth unavailable" />}</Dd>
        <Dd label="Book imbalance">
          {book.available && isNum(book.imbalance) ? <Num>{fmtPct(book.imbalance * 100, 1)}</Num> : <Na />}
        </Dd>
      </Dl>
      <Summary text={liq.summary} />
    </SectionCard>
  );
}

const WINDOW_LABEL: Record<string, string> = { "30d_1h": "30 days of 1h", "90d_1d": "90 days of 1d" };

function StatCell({ stat, field }: Readonly<{ stat: CorrelationStat | undefined; field: "correlation" | "beta" }>) {
  if (!stat?.available) return <Na reason={stat?.error ?? "Not computed"} />;
  const v = stat[field];
  const text = field === "correlation" ? fmtSigned(v, 2) : fmtFixed(v, 2);
  return <V value={text} reason={stat.error ?? "Not enough overlapping candles"} />;
}

/** Correlation and beta to BTC and ETH from the analysis snapshot (WL-036). */
export function CorrelationCard({ market }: Readonly<{ market: Market | null }>) {
  if (!market) return null;
  const c = market.correlation;
  const icon = <CompareArrows />;
  if (!c) {
    return (
      <SectionCard title="Correlation to BTC and ETH" icon={icon}>
        <EmptyState text="This analysis did not include correlation data." icon={icon} />
      </SectionCard>
    );
  }
  if (!c.available) {
    return (
      <SectionCard title="Correlation to BTC and ETH" icon={icon} right={<Na reason={c.error ?? "Not available"} />}>
        <EmptyState text={`Correlation unavailable${c.error ? `: ${c.error}` : "."}`} icon={icon} />
      </SectionCard>
    );
  }
  const windows = ["30d_1h", "90d_1d"];
  return (
    <SectionCard title="Correlation to BTC and ETH" icon={icon} noPadding>
      <Box sx={{ overflowX: "auto" }}>
        <Table size="small" sx={{ minWidth: 420 }}>
          <TableHead>
            <TableRow>
              <TableCell>Window</TableCell>
              <TableCell align="right">BTC corr</TableCell>
              <TableCell align="right">BTC beta</TableCell>
              <TableCell align="right">ETH corr</TableCell>
              <TableCell align="right">ETH beta</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {windows.map((key) => {
              const w = c.windows?.[key];
              return (
                <TableRow key={key}>
                  <TableCell>{WINDOW_LABEL[key] ?? key}</TableCell>
                  <TableCell align="right">
                    <StatCell stat={w?.btc} field="correlation" />
                  </TableCell>
                  <TableCell align="right">
                    <StatCell stat={w?.btc} field="beta" />
                  </TableCell>
                  <TableCell align="right">
                    <StatCell stat={w?.eth} field="correlation" />
                  </TableCell>
                  <TableCell align="right">
                    <StatCell stat={w?.eth} field="beta" />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </Box>
      <Typography variant="caption" component="p" sx={{ color: "text.secondary", px: 2, py: 1.25, m: 0 }}>
        Pearson correlation of log returns (−1 to +1) and beta (how far the pair moves per 1% of the benchmark).
      </Typography>
    </SectionCard>
  );
}
