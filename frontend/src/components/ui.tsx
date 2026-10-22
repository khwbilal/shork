import Box from "@mui/material/Box";
import Button, { type ButtonProps } from "@mui/material/Button";
import Card from "@mui/material/Card";
import Chip, { type ChipProps } from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableContainer from "@mui/material/TableContainer";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import InboxOutlined from "@mui/icons-material/InboxOutlined";
import type { SxProps, Theme } from "@mui/material/styles";
import type { ReactElement, ReactNode } from "react";
import { GLYPH, biasClass, type Direction } from "../lib/format";

/** Monospace with tabular figures, for prices, scores and IDs. */
export const monoSx = (t: Theme) => ({ fontFamily: t.typography.fontFamilyMono, fontVariantNumeric: "tabular-nums" as const });

/** A number in the mono face. */
export function Num({ children, sx }: Readonly<{ children: ReactNode; sx?: SxProps<Theme> }>) {
  return (
    <Box component="span" sx={[monoSx, ...(Array.isArray(sx) ? sx : [sx])] as SxProps<Theme>}>
      {children}
    </Box>
  );
}

/** No data is an em dash with the reason on hover, never a zero or a blank (ruleset 9.3). */
export function Na({ reason = "Not available" }: Readonly<{ reason?: string }>) {
  return (
    <Tooltip title={reason}>
      <Box component="span" aria-label={reason} tabIndex={0} sx={{ color: "text.disabled", cursor: "help" }}>
        —
      </Box>
    </Tooltip>
  );
}

/** A formatted value, or an em dash when the formatter returned null. */
export function V({ value, reason, mono = true }: Readonly<{ value: string | null; reason?: string; mono?: boolean }>) {
  if (value === null) return <Na reason={reason} />;
  return mono ? <Num>{value}</Num> : <>{value}</>;
}

type Tone = "buy" | "sell" | "neutral" | "info" | "warn" | "error";

const TONE: Record<Tone, ChipProps["color"]> = {
  buy: "success",
  sell: "error",
  neutral: "default",
  info: "primary",
  warn: "warning",
  error: "error",
};

/** A small chip that always carries a glyph as well as a colour, so it reads in greyscale. */
export function Pill({
  glyph,
  label,
  tone = "neutral",
  title,
  variant = "outlined",
  onClick,
}: Readonly<{
  glyph: string;
  label: ReactNode;
  tone?: Tone;
  title?: ReactNode;
  variant?: "outlined" | "filled";
  onClick?: () => void;
}>) {
  const chip = (
    <Chip
      size="small"
      variant={variant}
      color={TONE[tone]}
      onClick={onClick}
      label={
        <Box component="span" sx={{ display: "inline-flex", alignItems: "center", gap: 0.5 }}>
          <Box component="span" aria-hidden sx={{ fontSize: "0.7em" }}>
            {glyph}
          </Box>
          {label}
        </Box>
      }
    />
  );
  return title ? <Tooltip title={title}>{chip}</Tooltip> : chip;
}

export function toneOf(cls: Direction): Tone {
  if (cls === "buy") return "buy";
  if (cls === "sell") return "sell";
  return "neutral";
}

export function BiasPill({ bias, title }: Readonly<{ bias: string | null | undefined; title?: ReactNode }>) {
  if (!bias) return <Na />;
  const cls = biasClass(bias);
  return <Pill glyph={GLYPH[cls]} label={bias} tone={toneOf(cls)} title={title} />;
}

const TREND_BIAS: Record<string, string> = { Bullish: "Buy", Bearish: "Sell" };

export function TrendPill({ trend }: Readonly<{ trend: string | undefined }>) {
  const cls = biasClass(TREND_BIAS[trend ?? ""]);
  return <Pill glyph={GLYPH[cls]} label={trend || "Neutral"} tone={toneOf(cls)} />;
}

const STATUS: Record<string, [Tone, string]> = {
  win: ["buy", "✓"],
  loss: ["sell", "✕"],
  open: ["info", "○"],
  expired: ["neutral", "◷"],
  be: ["neutral", "="],
  skipped: ["neutral", "⊘"],
  invalid: ["warn", "!"],
};

export function StatusPill({ status, title }: Readonly<{ status: string; title?: string }>) {
  if (!status) return <Na reason="No status" />;
  const [tone, g] = STATUS[status] ?? ["neutral", "●"];
  return <Pill glyph={g} label={status} tone={tone} title={title} />;
}

export function EmptyState({ text, icon }: Readonly<{ text: string; icon?: ReactElement }>) {
  return (
    <Stack spacing={1} sx={{ alignItems: "center", py: 5, px: 2, color: "text.secondary", textAlign: "center" }}>
      <Box sx={{ color: "text.disabled", display: "flex", "& svg": { fontSize: 28 } }}>{icon ?? <InboxOutlined />}</Box>
      <Typography variant="body2">{text}</Typography>
    </Stack>
  );
}

export type KpiTile = {
  label: string;
  value: ReactNode;
  note: ReactNode;
  unit?: string;
  tone?: Direction | "text";
};

/** KPI tiles; on a phone they scroll sideways inside the strip instead of wrapping. */
export function KpiStrip({ tiles }: Readonly<{ tiles: KpiTile[] }>) {
  return (
    <Paper
      variant="outlined"
      role="list"
      sx={{
        display: "grid",
        gridAutoFlow: "column",
        gridAutoColumns: { xs: "minmax(150px, 1fr)", md: "minmax(0, 1fr)" },
        overflowX: "auto",
        scrollSnapType: "x mandatory",
      }}
    >
      {tiles.map((t, i) => {
        let color = "text.primary";
        if (t.tone === "buy") color = "success.main";
        else if (t.tone === "sell") color = "error.main";
        return (
          <Box
            role="listitem"
            key={t.label}
            sx={{ px: 2, py: 1.5, minWidth: 0, scrollSnapAlign: "start", borderLeft: i ? 1 : 0, borderColor: "divider" }}
          >
            <Typography variant="overline" component="div" sx={{ color: "text.secondary" }}>
              {t.label}
            </Typography>
            <Box
              sx={[
                monoSx,
                { fontSize: "1.25rem", fontWeight: 600, color, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" },
              ]}
            >
              {t.value}
              {t.unit ? (
                <Box component="span" sx={{ fontSize: "0.75rem", color: "text.secondary", ml: 0.5, fontWeight: 500 }}>
                  {t.unit}
                </Box>
              ) : null}
            </Box>
            <Typography variant="caption" component="div" noWrap sx={{ color: "text.secondary" }}>
              {t.note}
            </Typography>
          </Box>
        );
      })}
    </Paper>
  );
}

/** A widget card with a header row: icon, title, and an optional right slot. */
export function SectionCard({
  title,
  icon,
  right,
  children,
  noPadding = false,
  sx,
}: Readonly<{
  title: ReactNode;
  icon?: ReactElement;
  right?: ReactNode;
  children: ReactNode;
  noPadding?: boolean;
  sx?: SxProps<Theme>;
}>) {
  return (
    <Card sx={[{ display: "flex", flexDirection: "column", minWidth: 0 }, ...(Array.isArray(sx) ? sx : [sx])] as SxProps<Theme>}>
      <Stack
        direction="row"
       
        spacing={1}
        sx={{ alignItems: "center", px: 2, minHeight: 48, borderBottom: 1, borderColor: "divider", flexShrink: 0 }}
      >
        {icon ? <Box sx={{ display: "flex", color: "text.secondary", "& svg": { fontSize: 18 } }}>{icon}</Box> : null}
        <Typography variant="h3" component="h3" noWrap sx={{ flex: 1, minWidth: 0 }}>
          {title}
        </Typography>
        {right ? <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexShrink: 0 }}>{right}</Box> : null}
      </Stack>
      <Box sx={{ p: noPadding ? 0 : 2, flex: 1, minHeight: 0 }}>{children}</Box>
    </Card>
  );
}

/** A table that scrolls inside its card with a sticky header, so the page never scrolls sideways. */
export function DataTable({ children, minWidth = 760, maxHeight }: Readonly<{ children: ReactNode; minWidth?: number; maxHeight?: number | string }>) {
  return (
    <TableContainer sx={{ maxHeight: maxHeight ?? { xs: "70vh", md: "calc(100vh - 300px)" }, overflowX: "auto" }}>
      <Table stickyHeader size="small" sx={{ minWidth }}>
        {children}
      </Table>
    </TableContainer>
  );
}

/** A button with a busy state; `primary` makes it the one contained button of the view. */
export function ActionButton({
  children,
  icon,
  primary = false,
  compact = false,
  busy = false,
  busyLabel = "Working…",
  disabled = false,
  title,
  color,
  onClick,
}: Readonly<{
  children: ReactNode;
  icon?: ReactElement;
  primary?: boolean;
  compact?: boolean;
  busy?: boolean;
  busyLabel?: string;
  disabled?: boolean;
  title?: string;
  color?: ButtonProps["color"];
  onClick: () => void;
}>) {
  const btn = (
    <Button
      variant={primary ? "contained" : "outlined"}
      color={color ?? (primary ? "primary" : "inherit")}
      size={compact ? "small" : "medium"}
      disabled={busy || disabled}
      startIcon={busy ? <CircularProgress size={14} color="inherit" /> : icon}
      onClick={onClick}
      sx={primary ? undefined : { borderColor: "divider" }}
    >
      {busy ? busyLabel : children}
    </Button>
  );
  if (!title) return btn;
  return (
    <Tooltip title={title}>
      <span>{btn}</span>
    </Tooltip>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: Readonly<{ title: string; subtitle: ReactNode; actions?: ReactNode }>) {
  return (
    <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ alignItems: { xs: "stretch", sm: "flex-end" }, justifyContent: "space-between" }}>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="h2" component="h2" sx={{ overflowWrap: "anywhere" }}>
          {title}
        </Typography>
        <Typography variant="body2" sx={{ color: "text.secondary", mt: 0.5 }}>
          {subtitle}
        </Typography>
      </Box>
      {actions ? (
        <Stack
          direction="row"
          spacing={1}
          sx={{ flexShrink: 0, "& > *": { flex: { xs: 1, sm: "none" } }, "& .MuiButton-root": { width: { xs: "100%", sm: "auto" } } }}
        >
          {actions}
        </Stack>
      ) : null}
    </Stack>
  );
}
