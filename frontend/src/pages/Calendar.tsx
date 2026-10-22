import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import CalendarMonthOutlined from "@mui/icons-material/CalendarMonthOutlined";
import Refresh from "@mui/icons-material/Refresh";
import { useCallback, useEffect, useState } from "react";
import { api, type CalendarEvent, type CalendarKind, type CalendarResponse } from "../api";
import { ActionButton, DataTable, EmptyState, Na, Num, PageHeader, Pill, monoSx } from "../components/ui";
import { fmtWhen, pktToday } from "../lib/format";

const FILTERS: { key: CalendarKind | ""; label: string }[] = [
  { key: "", label: "All" },
  { key: "macro", label: "Macro" },
  { key: "earnings", label: "Earnings" },
  { key: "binance", label: "Binance" },
  { key: "crypto", label: "Crypto" },
];

const SESSION: Record<string, string> = { before_open: "Before open", after_close: "After close" };

/** Impact is not direction: warning tones and neutral only, never green or red. */
function ImpactPill({ impact }: Readonly<{ impact: CalendarEvent["impact"] }>) {
  if (impact === "high") return <Pill glyph="!" label="High" tone="warn" variant="filled" />;
  if (impact === "medium") return <Pill glyph="◐" label="Medium" tone="warn" />;
  if (impact === "low") return <Pill glyph="○" label="Low" />;
  return <Na reason="No impact rating from the source" />;
}

function addDays(ymd: string, n: number): string {
  const d = new Date(`${ymd}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function dayLabel(ymd: string, today: string): string {
  const d = new Date(`${ymd}T00:00:00Z`);
  const text = d.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });
  if (ymd === today) return `Today · ${text}`;
  if (ymd === addDays(today, 1)) return `Tomorrow · ${text}`;
  return text;
}

/** starts_at already carries +05:00, so the PKT date and time are the string's own parts. */
function pktDate(e: CalendarEvent): string {
  return e.starts_at.slice(0, 10);
}

function pktTime(e: CalendarEvent): string {
  return e.all_day ? "all day" : e.starts_at.slice(11, 16);
}

function groupByDay(events: CalendarEvent[]): [string, CalendarEvent[]][] {
  const map = new Map<string, CalendarEvent[]>();
  for (const e of events) {
    const day = pktDate(e);
    const list = map.get(day) ?? [];
    list.push(e);
    map.set(day, list);
  }
  return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
}

function Value({ v, reason }: Readonly<{ v: string | null | undefined; reason: string }>) {
  return v ? <Num>{v}</Num> : <Na reason={reason} />;
}

function EventRow({ e, onOpenPair }: Readonly<{ e: CalendarEvent; onOpenPair: (symbol: string, exchange: string, tv: string) => void }>) {
  const where = e.ticker ?? e.country;
  return (
    <TableRow hover>
      <TableCell sx={{ width: 80 }}>
        <Box component="span" sx={[monoSx, { fontWeight: 600, color: e.all_day ? "text.secondary" : "text.primary" }]}>
          {pktTime(e)}
        </Box>
      </TableCell>
      <TableCell sx={{ width: 110 }}>
        <ImpactPill impact={e.impact} />
      </TableCell>
      <TableCell sx={{ width: 90 }}>{where ? <Num sx={{ fontWeight: 600 }}>{where}</Num> : <Na reason="No country or ticker" />}</TableCell>
      <TableCell sx={{ whiteSpace: "normal", minWidth: 260 }}>
        <Typography variant="body2" sx={{ fontWeight: 500 }}>
          {e.url ? (
            <Link href={e.url} target="_blank" rel="noopener noreferrer" underline="hover" color="inherit">
              {e.title}
            </Link>
          ) : (
            e.title
          )}
        </Typography>
        {e.kind === "earnings" ? (
          <Stack direction="row" spacing={0.5} useFlexGap sx={{ flexWrap: "wrap", mt: 0.5, alignItems: "center" }}>
            <Typography variant="caption" sx={{ color: "text.secondary", mr: 0.5 }}>
              {e.session ? (SESSION[e.session] ?? e.session) : "Session not given"}
            </Typography>
            {e.instrument_symbols.map((tv) => {
              const [ex, sym] = tv.includes(":") ? tv.split(":", 2) : ["BINANCE", tv];
              return (
                <Chip
                  key={tv}
                  size="small"
                  variant="outlined"
                  color="primary"
                  label={sym}
                  title={`Open ${tv} on the desk`}
                  onClick={() => onOpenPair(sym, ex, tv)}
                  sx={monoSx}
                />
              );
            })}
          </Stack>
        ) : null}
      </TableCell>
      <TableCell align="right">
        <Value v={e.forecast} reason="No forecast" />
      </TableCell>
      <TableCell align="right">
        <Value v={e.previous} reason="No previous value" />
      </TableCell>
      <TableCell align="right">
        <Value v={e.actual} reason="Not released yet" />
      </TableCell>
    </TableRow>
  );
}

/** Economic, earnings and Binance events for the next 7 days, in PKT (WL-039). */
export default function CalendarPage({
  active,
  onOpenPair,
}: Readonly<{ active: boolean; onOpenPair: (symbol: string, exchange: string, tv: string) => void }>) {
  const [kind, setKind] = useState<CalendarKind | "">("");
  const [data, setData] = useState<CalendarResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await api.calendar(7, kind));
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [kind]);

  useEffect(() => {
    if (active) load().catch(() => undefined);
  }, [active, load]);

  const today = pktToday();
  const days = data ? groupByDay(data.events) : [];

  let body: React.ReactNode;
  if (error) body = <Alert severity="warning">Calendar unavailable: {error}</Alert>;
  else if (!data)
    body = (
      <Card sx={{ p: 2 }}>
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} height={40} />
        ))}
      </Card>
    );
  else if (!days.length)
    body = (
      <Card>
        <EmptyState
          text={kind ? `No ${kind} events in the next 7 days.` : "No events in the next 7 days. The calendar job refreshes daily at 16:00 PKT."}
          icon={<CalendarMonthOutlined />}
        />
      </Card>
    );
  else
    body = days.map(([day, events]) => (
      <Card key={day}>
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", px: 2, minHeight: 44, borderBottom: 1, borderColor: "divider" }}>
          <Typography variant="h3" component="h3" sx={{ flex: 1 }}>
            {dayLabel(day, today)}
          </Typography>
          <Typography variant="caption" sx={{ color: "text.secondary" }}>
            {events.length} {events.length === 1 ? "event" : "events"}
          </Typography>
        </Stack>
        <DataTable minWidth={860} maxHeight="none">
          <TableHead>
            <TableRow>
              <TableCell>Time PKT</TableCell>
              <TableCell>Impact</TableCell>
              <TableCell>Where</TableCell>
              <TableCell>Event</TableCell>
              <TableCell align="right">Forecast</TableCell>
              <TableCell align="right">Previous</TableCell>
              <TableCell align="right">Actual</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {events.map((e) => (
              <EventRow key={e.id} e={e} onOpenPair={onOpenPair} />
            ))}
          </TableBody>
        </DataTable>
      </Card>
    ));

  return (
    <Stack spacing={2}>
      <PageHeader
        title="Calendar"
        subtitle="Macro releases, US earnings for Binance-listed stocks, and Binance events for the next 7 days. Times in PKT."
        actions={
          <ActionButton icon={<Refresh />} busy={loading} busyLabel="Loading…" onClick={() => void load()}>
            Refresh
          </ActionButton>
        }
      />
      <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ alignItems: { xs: "stretch", md: "center" }, justifyContent: "space-between" }}>
        <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }} role="group" aria-label="Filter by type">
          {FILTERS.map((f) => (
            <Chip
              key={f.key || "all"}
              label={f.label}
              color={kind === f.key ? "primary" : "default"}
              variant={kind === f.key ? "filled" : "outlined"}
              aria-pressed={kind === f.key}
              onClick={() => setKind(f.key)}
              sx={{ minHeight: { xs: 40, sm: 32 } }}
            />
          ))}
        </Stack>
        {data ? (
          <Stack direction="row" spacing={0.75} useFlexGap sx={{ flexWrap: "wrap" }} aria-label="Sources">
            {data.sources.map((s) => {
              const ok = s.available !== false;
              const title = ok
                ? `${s.name}: ${String(s.events ?? 0)} events, fetched ${fmtWhen(s.fetched_at ?? undefined) ?? "at an unknown time"}`
                : `${s.name}: ${s.error ?? "unavailable"}`;
              return <Pill key={s.name} glyph={ok ? "✓" : "✕"} label={s.name.replace(/_/g, " ")} tone={ok ? "neutral" : "warn"} title={title} />;
            })}
          </Stack>
        ) : null}
      </Stack>
      {body}
    </Stack>
  );
}
