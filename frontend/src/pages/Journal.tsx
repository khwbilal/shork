import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Tooltip from "@mui/material/Tooltip";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Close from "@mui/icons-material/Close";
import DeleteOutlined from "@mui/icons-material/DeleteOutlined";
import MenuBookOutlined from "@mui/icons-material/MenuBookOutlined";
import Refresh from "@mui/icons-material/Refresh";
import { useCallback, useEffect, useState } from "react";
import { api, type JournalEntry, type Stats } from "../api";
import { useFeedback } from "../components/feedback";
import { ActionButton, BiasPill, DataTable, EmptyState, KpiStrip, Na, Num, PageHeader, StatusPill, V } from "../components/ui";
import { fmtPx, fmtSigned, fmtWhen, humanize, isNum } from "../lib/format";

const CLOSE_LABEL: Record<string, string> = { win: "win", loss: "loss", be: "breakeven" };

function RowButton({ label, onClick }: Readonly<{ label: string; onClick: () => void }>) {
  return (
    <Button size="small" variant="outlined" color="inherit" sx={{ borderColor: "divider", minWidth: 0, px: 1.25 }} onClick={onClick}>
      {label}
    </Button>
  );
}

export default function Journal({
  active,
  version,
  onStats,
}: Readonly<{ active: boolean; version: number; onStats: (s: Stats) => void }>) {
  const { toast, ask } = useFeedback();
  const [entries, setEntries] = useState<JournalEntry[] | null>(null);
  const [stats, setStats] = useState<Stats>({});
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await api.journal();
      setEntries(res.entries);
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

  async function close(id: string, status: string) {
    let exitPrice: number | null = null;
    if (status in CLOSE_LABEL) {
      const raw = await ask({
        title: `Close as ${CLOSE_LABEL[status]}`,
        text: "Add the exit price to compute the R multiple, or leave it blank.",
        label: "Exit price (optional)",
        okLabel: "Close trade",
        input: true,
      });
      if (raw === null) return;
      if (typeof raw === "string" && raw) {
        exitPrice = Number(raw.replace(/,/g, ""));
        if (Number.isNaN(exitPrice)) {
          toast("Exit price must be a number.");
          return;
        }
      }
    }
    try {
      await api.closeJournal(id, status, exitPrice);
      toast(`Trade closed as ${status}.`);
    } catch (err) {
      toast(`Could not close trade: ${(err as Error).message}`);
    }
    await refresh();
  }

  async function remove(id: string) {
    const ok = await ask({
      title: "Delete this entry?",
      text: "It is removed from the journal and its stats.",
      okLabel: "Delete",
      danger: true,
    });
    if (!ok) return;
    try {
      await api.deleteJournal(id);
      toast("Entry deleted.");
    } catch (err) {
      toast(`Could not delete: ${(err as Error).message}`);
    }
    await refresh();
  }

  let table: React.ReactNode;
  if (error)
    table = (
      <Alert severity="warning" sx={{ m: 2 }}>
        Journal unavailable: {error}
      </Alert>
    );
  else if (!entries)
    table = (
      <Box sx={{ p: 2 }}>
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} height={40} />
        ))}
      </Box>
    );
  else if (!entries.length)
    table = <EmptyState text="Nothing logged yet. Run a full analysis on the desk, then use Log to journal." icon={<MenuBookOutlined />} />;
  else
    table = (
      <DataTable minWidth={980}>
        <TableHead>
          <TableRow>
            <TableCell>Logged</TableCell>
            <TableCell>Pair</TableCell>
            <TableCell>Side</TableCell>
            <TableCell>Setup</TableCell>
            <TableCell align="right">Entry</TableCell>
            <TableCell align="right">Stop</TableCell>
            <TableCell align="right">Target</TableCell>
            <TableCell>Status</TableCell>
            <TableCell align="right">R</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {entries.map((e) => {
            const open = e.status === "open";
            return (
              <TableRow key={e.id} hover>
                <TableCell>
                  <V value={fmtWhen(e.created_at)} mono={false} />
                </TableCell>
                <TableCell>
                  <Num sx={{ fontWeight: 700 }}>{e.symbol}</Num>{" "}
                  <Typography component="span" variant="caption" sx={{ color: "text.secondary" }}>
                    {e.timeframe}
                  </Typography>
                </TableCell>
                <TableCell>
                  <BiasPill bias={e.side} />
                </TableCell>
                <TableCell>{e.setup ? <Chip size="small" label={humanize(e.setup)} /> : <Na />}</TableCell>
                <TableCell align="right">
                  <V value={fmtPx(e.entry)} />
                </TableCell>
                <TableCell align="right">
                  <V value={fmtPx(e.stop_loss)} />
                </TableCell>
                <TableCell align="right">
                  <V value={fmtPx(e.take_profit)} />
                </TableCell>
                <TableCell>
                  <StatusPill status={e.status} />
                </TableCell>
                <TableCell align="right">
                  <V value={fmtSigned(e.r_multiple, 2)} reason={open ? "Still open" : "No exit price"} />
                </TableCell>
                <TableCell align="right">
                  <Stack direction="row" spacing={0.5} sx={{ justifyContent: "flex-end" }}>
                    {open ? (
                      <>
                        <RowButton label="Win" onClick={() => void close(e.id, "win")} />
                        <RowButton label="Loss" onClick={() => void close(e.id, "loss")} />
                        <RowButton label="BE" onClick={() => void close(e.id, "be")} />
                        <Tooltip title="Skipped">
                          <IconButton size="small" aria-label="Mark as skipped" onClick={() => void close(e.id, "skipped")}>
                            <Close fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </>
                    ) : (
                      <Tooltip title="Delete">
                        <IconButton size="small" aria-label="Delete entry" onClick={() => void remove(e.id)}>
                          <DeleteOutlined fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
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
        title="Journal"
        subtitle={
          entries?.length
            ? `${String(stats.total ?? entries.length)} trades logged, ${String(stats.open ?? 0)} still open.`
            : "Trades you logged from the desk."
        }
        actions={
          <ActionButton icon={<Refresh />} onClick={() => void refresh()}>
            Refresh
          </ActionButton>
        }
      />
      <KpiStrip
        tiles={[
          {
            label: "Hit rate",
            value: isNum(stats.hit_rate) ? `${String(Math.round(stats.hit_rate * 100))}%` : <Na reason="No closed trades yet" />,
            note: `${String(stats.closed ?? 0)} closed trades`,
          },
          { label: "Wins / losses", value: `${String(stats.wins ?? 0)} / ${String(stats.losses ?? 0)}`, note: `${String(stats.breakeven ?? 0)} breakeven` },
          { label: "Open", value: String(stats.open ?? 0), note: "Awaiting an outcome" },
          {
            label: "Average R",
            value: <V value={fmtSigned(stats.avg_r, 2)} reason="Needs exit prices" />,
            note: "Per closed trade",
          },
        ]}
      />
      <Card>{table}</Card>
    </Stack>
  );
}
