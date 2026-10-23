import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import Refresh from "@mui/icons-material/Refresh";
import ShowChart from "@mui/icons-material/ShowChart";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { api, type SignalDashboard } from "../api";
import { ActionButton, EmptyState, KpiStrip, Na, PageHeader, V, type KpiTile } from "../components/ui";
import { fmtSigned, isNum } from "../lib/format";

function ChartCard({ title, note, children }: Readonly<{ title: string; note?: string; children: React.ReactNode }>) {
  return (
    <Card sx={{ p: 2, minWidth: 0, height: "100%", display: "flex", flexDirection: "column" }}>
      <Typography variant="h3" component="h3" sx={{ mb: 0.5 }}>
        {title}
      </Typography>
      {note ? (
        <Typography variant="caption" sx={{ color: "text.secondary", mb: 1.5, display: "block" }}>
          {note}
        </Typography>
      ) : (
        <Box sx={{ mb: 1.5 }} />
      )}
      <Box sx={{ flex: 1, minHeight: 240, width: "100%" }}>{children}</Box>
    </Card>
  );
}

function pct(v: number | null | undefined): string {
  if (!isNum(v)) return "—";
  return `${String(Math.round(v * 100))}%`;
}

export default function Dashboard({ active, version }: Readonly<{ active: boolean; version: number }>) {
  const theme = useTheme();
  const [data, setData] = useState<SignalDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const primary = theme.palette.primary.main;
  const textSec = theme.palette.text.secondary;
  const grid = theme.palette.divider;
  const win = theme.palette.success.main;
  const loss = theme.palette.error.main;
  const warn = theme.palette.warning.main;
  const paper2 = theme.palette.surface.paper2;

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.signalDashboard();
      setData(res);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh().catch(() => undefined);
  }, [active, version, refresh]);

  const equityFlat = useMemo(() => {
    return (data?.equity_curve ?? []).map((p) => {
      const row: Record<string, string | number> = {
        date: p.date,
        cumulative_r: p.cumulative_r,
      };
      for (const [k, v] of Object.entries(p.cumulative_r_by_strategy ?? {})) {
        row[`s_${k}`] = v;
      }
      return row;
    });
  }, [data]);

  const kpis: KpiTile[] = useMemo(() => {
    if (!data) {
      return [
        { label: "Hit rate", value: <Na reason="Loading" />, note: "Loading" },
        { label: "Average R", value: <Na reason="Loading" />, note: "Loading" },
        { label: "Open", value: <Na reason="Loading" />, note: "Loading" },
        { label: "Decided", value: <Na reason="Loading" />, note: "Loading" },
        { label: "Best strategy", value: <Na reason="Loading" />, note: "Loading" },
        { label: "Weakest", value: <Na reason="Loading" />, note: "Loading" },
      ];
    }
    const o = data.overall;
    const minN = data.min_reliable;
    return [
      {
        label: "Hit rate",
        value: isNum(o.hit_rate) ? pct(o.hit_rate) : <Na reason="No decided signals" />,
        note: "Wins among decided",
      },
      {
        label: "Average R",
        value: <V value={fmtSigned(o.avg_r, 2)} reason="No closed signals" />,
        note: "Closed including expired",
      },
      { label: "Open", value: String(o.open ?? 0), note: `${String(o.n ?? 0)} total` },
      {
        label: "Decided",
        value: String(o.decided ?? 0),
        note: `${String(o.wins ?? 0)}W / ${String(o.losses ?? 0)}L`,
      },
      {
        label: "Best strategy",
        value: data.best_label ? data.best_label : <Na reason={`Need ${String(minN)}+ decided`} />,
        note: data.best ? "By hit rate (reliable)" : "Weak sample",
      },
      {
        label: "Weakest",
        value: data.worst_label ? data.worst_label : <Na reason={`Need ${String(minN)}+ decided`} />,
        note: data.worst ? "By hit rate (reliable)" : "Weak sample",
      },
    ];
  }, [data]);

  const withSignals = useMemo(
    () => (data?.by_strategy ?? []).filter((b) => (b.n ?? 0) > 0),
    [data],
  );

  const hitBars = useMemo(
    () =>
      withSignals.map((b) => ({
        label: b.label,
        hit: isNum(b.hit_rate) ? Math.round(b.hit_rate * 1000) / 10 : 0,
        reliable: b.reliable,
      })),
    [withSignals],
  );

  const rBars = useMemo(
    () =>
      withSignals.map((b) => ({
        label: b.label,
        avg_r: b.avg_r ?? 0,
        reliable: b.reliable,
      })),
    [withSignals],
  );

  const scatter = useMemo(
    () =>
      withSignals
        .filter((b) => isNum(b.hit_rate))
        .map((b) => ({
          label: b.label,
          n: b.decided ?? 0,
          hit: Math.round((b.hit_rate ?? 0) * 1000) / 10,
          z: Math.max(b.decided ?? 1, 1),
        })),
    [withSignals],
  );

  const equityKeys = useMemo(() => {
    const keys = new Set<string>();
    for (const p of data?.equity_curve ?? []) {
      for (const k of Object.keys(p.cumulative_r_by_strategy ?? {})) keys.add(k);
    }
    return [...keys].slice(0, 6);
  }, [data]);

  const strategyLabel = useMemo(() => {
    const m = new Map((data?.by_strategy ?? []).map((b) => [b.id, b.label]));
    return (id: string) => m.get(id) ?? id;
  }, [data]);

  let body: React.ReactNode;
  if (error) {
    body = (
      <Typography color="warning.main" sx={{ p: 2 }}>
        Dashboard unavailable: {error}
      </Typography>
    );
  } else if (loading && !data) {
    body = (
      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" } }}>
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} variant="rounded" height={280} />
        ))}
      </Box>
    );
  } else if (!data || (data.overall.n ?? 0) === 0) {
    body = (
      <EmptyState
        text="No archived signals yet. Run a full analysis with Buy or Sell bias to start the track record."
        icon={<ShowChart />}
      />
    );
  } else {
    body = (
      <Box
        sx={{
          display: "grid",
          gap: 2,
          gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "repeat(2, minmax(0, 1fr))" },
        }}
      >
        <ChartCard title="Hit rate by strategy" note="Percent wins among decided (win or loss). Grey bars have a small sample.">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={hitBars} layout="vertical" margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
              <CartesianGrid stroke={grid} strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} tick={{ fill: textSec, fontSize: 11 }} unit="%" />
              <YAxis type="category" dataKey="label" width={110} tick={{ fill: textSec, fontSize: 11 }} />
              <Tooltip formatter={(v) => [`${String(v)}%`, "Hit rate"]} />
              <Bar dataKey="hit" name="Hit rate" radius={[0, 4, 4, 0]}>
                {hitBars.map((row) => (
                  <Cell key={row.label} fill={row.reliable ? primary : theme.palette.grey[400]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Average R by strategy" note="Mean R on closed signals (wins, losses, expired).">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rBars} layout="vertical" margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
              <CartesianGrid stroke={grid} strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" tick={{ fill: textSec, fontSize: 11 }} />
              <YAxis type="category" dataKey="label" width={110} tick={{ fill: textSec, fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="avg_r" name="Avg R" radius={[0, 4, 4, 0]}>
                {rBars.map((row) => (
                  <Cell key={row.label} fill={(row.avg_r ?? 0) >= 0 ? win : loss} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Cumulative R over time" note="Running sum of R as signals close. Thin lines are per strategy.">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={equityFlat} margin={{ left: 0, right: 16, top: 8, bottom: 8 }}>
              <CartesianGrid stroke={grid} strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fill: textSec, fontSize: 10 }} minTickGap={24} />
              <YAxis tick={{ fill: textSec, fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="cumulative_r" name="Overall" stroke={primary} strokeWidth={2} dot={false} />
              {equityKeys.map((id, i) => (
                <Line
                  key={id}
                  type="monotone"
                  dataKey={`s_${id}`}
                  name={strategyLabel(id)}
                  stroke={i % 2 === 0 ? warn : theme.palette.info.main}
                  strokeWidth={1}
                  strokeOpacity={0.85}
                  dot={false}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Outcomes by strategy" note="Win (up) · Loss (down) · Expired">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.outcomes_by_strategy} margin={{ left: 0, right: 16, top: 8, bottom: 8 }}>
              <CartesianGrid stroke={grid} strokeDasharray="3 3" />
              <XAxis dataKey="label" tick={{ fill: textSec, fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={56} />
              <YAxis allowDecimals={false} tick={{ fill: textSec, fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="wins" name="Win" stackId="a" fill={win} />
              <Bar dataKey="losses" name="Loss" stackId="a" fill={loss} />
              <Bar dataKey="expired" name="Expired" stackId="a" fill={theme.palette.grey[500]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Signals per day" note="Last 30 days by created date.">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data.volume_by_day} margin={{ left: 0, right: 16, top: 8, bottom: 8 }}>
              <CartesianGrid stroke={grid} strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fill: textSec, fontSize: 10 }} minTickGap={28} />
              <YAxis allowDecimals={false} tick={{ fill: textSec, fontSize: 11 }} />
              <Tooltip />
              <Area type="monotone" dataKey="count" name="Signals" stroke={primary} fill={paper2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Sample size vs hit rate" note="Bubble size is decided trades. Small samples sit left.">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
              <CartesianGrid stroke={grid} strokeDasharray="3 3" />
              <XAxis type="number" dataKey="n" name="Decided" tick={{ fill: textSec, fontSize: 11 }} allowDecimals={false} />
              <YAxis type="number" dataKey="hit" name="Hit %" domain={[0, 100]} tick={{ fill: textSec, fontSize: 11 }} unit="%" />
              <ZAxis type="number" dataKey="z" range={[40, 280]} />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(v, name) => [v, name === "hit" ? "Hit %" : name]} labelFormatter={(_, p) => (p?.[0]?.payload as { label?: string } | undefined)?.label ?? ""} />
              <Scatter name="Strategies" data={scatter} fill={primary} />
            </ScatterChart>
          </ResponsiveContainer>
        </ChartCard>
      </Box>
    );
  }

  return (
    <Stack spacing={2}>
      <PageHeader
        title="Dashboard"
        subtitle="Which strategies are working from your archived signals."
        actions={
          <ActionButton icon={<Refresh />} onClick={() => void refresh()} busy={loading} busyLabel="Refreshing…">
            Refresh
          </ActionButton>
        }
      />
      <KpiStrip tiles={kpis} />
      {body}
    </Stack>
  );
}
