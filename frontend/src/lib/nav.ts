/** Routes, timeframes and labels shared by the shell, the search and the pages. */
export const PAGES = {
  desk: "Desk",
  watchlist: "Watchlist",
  calendar: "Calendar",
  journal: "Journal",
  signals: "Signals",
} as const;
export type PageKey = keyof typeof PAGES;

export const TIMEFRAMES = ["15m", "1h", "4h", "1D"] as const;
export const EXCHANGES = ["BINANCE", "KUCOIN", "BYBIT", "MEXC"] as const;

export const PROVIDER_LABEL: Record<string, string> = {
  claude: "Claude API",
  claude_code: "Claude subscription",
  cursor: "Cursor",
  openai: "OpenAI",
  offline: "No AI",
  none: "No AI",
};
