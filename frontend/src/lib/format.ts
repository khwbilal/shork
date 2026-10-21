import type { Market } from "../api";

export function isNum(n: unknown): n is number {
  return n !== null && n !== undefined && n !== "" && !Number.isNaN(Number(n));
}

export function fmtPx(n: unknown): string | null {
  if (!isNum(n)) return null;
  const v = Number(n);
  const digits = Math.abs(v) >= 1000 ? 2 : Math.abs(v) >= 1 ? 4 : 6;
  return v.toLocaleString(undefined, { maximumFractionDigits: digits });
}

export function fmtSigned(n: unknown, digits = 1): string | null {
  if (!isNum(n)) return null;
  const v = Number(n);
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}`;
}

export function fmtPct(n: unknown, digits = 1): string | null {
  const s = fmtSigned(n, digits);
  return s === null ? null : `${s}%`;
}

export function fmtConf(c: unknown): string | null {
  if (!isNum(c)) return null;
  const v = Number(c);
  return `${Math.round(v <= 1 ? v * 100 : v)}%`;
}

export function fmtWhen(iso: string | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function rewardRisk(entry: unknown, stop: unknown, target: unknown): number | null {
  if (!isNum(entry) || !isNum(stop) || !isNum(target)) return null;
  const risk = Math.abs(entry - stop);
  return risk > 0 ? Math.abs(target - entry) / risk : null;
}

export type Direction = "buy" | "sell" | "";

export function biasClass(bias: string | null | undefined): Direction {
  const b = String(bias ?? "").toLowerCase();
  if (b === "buy" || b === "long") return "buy";
  if (b === "sell" || b === "short") return "sell";
  return "";
}

export const GLYPH: Record<Direction, string> = { buy: "▲", sell: "▼", "": "●" };

export function humanize(s: string | null | undefined): string {
  return String(s ?? "").replace(/_/g, " ");
}

export function currentPrice(market: Market | null): number | undefined {
  return market?.coin_analysis?.price_data?.current_price ?? market?.yahoo_price?.price;
}
