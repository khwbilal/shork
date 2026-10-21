import { useState } from "react";
import { api, type WatchlistResponse } from "../api";
import { Button, BiasPill, EmptyState, KpiStrip, Na, PageHeader, V } from "../components/ui";
import { fmtPx, fmtSigned, humanize } from "../lib/format";

export default function Watchlist({
  timeframe,
  onOpen,
}: Readonly<{ timeframe: string; onOpen: (symbol: string) => void }>) {
  const [data, setData] = useState<WatchlistResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function score() {
    setBusy(true);
    setError(null);
    try {
      setData(await api.scoreWatchlist(timeframe));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const rows = data?.rows ?? [];
  const top = rows[0];
  const notScored = <Na reason="Not scored yet" />;

  let table: React.ReactNode;
  if (busy) table = <EmptyState text="Scoring the watchlist… this takes 20–40 seconds." icon="clock" />;
  else if (error) table = <EmptyState text={`Scoring failed: ${error}`} />;
  else if (!data) table = <EmptyState text="Scoring takes 20–40 seconds. Use the button above." icon="list" />;
  else if (!rows.length) table = <EmptyState text="No results." />;
  else
    table = (
      <table className="data">
        <thead>
          <tr>
            <th>Pair</th>
            <th>Quality</th>
            <th>Bias</th>
            <th className="num">Confluence</th>
            <th>Setup</th>
            <th>MTF</th>
            <th>Book</th>
            <th>Liquidity</th>
            <th className="num">Price</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.symbol}>
              <td className="sym">{r.symbol}</td>
              <td>
                <span className="quality">
                  <span className="track">
                    <i style={{ width: `${r.quality ?? 0}%` }} />
                  </span>
                  {r.quality ?? 0}
                </span>
              </td>
              <td>{r.error ? <Na reason={r.error} /> : <BiasPill bias={r.bias} />}</td>
              <td className="num">
                <V value={fmtSigned(r.confluence)} />
              </td>
              <td>
                {r.setup ? (
                  <>
                    <span className="chip">{humanize(r.setup)}</span>
                    {r.trade_allowed === false ? (
                      <>
                        {" "}
                        <span className="pill warn">
                          <span className="g">!</span>chop
                        </span>
                      </>
                    ) : null}
                  </>
                ) : (
                  <Na />
                )}
              </td>
              <td>{r.mtf_alignment ? humanize(r.mtf_alignment).toLowerCase() : <Na />}</td>
              <td>{r.book_bias ?? <Na reason="Depth unavailable" />}</td>
              <td>{r.liq_bias ?? <Na reason="No futures data" />}</td>
              <td className="num">
                <V value={fmtPx(r.price)} />
              </td>
              <td>
                <div className="row-actions">
                  <Button compact onClick={() => onOpen(r.symbol)}>
                    Open
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
        title="Watchlist"
        subtitle={
          data
            ? `${String(rows.length)} pairs scored on ${data.timeframe}, ${String(data.actionable_count)} actionable.`
            : "Score the majors for setup quality: confluence, chop filter, book and liquidity."
        }
        actions={
          <Button icon="refresh" primary busy={busy} busyLabel="Scoring…" onClick={score}>
            Score watchlist
          </Button>
        }
      />
      <KpiStrip
        tiles={[
          { label: "Scored", value: data ? String(rows.length) : notScored, note: data ? `On ${data.timeframe}` : "Pairs in the list" },
          { label: "Actionable", value: data ? String(data.actionable_count) : notScored, note: "Trade allowed, quality ≥ 55" },
          {
            label: "Top pick",
            value: top ? top.symbol : notScored,
            note: top ? `Quality ${String(top.quality ?? 0)} · ${top.bias ?? "—"}` : "Highest quality",
          },
          { label: "Timeframe", value: data?.timeframe ?? timeframe, note: "From the top bar" },
        ]}
      />
      <div className="card">
        <div className="table-wrap">{table}</div>
      </div>
    </>
  );
}
