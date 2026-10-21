import { useCallback, useEffect, useState } from "react";
import { api, type Signal, type Stats } from "../api";
import { useFeedback } from "../components/feedback";
import { BiasPill, Button, EmptyState, KpiStrip, Na, PageHeader, StatusPill, V } from "../components/ui";
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
  if (error) table = <EmptyState text={`Signals unavailable: ${error}`} />;
  else if (!signals) table = <EmptyState text="Loading…" icon="clock" />;
  else if (!signals.length)
    table = <EmptyState text="No archived signals yet. A full analysis with a Buy or Sell bias saves one here." icon="target" />;
  else
    table = (
      <table className="data">
        <thead>
          <tr>
            <th>Created</th>
            <th>Pair</th>
            <th>Bias</th>
            <th>Setup</th>
            <th className="num">Entry</th>
            <th className="num">Stop</th>
            <th className="num">Target</th>
            <th className="num">Score</th>
            <th>Status</th>
            <th className="num">R</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {signals.map((s) => (
            <tr key={s.id}>
              <td><V value={fmtWhen(s.created_at)} /></td>
              <td className="sym">
                {s.symbol} <span className="card-sub">{s.timeframe}</span>
              </td>
              <td><BiasPill bias={s.bias} /></td>
              <td>{s.setup ? <span className="chip">{humanize(s.setup)}</span> : <Na />}</td>
              <td className="num"><V value={fmtPx(s.entry)} /></td>
              <td className="num"><V value={fmtPx(s.stop_loss)} /></td>
              <td className="num"><V value={fmtPx(s.take_profit)} /></td>
              <td className="num"><V value={fmtSigned(s.confluence)} /></td>
              <td><StatusPill status={s.status} title={s.outcome ?? undefined} /></td>
              <td className="num">
                <V value={fmtSigned(s.r_multiple, 2)} reason={s.status === "open" ? "Still open" : "Not decided"} />
              </td>
              <td>
                <div className="row-actions">
                  <Button compact busy={checking === s.id} busyLabel="…" onClick={() => void check(s.id)}>
                    Check
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    );

  return (
    <>
      <PageHeader
        title="Signals"
        subtitle="Every Buy/Sell from a full analysis, checked against later candles."
        actions={
          <>
            <Button icon="refresh" onClick={() => void refresh()}>
              Refresh
            </Button>
            <Button icon="check" primary busy={verifying} busyLabel="Verifying…" onClick={() => void verifyAll()}>
              Verify open signals
            </Button>
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
      <div className="card">
        <div className="table-wrap">{table}</div>
      </div>
    </>
  );
}
