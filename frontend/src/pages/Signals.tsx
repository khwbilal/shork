import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import DoneAll from "@mui/icons-material/DoneAll";
import Refresh from "@mui/icons-material/Refresh";
import TrackChanges from "@mui/icons-material/TrackChanges";
import { useCallback, useEffect, useState } from "react";
import { api, type Signal, type Stats } from "../api";
import { useFeedback } from "../components/feedback";
import { ActionButton, BiasPill, DataTable, EmptyState, KpiStrip, Na, Num, PageHeader, StatusPill, V } from "../components/ui";
import { fmtPx, fmtSigned, fmtWhen, humanize, isNum } from "../lib/format";

export default function Signals({
  active,
  version,
  onStats,
}: Readonly<{ active: boolean; version: number; onStats: (s: Stats) => void }>) {
  const { toast } = useFeedback();
  const [signals, setSignals] = useState<Signal[] | null>(null);
  const [stats, setStats] = useState<Stats>({});
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [checking, setChecking] = useState<string | null>(null);

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
    // Load on mount (rail counts), when the page is opened, and after outside changes.
    refresh().catch(() => undefined);
  }, [active, version, refresh]);

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

  let table: React.ReactNode;
  if (error)
    table = (
      <Alert severity="warning" sx={{ m: 2 }}>
        Signals unavailable: {error}
      </Alert>
    );
  else if (!signals)
    table = (
      <Box sx={{ p: 2 }}>
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} height={40} />
        ))}
      </Box>
    );
  else if (!signals.length)
    table = <EmptyState text="No archived signals yet. A full analysis with a Buy or Sell bias saves one here." icon={<TrackChanges />} />;
  else
    table = (
      <DataTable minWidth={1040}>
        <TableHead>
          <TableRow>
            <TableCell>Created</TableCell>
            <TableCell>Pair</TableCell>
            <TableCell>Bias</TableCell>
            <TableCell>Setup</TableCell>
            <TableCell align="right">Entry</TableCell>
            <TableCell align="right">Stop</TableCell>
            <TableCell align="right">Target</TableCell>
            <TableCell align="right">Score</TableCell>
            <TableCell>Status</TableCell>
            <TableCell align="right">R</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {signals.map((s) => (
            <TableRow key={s.id} hover>
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
                <BiasPill bias={s.bias} />
              </TableCell>
              <TableCell>{s.setup ? <Chip size="small" label={humanize(s.setup)} /> : <Na />}</TableCell>
              <TableCell align="right">
                <V value={fmtPx(s.entry)} />
              </TableCell>
              <TableCell align="right">
                <V value={fmtPx(s.stop_loss)} />
              </TableCell>
              <TableCell align="right">
                <V value={fmtPx(s.take_profit)} />
              </TableCell>
              <TableCell align="right">
                <V value={fmtSigned(s.confluence)} />
              </TableCell>
              <TableCell>
                <StatusPill status={s.status} title={s.outcome ?? undefined} />
              </TableCell>
              <TableCell align="right">
                <V value={fmtSigned(s.r_multiple, 2)} reason={s.status === "open" ? "Still open" : "Not decided"} />
              </TableCell>
              <TableCell align="right">
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
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </DataTable>
    );

  return (
    <Stack spacing={2}>
      <PageHeader
        title="Signals"
        subtitle="Every Buy or Sell from a full analysis, checked against later candles."
        actions={
          <>
            <ActionButton icon={<Refresh />} onClick={() => void refresh()}>
              Refresh
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
            value: isNum(stats.hit_rate) ? `${String(Math.round(stats.hit_rate * 100))}%` : <Na reason="No decided signals yet" />,
            note: "Target before stop",
          },
          { label: "Wins / losses", value: `${String(stats.wins ?? 0)} / ${String(stats.losses ?? 0)}`, note: `${String(stats.expired ?? 0)} expired` },
          { label: "Open", value: String(stats.open ?? 0), note: "Neither level hit yet" },
          {
            label: "Average R",
            value: <V value={fmtSigned(stats.avg_r, 2)} reason="No closed signals" />,
            note: `${String(stats.total ?? 0)} archived`,
          },
        ]}
      />
      <Card>{table}</Card>
    </Stack>
  );
}
