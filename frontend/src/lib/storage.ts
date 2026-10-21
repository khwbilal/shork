/** localStorage for per-browser preferences only; every access may throw. */
export function readPref(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writePref(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* private mode / blocked storage */
  }
}

export type RecentPair = { symbol: string; exchange: string; tv_symbol: string };

export function readRecents(): RecentPair[] {
  try {
    const list = JSON.parse(readPref("cca_recent") ?? "[]") as unknown;
    return Array.isArray(list) ? (list as RecentPair[]) : [];
  } catch {
    return [];
  }
}

export function rememberRecent(pair: RecentPair): void {
  const list = readRecents().filter((r) => r.symbol !== pair.symbol);
  list.unshift(pair);
  writePref("cca_recent", JSON.stringify(list.slice(0, 6)));
}
