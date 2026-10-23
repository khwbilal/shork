import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import DoneAll from "@mui/icons-material/DoneAll";
import Refresh from "@mui/icons-material/Refresh";
import TrackChanges from "@mui/icons-material/TrackChanges";
import Update from "@mui/icons-material/Update";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, type Signal, type SignalReview, type Stats, type StrategyInfo } from "../api";
import { useFeedback } from "../components/feedback";
import { ActionButton, BiasPill, DataTable, EmptyState, KpiStrip, Na, Num, PageHeader, StatusPill, V } from "../components/ui";
import { fmtPx, fmtSigned, fmtWhen, humanize, isNum } from "../lib/format";

const TF_TABS = [
  { id: "all", label: "All" },
  { id: "15m", label: "15m" },
  { id: "1h", label: "1h" },
  { id: "4h", label: "4h" },
  { id: "1d", label: "1D" },
] as const;

type TfTab = (typeof TF_TABS)[number]["id"];

const STATUS_OPTIONS = [
  { id: "all", label: "All statuses" },
  { id: "open", label: "Open" },
  { id: "win", label: "Win" },
  { id: "loss", label: "Loss" },
  { id: "expired", label: "Expired" },
] as const;

type StatusFilter = (typeof STATUS_OPTIONS)[number]["id"];

const STANCE_META: Record<string, { glyph: string; label: string }> = {
  hold: { glyph: "○", label: "Hold" },
  caution: { glyph: "△", label: "Caution" },
  exit_early: { glyph: "▸", label: "Exit early" },
};

function normTf(tf: string | null | undefined): string {
  return (tf || "").trim().toLowerCase();
}

function normStrategy(id: string | null | undefined): string {
  const s = (id || "").trim().toLowerCase();
  return s || "desk";
}

function strategyLabel(id: string | null | undefined, catalog: StrategyInfo[]): string {
  const sid = normStrategy(id);
  return catalog.find((s) => s.id === sid)?.label ?? (sid === "desk" ? "Desk" : humanize(sid));
}

function matchesTf(signalTf: string | null | undefined, tab: TfTab): boolean {
  if (tab === "all") return true;
  return normTf(signalTf) === tab;
}

function latestReview(s: Signal): SignalReview | null {
  const list = s.live_review_json;
  if (!Array.isArray(list) || !list.length) return null;
  return list[list.length - 1] ?? null;
}

function StanceChip({ stance }: Readonly<{ stance: string | null | undefined }>) {
  if (!stance) return <Na reason="No live review yet" />;
  const meta = STANCE_META[stance] ?? { glyph: "●", label: humanize(stance) };
  return <Chip size="small" label={`${meta.glyph} ${meta.label}`} variant="outlined" />;
}

function filterStats(rows: Signal[]): Stats {
  const closed = rows.filter((r) => r.status === "win" || r.status === "loss" || r.status === "expired");
  const wins = closed.filter((r) => r.status === "win");
  const losses = closed.filter((r) => r.status === "loss");
  const expired = closed.filter((r) => r.status === "expired");
  const open = rows.filter((r) => r.status === "open").length;
  const decided = [...wins, ...losses];
  const hit = decided.length ? wins.length / decided.length : null;
  const rs = closed.map((r) => r.r_multiple).filter((v): v is number => typeof v === "number" && !Number.isNaN(v));
  const avg_r = rs.length ? Math.round((rs.reduce((a, b) => a + b, 0) / rs.length) * 100) / 100 : null;
  return {
    total: rows.length,
    open,
    wins: wins.length,
    losses: losses.length,
    expired: expired.length,
    hit_rate: hit,
    avg_r,
  };
}

export default function Signals({
  active,
  version,
  onStats,
  onOpenSignal,
}: Readonly<{
  active: boolean;
  version: number;
  onStats: (s: Stats) => void;
  onOpenSignal: (id: string) => void;
}>) {
  const { toast } = useFeedback();
  const [signals, setSignals] = useState<Signal[] | null>(null);
  const [stats, setStats] = useState<Stats>({});
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [checking, setChecking] = useState<string | null>(null);
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [tfTab, setTfTab] = useState<TfTab>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [strategyFilter, setStrategyFilter] = useState<string>("all");
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);

  const refresh = useCallback(async () => {
    try {
      const res = await api.signals();
      setSignals(res.signals);
      setStats(res.stats);
      onStats(res.stats);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }, [onStats]);

  useEffect(() => {
    api
      .strategies()
      .then((res) => setStrategies(res.strategies))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    refresh().catch(() => undefined);
  }, [active, version, refresh]);

  const filtered = useMemo(() => {
    if (!signals) return null;
    return signals.filter((s) => {
      if (!matchesTf(s.timeframe, tfTab)) return false;
      if (statusFilter !== "all" && (s.status || "").toLowerCase() !== statusFilter) return false;
      if (strategyFilter !== "all" && normStrategy(s.strategy_id) !== strategyFilter) return false;
      return true;
    });
  }, [signals, tfTab, statusFilter, strategyFilter]);

  const viewStats = useMemo(() => {
    if (!filtered) return stats;
    if (tfTab === "all" && statusFilter === "all" && strategyFilter === "all") return stats;
    return filterStats(filtered);
  }, [filtered, stats, tfTab, statusFilter, strategyFilter]);

  const tabCounts = useMemo(() => {
    const counts: Record<TfTab, number> = { all: 0, "15m": 0, "1h": 0, "4h": 0, "1d": 0 };
    if (!signals) return counts;
    const statusOk = (s: Signal) => statusFilter === "all" || (s.status || "").toLowerCase() === statusFilter;
    const strategyOk = (s: Signal) =>
      strategyFilter === "all" || normStrategy(s.strategy_id) === strategyFilter;
    for (const s of signals) {
      if (!statusOk(s) || !strategyOk(s)) continue;
      counts.all += 1;
      const tf = normTf(s.timeframe);
      if (tf === "15m" || tf === "1h" || tf === "4h" || tf === "1d") counts[tf] += 1;
    }
    return counts;
  }, [signals, statusFilter, strategyFilter]);

  async function verifyAll() {
    setVerifying(true);
    try {
      const res = await api.verifySignals();
      toast(`Checked ${String(res.checked)} signals, ${String(res.updated)} updated.`);
    } catch (err) {
      toast(`Verify failed: ${(err as Error).message}`);
    } finally {
      setVerifying(false);
    }
    await refresh();
  }

  async function reviewAll() {
    setReviewing(true);
    try {
      const res = await api.reviewOpenSignals();
      toast(`Live review on ${String(res.checked)} open, ${String(res.updated)} updated.`);
    } catch (err) {
      toast(`Live review failed: ${(err as Error).message}`);
    } finally {
      setReviewing(false);
    }
    await refresh();
  }

  async function check(id: string) {
    setChecking(id);
    try {
      const res = await api.verifySignal(id);
      toast(`${res.signal.symbol}: ${res.signal.status} (${res.signal.outcome ?? "checked"})`);
    } catch (err) {
      toast(`Check failed: ${(err as Error).message}`);
    } finally {
      setChecking(null);
    }
    await refresh();
  }

  async function reviewOne(id: string) {
    setReviewingId(id);
    try {
      const res = await api.reviewSignal(id);
      const stance = res.review?.stance ? STANCE_META[res.review.stance]?.label ?? res.review.stance : "no price";
      toast(`${res.signal.symbol}: ${stance}${res.review?.unrealized_r != null ? ` (${fmtSigned(res.review.unrealized_r, 2)}R)` : ""}`);
      onOpenSignal(res.signal.id);
    } catch (err) {
      toast(`Review failed: ${(err as Error).message}`);
    } finally {
      setReviewingId(null);
    }
    await refresh();
  }

  let table: React.ReactNode;
  if (error)
    table = (
      <Alert severity="warning" sx={{ m: 2 }}>
        Signals unavailable: {error}
      </Alert>
    );
  else if (!filtered)
    table = (
      <Box sx={{ p: 2 }}>
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} height={40} />
        ))}
      </Box>
    );
  else if (!signals?.length)
    table = <EmptyState text="No archived signals yet. A full analysis with a Buy or Sell bias saves one here." icon={<TrackChanges />} />;
  else if (!filtered.length) {
    const tfLabel = TF_TABS.find((t) => t.id === tfTab)?.label ?? tfTab;
    const statusLabel = statusFilter === "all" ? "" : ` / ${statusFilter}`;
    const stratLabel =
      strategyFilter === "all" ? "" : ` / ${strategyLabel(strategyFilter, strategies)}`;
    table = (
      <EmptyState text={`No signals match ${tfLabel}${statusLabel}${stratLabel}.`} icon={<TrackChanges />} />
    );
  } else
    table = (
      <DataTable minWidth={1280}>
        <TableHead>
          <TableRow>
            <TableCell>Created</TableCell>
            <TableCell>Pair</TableCell>
            <TableCell>Strategy</TableCell>
            <TableCell>Bias</TableCell>
            <TableCell align="right">Entry</TableCell>
            <TableCell align="right">Stop</TableCell>
            <TableCell align="right">Target</TableCell>
            <TableCell align="right">Now</TableCell>
            <TableCell>Stance</TableCell>
            <TableCell>Status</TableCell>
            <TableCell align="right">R</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {filtered.map((s) => {
            const latest = latestReview(s);
            const isOpen = (s.status || "").toLowerCase() === "open";
            return (
              <TableRow
                key={s.id}
                hover
                sx={{ cursor: "pointer" }}
                onClick={() => onOpenSignal(s.id)}
              >
                <TableCell>
                  <V value={fmtWhen(s.created_at)} mono={false} />
                </TableCell>
                <TableCell>
                  <Num sx={{ fontWeight: 700 }}>{s.symbol}</Num>{" "}
                  <Typography component="span" variant="caption" sx={{ color: "text.secondary" }}>
                    {s.timeframe}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip size="small" label={strategyLabel(s.strategy_id, strategies)} variant="outlined" />
                </TableCell>
                <TableCell>
                  <BiasPill bias={s.bias} />
                </TableCell>
                <TableCell align="right">
                  <V value={fmtPx(s.entry)} />
                </TableCell>
                <TableCell align="right">
                  <V value={fmtPx(s.stop_loss)} />
                </TableCell>
                <TableCell align="right">
                  <V value={fmtPx(s.take_profit)} />
                </TableCell>
                <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                  {latest?.price != null ? (
                    <Stack spacing={0} sx={{ alignItems: "flex-end" }}>
                      <V value={fmtPx(latest.price)} />
                      <Typography variant="caption" sx={{ color: "text.secondary" }}>
                        {isNum(latest.unrealized_r) ? `${fmtSigned(latest.unrealized_r, 2)}R` : "—"}
                      </Typography>
                    </Stack>
                  ) : (
                    <Na reason="Run live review" />
                  )}
                </TableCell>
                <TableCell onClick={(e) => e.stopPropagation()}>
                  <StanceChip stance={latest?.stance} />
                </TableCell>
                <TableCell>
                  <StatusPill status={s.status} title={s.outcome ?? undefined} />
                </TableCell>
                <TableCell align="right">
                  <V value={fmtSigned(s.r_multiple, 2)} reason={s.status === "open" ? "Still open" : "Not decided"} />
                </TableCell>
                <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                  <Stack direction="row" spacing={0.75} sx={{ justifyContent: "flex-end" }}>
                    {isOpen ? (
                      <Button
                        size="small"
                        variant="outlined"
                        color="inherit"
                        sx={{ borderColor: "divider" }}
                        disabled={reviewingId === s.id}
                        startIcon={reviewingId === s.id ? <CircularProgress size={12} color="inherit" /> : <Update sx={{ fontSize: 14 }} />}
                        onClick={() => void reviewOne(s.id)}
                      >
                        Review
                      </Button>
                    ) : null}
                    <Button
                      size="small"
                      variant="outlined"
                      color="inherit"
                      sx={{ borderColor: "divider" }}
                      disabled={checking === s.id}
                      startIcon={checking === s.id ? <CircularProgress size={12} color="inherit" /> : undefined}
                      onClick={() => void check(s.id)}
                    >
                      Check
                    </Button>
                  </Stack>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </DataTable>
    );

  return (
    <Stack spacing={2}>
      <PageHeader
        title="Signals"
        subtitle="Every Buy or Sell from a full analysis. Click a row for pack details and live review history. Original plan stays frozen."
        actions={
          <>
            <ActionButton icon={<Refresh />} onClick={() => void refresh()}>
              Refresh
            </ActionButton>
            <ActionButton icon={<Update />} busy={reviewing} busyLabel="Reviewing…" onClick={() => void reviewAll()}>
              Live review open
            </ActionButton>
            <ActionButton icon={<DoneAll />} primary busy={verifying} busyLabel="Verifying…" onClick={() => void verifyAll()}>
              Verify open signals
            </ActionButton>
          </>
        }
      />
      <KpiStrip
        tiles={[
          {
            label: "Hit rate",
            value: isNum(viewStats.hit_rate) ? `${String(Math.round(viewStats.hit_rate * 100))}%` : <Na reason="No decided signals yet" />,
            note: "Target before stop",
          },
          {
            label: "Wins / losses",
            value: `${String(viewStats.wins ?? 0)} / ${String(viewStats.losses ?? 0)}`,
            note: `${String(viewStats.expired ?? 0)} expired`,
          },
          { label: "Open", value: String(viewStats.open ?? 0), note: "Neither level hit yet" },
          {
            label: "Average R",
            value: <V value={fmtSigned(viewStats.avg_r, 2)} reason="No closed signals" />,
            note: `${String(viewStats.total ?? 0)} in view`,
          },
        ]}
      />
      <Card>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={1.5}
          sx={{
            px: 2,
            pt: 1.5,
            borderBottom: 1,
            borderColor: "divider",
            alignItems: { xs: "stretch", sm: "center" },
            justifyContent: "space-between",
          }}
        >
          <Tabs
            value={tfTab}
            onChange={(_, v: TfTab) => setTfTab(v)}
            variant="scrollable"
            scrollButtons="auto"
            aria-label="Filter signals by timeframe"
            sx={{ minHeight: 44, "& .MuiTab-root": { minHeight: 44, textTransform: "none" } }}
          >
            {TF_TABS.map((t) => (
              <Tab
                key={t.id}
                value={t.id}
                label={
                  <Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }}>
                    <span>{t.label}</span>
                    <Chip size="small" label={tabCounts[t.id]} sx={{ height: 20, "& .MuiChip-label": { px: 0.75 } }} />
                  </Stack>
                }
              />
            ))}
          </Tabs>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ mb: { xs: 1.5, sm: 1.5 }, mr: { sm: 0.5 } }}>
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel id="signal-strategy-filter-label">Strategy</InputLabel>
              <Select
                labelId="signal-strategy-filter-label"
                label="Strategy"
                value={strategyFilter}
                onChange={(e) => setStrategyFilter(String(e.target.value))}
              >
                <MenuItem value="all">All strategies</MenuItem>
                {(strategies.length
                  ? strategies
                  : [{ id: "desk", label: "Desk (default)", summary: "" }]
                ).map((s) => (
                  <MenuItem key={s.id} value={s.id}>
                    {s.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="signal-status-filter-label">Status</InputLabel>
              <Select
                labelId="signal-status-filter-label"
                label="Status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
              >
                {STATUS_OPTIONS.map((o) => (
                  <MenuItem key={o.id} value={o.id}>
                    {o.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
        </Stack>
        {table}
      </Card>
    </Stack>
  );
}
