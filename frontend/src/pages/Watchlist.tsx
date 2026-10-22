import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import FormatListBulleted from "@mui/icons-material/FormatListBulleted";
import Refresh from "@mui/icons-material/Refresh";
import { useState } from "react";
import { api, type WatchlistResponse } from "../api";
import { ActionButton, BiasPill, DataTable, EmptyState, KpiStrip, Na, Num, PageHeader, Pill, V } from "../components/ui";
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
  if (busy)
    table = (
      <Box sx={{ p: 2 }}>
        <Alert severity="info" variant="outlined" sx={{ mb: 2 }}>
          Scoring the watchlist. This takes 20 to 40 seconds.
        </Alert>
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} height={40} />
        ))}
      </Box>
    );
  else if (error)
    table = (
      <Alert severity="warning" sx={{ m: 2 }}>
        Scoring failed: {error}
      </Alert>
    );
  else if (!data) table = <EmptyState text="Scoring takes 20 to 40 seconds. Use the button above." icon={<FormatListBulleted />} />;
  else if (!rows.length) table = <EmptyState text="No results." />;
  else
    table = (
      <DataTable minWidth={980}>
        <TableHead>
          <TableRow>
            <TableCell>Pair</TableCell>
            <TableCell>Quality</TableCell>
            <TableCell>Bias</TableCell>
            <TableCell align="right">Confluence</TableCell>
            <TableCell>Setup</TableCell>
            <TableCell>MTF</TableCell>
            <TableCell>Book</TableCell>
            <TableCell>Liquidity</TableCell>
            <TableCell align="right">Price</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((r) => (
            <TableRow key={r.symbol} hover>
              <TableCell>
                <Num sx={{ fontWeight: 700 }}>{r.symbol}</Num>
              </TableCell>
              <TableCell>
                {r.quality === undefined ? (
                  <Na reason={r.error ?? "Not scored"} />
                ) : (
                  <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                    <LinearProgress variant="determinate" value={Math.max(0, Math.min(100, r.quality))} sx={{ width: 64, height: 6, borderRadius: 3 }} />
                    <Num>{r.quality}</Num>
                  </Stack>
                )}
              </TableCell>
              <TableCell>{r.error ? <Na reason={r.error} /> : <BiasPill bias={r.bias} />}</TableCell>
              <TableCell align="right">
                <V value={fmtSigned(r.confluence)} />
              </TableCell>
              <TableCell>
                {r.setup ? (
                  <Stack direction="row" spacing={0.5}>
                    <Chip size="small" label={humanize(r.setup)} />
                    {r.trade_allowed === false ? <Pill glyph="!" label="chop" tone="warn" /> : null}
                  </Stack>
                ) : (
                  <Na />
                )}
              </TableCell>
              <TableCell>{r.mtf_alignment ? humanize(r.mtf_alignment).toLowerCase() : <Na />}</TableCell>
              <TableCell>{r.book_bias ?? <Na reason="Depth unavailable" />}</TableCell>
              <TableCell>{r.liq_bias ?? <Na reason="No futures data" />}</TableCell>
              <TableCell align="right">
                <V value={fmtPx(r.price)} />
              </TableCell>
              <TableCell align="right">
                <Button size="small" variant="outlined" color="inherit" sx={{ borderColor: "divider" }} onClick={() => onOpen(r.symbol)}>
                  Open
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
        title="Watchlist"
        subtitle={
          data
            ? `${String(rows.length)} pairs scored on ${data.timeframe}, ${String(data.actionable_count)} actionable.`
            : "Score the majors for setup quality: confluence, chop filter, book and liquidity."
        }
        actions={
          <ActionButton icon={<Refresh />} primary busy={busy} busyLabel="Scoring…" onClick={() => void score()}>
            Score watchlist
          </ActionButton>
        }
      />
      <KpiStrip
        tiles={[
          { label: "Scored", value: data ? String(rows.length) : notScored, note: data ? `On ${data.timeframe}` : "Pairs in the list" },
          { label: "Actionable", value: data ? String(data.actionable_count) : notScored, note: "Trade allowed, quality ≥ 55" },
          {
            label: "Top pick",
            value: top ? top.symbol : notScored,
            note: top ? (
              <>
                Quality {top.quality ?? <Na />} · {top.bias ?? <Na />}
              </>
            ) : (
              "Highest quality"
            ),
          },
          { label: "Timeframe", value: data?.timeframe ?? timeframe, note: "From the top bar" },
        ]}
      />
      <Card>{table}</Card>
    </Stack>
  );
}
