import type { ReactNode } from "react";
import { GLYPH, biasClass } from "../lib/format";
import Icon, { type IconName } from "./Icon";

/** No data is an em dash with the reason on hover — never a zero or a blank. */
export function Na({ reason = "Not available" }: Readonly<{ reason?: string }>) {
  return (
    <span className="na" title={reason}>
      —
    </span>
  );
}

/** A formatted value, or an em dash when the formatter returned null. */
export function V({ value, reason }: Readonly<{ value: string | null; reason?: string }>) {
  return value === null ? <Na reason={reason} /> : <>{value}</>;
}

export function BiasPill({ bias }: Readonly<{ bias: string | null | undefined }>) {
  if (!bias) return <Na />;
  const cls = biasClass(bias);
  return (
    <span className={`pill ${cls}`}>
      <span className="g">{GLYPH[cls]}</span>
      {bias}
    </span>
  );
}

const TREND_BIAS: Record<string, string> = { Bullish: "Buy", Bearish: "Sell" };

export function TrendPill({ trend }: Readonly<{ trend: string | undefined }>) {
  const cls = biasClass(TREND_BIAS[trend ?? ""]);
  return (
    <span className={`pill ${cls}`}>
      <span className="g">{GLYPH[cls]}</span>
      {trend || "Neutral"}
    </span>
  );
}

const STATUS: Record<string, [string, string]> = {
  win: ["win", "✓"],
  loss: ["loss", "✕"],
  open: ["info", "○"],
  expired: ["", "◷"],
  be: ["", "="],
  skipped: ["", "–"],
  invalid: ["warn", "!"],
};

export function StatusPill({ status, title }: Readonly<{ status: string; title?: string }>) {
  const [cls, g] = STATUS[status] ?? ["", "●"];
  return (
    <span className={`pill ${cls}`} title={title}>
      <span className="g">{g}</span>
      {status || "—"}
    </span>
  );
}

export function EmptyState({ text, icon = "inbox" }: Readonly<{ text: string; icon?: IconName }>) {
  return (
    <div className="empty">
      <Icon name={icon} />
      {text}
    </div>
  );
}

export type KpiTile = {
  label: string;
  value: ReactNode;
  note: ReactNode;
  unit?: string;
  cls?: string;
};

export function KpiStrip({ tiles }: Readonly<{ tiles: KpiTile[] }>) {
  return (
    <div className="kpi-strip" role="list">
      {tiles.map((t) => (
        <div className="kpi" role="listitem" key={t.label}>
          <div className="kpi-label">{t.label}</div>
          <div className={`kpi-value ${t.cls ?? ""}`}>
            {t.value}
            {t.unit ? <span className="unit">{t.unit}</span> : null}
          </div>
          <div className="kpi-note">{t.note}</div>
        </div>
      ))}
    </div>
  );
}

export function Card({
  title,
  icon,
  right,
  children,
  className = "",
  bodyClassName = "card-body",
}: Readonly<{
  title: ReactNode;
  icon: IconName;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}>) {
  return (
    <div className={`card ${className}`}>
      <div className="card-head">
        <h3>
          <Icon name={icon} />
          {title}
        </h3>
        {right ? <div className="right">{right}</div> : null}
      </div>
      <div className={bodyClassName}>{children}</div>
    </div>
  );
}

export function Button({
  children,
  icon,
  primary = false,
  compact = false,
  busy = false,
  busyLabel = "Working…",
  disabled = false,
  title,
  onClick,
}: Readonly<{
  children: ReactNode;
  icon?: IconName;
  primary?: boolean;
  compact?: boolean;
  busy?: boolean;
  busyLabel?: string;
  disabled?: boolean;
  title?: string;
  onClick: () => void;
}>) {
  const cls = ["btn", primary ? "primary" : "", compact ? "compact" : ""].filter(Boolean).join(" ");
  return (
    <button className={cls} type="button" disabled={busy || disabled} title={title} onClick={onClick}>
      {busy ? (
        <>
          <span className="spinner" />
          {busyLabel}
        </>
      ) : (
        <>
          {icon ? <Icon name={icon} small /> : null}
          {children}
        </>
      )}
    </button>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: Readonly<{ title: string; subtitle: string; actions?: ReactNode }>) {
  return (
    <div className="page-header">
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {actions ? <div className="actions">{actions}</div> : null}
    </div>
  );
}
