export type Bias = "Buy" | "Sell" | "Neutral";

export type TradeLevels = {
  bias: Bias;
  entry: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  support: number | null;
  resistance: number | null;
  support_2: number | null;
  resistance_2: number | null;
  trend: string | null;
  trend_line: string | null;
  ema20: number | null;
  ema50: number | null;
  confidence: number | null;
  reasoning: string;
};

export type Confluence = {
  score?: number;
  bias?: Bias;
  confidence?: number;
  components?: Record<string, number>;
  summary?: string;
};

export type Setup = {
  type?: string;
  trade_allowed?: boolean;
  prefer_bias?: Bias | null;
  adx?: number | null;
  mtf_alignment?: string;
  summary?: string;
};

export type MtfFrame = { trend?: string; rsi?: number; macd?: string; adx?: number };

export type Flow = {
  available?: boolean;
  whale_bias?: string;
  whale_long_pct?: number;
  retail_bias?: string;
  retail_long_pct?: number;
  funding_bias?: string;
  funding_apr_est?: number;
  oi_change_pct?: number;
  taker_bias?: string;
  oi_price_signal?: string;
  basis_pct?: number;
  price_change_24h_pct?: number;
  summary?: string;
};

export type LiqPoint = { price?: number; distance_pct?: number; move_pct?: number };

export type Liquidity = {
  available?: boolean;
  bias?: string;
  long_share_pct?: number;
  short_share_pct?: number;
  nearest_long_liq?: LiqPoint;
  nearest_short_liq?: LiqPoint;
  cascade?: { long_cascade_trigger?: LiqPoint; short_squeeze_trigger?: LiqPoint };
  summary?: string;
};

export type OrderBook = { available?: boolean; bias?: string; imbalance?: number };

export type Market = {
  data_source?: string;
  coin_analysis?: { price_data?: { current_price?: number } };
  yahoo_price?: { price?: number; change_pct?: number };
  flow?: Flow;
  orderbook?: OrderBook;
  liquidity?: Liquidity;
  mtf_local?: { alignment?: string; timeframes?: Record<string, MtfFrame> };
  setup?: Setup;
  confluence?: Confluence;
  recorded_signal_id?: string;
};

export type AnalyzeResponse = {
  symbol: string;
  exchange: string;
  timeframe: string;
  tv_symbol: string;
  market: Market;
  levels: TradeLevels;
  analysis: string;
  provider: string;
};

export type ChatMessage = { role: "user" | "assistant" | "system"; content: string };

export type ChatResponse = { symbol: string; reply: string; provider: string };

export type HealthResponse = {
  status: string;
  app: string;
  ai_provider: string;
  ai_model: string | null;
  tradingview_ready: boolean;
};

export type SymbolResult = { symbol: string; exchange: string; tv_symbol: string; kind: string; label: string };

export type WatchlistRow = {
  symbol: string;
  quality?: number;
  bias?: Bias;
  confluence?: number;
  setup?: string;
  trade_allowed?: boolean;
  mtf_alignment?: string;
  book_bias?: string | null;
  liq_bias?: string | null;
  price?: number;
  error?: string;
};

export type WatchlistResponse = {
  timeframe: string;
  count: number;
  actionable_count: number;
  rows: WatchlistRow[];
};

export type Stats = {
  total?: number;
  open?: number;
  closed?: number;
  wins?: number;
  losses?: number;
  breakeven?: number;
  expired?: number;
  hit_rate?: number | null;
  avg_r?: number | null;
};

export type JournalEntry = {
  id: string;
  created_at: string;
  symbol: string;
  timeframe?: string;
  side: "Buy" | "Sell";
  setup?: string | null;
  entry?: number | null;
  stop_loss?: number | null;
  take_profit?: number | null;
  status: string;
  r_multiple?: number | null;
};

export type Signal = {
  id: string;
  created_at: string;
  symbol: string;
  timeframe?: string;
  bias: Bias;
  setup?: string | null;
  entry?: number;
  stop_loss?: number;
  take_profit?: number;
  confluence?: number | null;
  status: string;
  outcome?: string | null;
  r_multiple?: number | null;
};

function apiError(body: string): string {
  try {
    const j = JSON.parse(body) as { detail?: unknown };
    if (typeof j.detail === "string") return j.detail;
    if (Array.isArray(j.detail)) return j.detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join("; ");
  } catch {
    /* not JSON */
  }
  return body;
}

async function request<T>(path: string, init?: { method?: string; body?: unknown }): Promise<T> {
  const res = await fetch(path, {
    method: init?.method ?? "GET",
    headers: init?.body === undefined ? undefined : { "Content-Type": "application/json" },
    body: init?.body === undefined ? undefined : JSON.stringify(init.body),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(apiError(text) || res.statusText);
  return (text ? JSON.parse(text) : null) as T;
}

type Pair = { symbol: string; exchange: string; timeframe: string };

export const api = {
  health: () => request<HealthResponse>("/api/health"),
  analyze: (p: Pair) => request<AnalyzeResponse>("/api/analyze", { method: "POST", body: p }),
  chat: (p: Pair & { message: string; history: ChatMessage[] }) =>
    request<ChatResponse>("/api/chat", { method: "POST", body: p }),
  searchSymbols: (q: string, exchange: string) =>
    request<{ results: SymbolResult[] }>(
      `/api/symbols/search?q=${encodeURIComponent(q)}&exchange=${encodeURIComponent(exchange)}&limit=20`,
    ),
  scoreWatchlist: (timeframe: string) =>
    request<WatchlistResponse>(`/api/watchlist/score?timeframe=${encodeURIComponent(timeframe)}`),
  journal: () => request<{ entries: JournalEntry[]; stats: Stats }>("/api/journal?limit=100"),
  addJournal: (body: Record<string, unknown>) => request<JournalEntry>("/api/journal", { method: "POST", body }),
  closeJournal: (id: string, status: string, exit_price: number | null) =>
    request<JournalEntry>(`/api/journal/${encodeURIComponent(id)}/close`, { method: "POST", body: { status, exit_price } }),
  deleteJournal: (id: string) => request<{ ok: boolean }>(`/api/journal/${encodeURIComponent(id)}`, { method: "DELETE" }),
  signals: () => request<{ signals: Signal[]; stats: Stats }>("/api/signals?limit=100"),
  verifySignals: () =>
    request<{ checked: number; updated: number; stats: Stats }>("/api/signals/verify?only_open=true&limit=50", {
      method: "POST",
    }),
  verifySignal: (id: string) =>
    request<{ signal: Signal; stats: Stats }>(`/api/signals/${encodeURIComponent(id)}/verify`, { method: "POST" }),
};
