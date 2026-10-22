import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import ArrowDownward from "@mui/icons-material/ArrowDownward";
import ArrowForward from "@mui/icons-material/ArrowForward";
import ArrowUpward from "@mui/icons-material/ArrowUpward";
import InfoOutlined from "@mui/icons-material/InfoOutlined";
import { useCallback, useEffect, useState } from "react";
import { api, type PulseCell, type PulseResponse, type PulseSymbol } from "../api";
import { fmtFixed, fmtPct, fmtPx, fmtWhen } from "../lib/format";
import { BiasPill, Na, Num, monoSx } from "./ui";

const POLL_MS = 20_000;
const TFS = ["1M", "1w", "1d", "1h", "15m"] as const;

function TrendArrow({ trend }: Readonly<{ trend: PulseCell["trend"] }>) {
  const sx = { fontSize: 16, color: "text.secondary" };
  if (trend === "up") return <ArrowUpward aria-label="Trend up" sx={sx} />;
  if (trend === "down") return <ArrowDownward aria-label="Trend down" sx={sx} />;
  if (trend === "flat") return <ArrowForward aria-label="Trend flat" sx={sx} />;
  return <Na reason="No trend" />;
}

function Cell({ tf, cell, rule }: Readonly<{ tf: string; cell: PulseCell | undefined; rule: string }>) {
  const body =
    cell && cell.available ? (
      <Stack direction="row" spacing={0.5} sx={{ alignItems: "center", minHeight: 26 }}>
        <TrendArrow trend={cell.trend} />
        <Tooltip title="RSI 14">
          <Box component="span" sx={[monoSx, { fontSize: "0.75rem", color: "text.secondary", minWidth: 22 }]}>
            {fmtFixed(cell.rsi, 0) ?? <Na reason="No RSI" />}
          </Box>
        </Tooltip>
        <BiasPill bias={cell.bias} title={rule} />
      </Stack>
    ) : (
      <Box sx={{ minHeight: 26, display: "flex", alignItems: "center" }}>
        <Na reason={cell?.error ?? "Not available"} />
      </Box>
    );
  return (
    <Box sx={{ px: 1.25, py: 0.75, borderLeft: 1, borderColor: "divider", minWidth: 0 }}>
      <Typography variant="overline" component="div" sx={[monoSx, { color: "text.secondary", lineHeight: 1.4, textTransform: "none" }]}>
        {tf}
      </Typography>
      {body}
    </Box>
  );
}

function SymbolRow({ s, rule }: Readonly<{ s: PulseSymbol; rule: string }>) {
  const byTf = new Map(s.timeframes.map((c) => [c.tf, c]));
  const change = fmtPct(s.change_24h_pct, 2);
  let glyph = "";
  if (s.change_24h_pct !== null && s.change_24h_pct !== undefined) glyph = s.change_24h_pct >= 0 ? "▲ " : "▼ ";
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "minmax(132px, 1.2fr) repeat(5, minmax(118px, 1fr))",
        alignItems: "stretch",
        "& + &": { borderTop: 1, borderColor: "divider" },
      }}
    >
      <Box sx={{ px: 1.5, py: 0.75, minWidth: 0 }}>
        <Typography variant="overline" component="div" sx={{ color: "text.secondary", lineHeight: 1.4 }}>
          {s.symbol.replace(/USDT$/, "")}
        </Typography>
        {s.available ? (
          <Stack direction="row" spacing={1} sx={{ alignItems: "baseline" }}>
            <Num sx={{ fontWeight: 700, fontSize: "0.9375rem" }}>{fmtPx(s.price) ?? <Na />}</Num>
            <Tooltip title="24h change">
              <Box component="span" sx={[monoSx, { fontSize: "0.75rem", color: "text.secondary" }]}>
                {change ? `${glyph}${change}` : <Na />}
              </Box>
            </Tooltip>
          </Stack>
        ) : (
          <Na reason={s.error ?? "Ticker unavailable"} />
        )}
      </Box>
      {TFS.map((tf) => (
        <Cell key={tf} tf={tf} cell={byTf.get(tf)} rule={rule} />
      ))}
    </Box>
  );
}

/** BTC and ETH pulse (WL-035): polled every 20 s while the desk is on screen and the tab is visible. */
export default function PulseStrip({ active }: Readonly<{ active: boolean }>) {
  const [data, setData] = useState<PulseResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [visible, setVisible] = useState(() => document.visibilityState === "visible");

  useEffect(() => {
    const onVis = () => setVisible(document.visibilityState === "visible");
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, []);

  const load = useCallback(() => {
    api
      .pulse()
      .then((res) => {
        setData(res);
        setError(null);
      })
      .catch((err: unknown) => setError((err as Error).message));
  }, []);

  useEffect(() => {
    if (!active || !visible) return;
    load();
    const timer = setInterval(load, POLL_MS);
    return () => clearInterval(timer);
  }, [active, visible, load]);

  let body;
  if (data) {
    body = data.symbols.map((s) => <SymbolRow key={s.symbol} s={s} rule={data.rule} />);
  } else if (error) {
    body = (
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", p: 1.5 }}>
        <Na reason={error} />
        <Typography variant="body2" sx={{ color: "text.secondary" }}>
          Pulse unavailable: {error}
        </Typography>
      </Stack>
    );
  } else {
    body = [0, 1].map((i) => <Skeleton key={i} variant="rectangular" height={52} sx={{ m: 1, borderRadius: 1 }} />);
  }

  return (
    <Card aria-label="BTC and ETH pulse" sx={{ minWidth: 0 }}>
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", px: 1.5, py: 0.5, borderBottom: 1, borderColor: "divider" }}>
        <Typography variant="overline" sx={{ color: "text.secondary", flex: 1 }}>
          Market pulse
        </Typography>
        {data ? (
          <Typography variant="caption" sx={{ color: "text.secondary" }}>
            {error ? "Stale · " : ""}
            {fmtWhen(data.generated_at) ?? ""}
          </Typography>
        ) : null}
        {data ? (
          <Tooltip title={data.rule}>
            <InfoOutlined aria-label="How trend and bias are decided" tabIndex={0} sx={{ fontSize: 16, color: "text.secondary" }} />
          </Tooltip>
        ) : null}
      </Stack>
      <Box sx={{ overflowX: "auto" }}>
        <Box sx={{ minWidth: data ? 760 : 0 }}>{body}</Box>
      </Box>
    </Card>
  );
}
