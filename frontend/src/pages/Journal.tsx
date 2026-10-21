import { useCallback, useEffect, useState } from "react";
import { api, type JournalEntry, type Stats } from "../api";
import { useFeedback } from "../components/feedback";
import Icon from "../components/Icon";
import { BiasPill, Button, EmptyState, KpiStrip, Na, PageHeader, StatusPill, V } from "../components/ui";
import { fmtPx, fmtSigned, fmtWhen, humanize, isNum } from "../lib/format";

const CLOSE_LABEL: Record<string, string> = { win: "win", loss: "loss", be: "breakeven" };

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
  if (error) table = <EmptyState text={`Journal unavailable: ${error}`} />;
  else if (!entries) table = <EmptyState text="Loading…" icon="clock" />;
  else if (!entries.length)
    table = <EmptyState text="Nothing logged yet. Run a full analysis on the desk, then use Log to journal." icon="book" />;
  else
    table = (
      <table className="data">
        <thead>
          <tr>
            <th>Logged</th>
            <th>Pair</th>
            <th>Side</th>
            <th>Setup</th>
            <th className="num">Entry</th>
            <th className="num">Stop</th>
            <th className="num">Target</th>
            <th>Status</th>
            <th className="num">R</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => {
            const open = e.status === "open";
            return (
              <tr key={e.id}>
                <td>
                  <V value={fmtWhen(e.created_at)} />
                </td>
                <td className="sym">
                  {e.symbol} <span className="card-sub">{e.timeframe}</span>
                </td>
                <td>
                  <BiasPill bias={e.side} />
                </td>
                <td>{e.setup ? <span className="chip">{humanize(e.setup)}</span> : <Na />}</td>
                <td className="num"><V value={fmtPx(e.entry)} /></td>
                <td className="num"><V value={fmtPx(e.stop_loss)} /></td>
                <td className="num"><V value={fmtPx(e.take_profit)} /></td>
                <td>
                  <StatusPill status={e.status} />
                </td>
                <td className="num">
                  <V value={fmtSigned(e.r_multiple, 2)} reason={open ? "Still open" : "No exit price"} />
                </td>
                <td>
                  <div className="row-actions">
                    {open ? (
                      <>
                        <Button compact onClick={() => close(e.id, "win")}>Win</Button>
                        <Button compact onClick={() => close(e.id, "loss")}>Loss</Button>
                        <Button compact onClick={() => close(e.id, "be")}>BE</Button>
                        <button className="btn compact" type="button" title="Skipped" onClick={() => close(e.id, "skipped")}>
                          <Icon name="x" small />
                        </button>
                      </>
                    ) : (
                      <button className="btn compact" type="button" title="Delete" onClick={() => remove(e.id)}>
                        <Icon name="trash" small />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    );

  return (
    <>
      <PageHeader
        title="Journal"
        subtitle={
          entries?.length
            ? `${String(stats.total ?? entries.length)} trades logged, ${String(stats.open ?? 0)} still open.`
            : "Trades you logged from the desk."
        }
        actions={
          <Button icon="refresh" onClick={() => void refresh()}>
            Refresh
          </Button>
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
      <div className="card">
        <div className="table-wrap">{table}</div>
      </div>
    </>
  );
}
