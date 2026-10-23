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
  correlation?: Correlation;
  recorded_signal_id?: string;
};

export type StrategyInfo = {
  id: string;
  label: string;
  summary: string;
  primary_tf?: string | null;
  context_tfs?: string[];
  incompatible_desk_tfs?: string[];
  indicators?: string[];
  uses_desk_pipeline?: boolean;
};

export type StrategiesResponse = {
  strategies: StrategyInfo[];
  default: string;
};

export type OptimizeMode = "local_score" | "ai_ensemble" | "majority_vote";

export type StrategyPackResult = {
  strategy_id: string;
  strategy_label: string;
  timeframe?: string;
  bias: Bias;
  entry?: number | null;
  stop_loss?: number | null;
  take_profit?: number | null;
  confidence?: number | null;
  reasoning?: string;
  fit_score?: number;
  trade_allowed?: boolean;
  pack_score?: number;
  analysis?: string;
  error?: string;
};

export type MultiAnalysis = {
  optimize_mode?: OptimizeMode | string;
  reason?: string;
  final_strategy_id?: string;
  packs?: StrategyPackResult[];
};

export type AnalyzeResponse = {
  symbol: string;
  exchange: string;
  timeframe: string;
  tv_symbol: string;
  strategy_id: string;
  strategy_label: string;
  market: Market;
  levels: TradeLevels;
  analysis: string;
  provider: string;
  optimize_mode?: OptimizeMode | string | null;
  final_strategy_id?: string | null;
  packs?: StrategyPackResult[] | null;
};

export type ChatMessage = { role: "user" | "assistant" | "system"; content: string };

export type ChatResponse = { symbol: string; reply: string; provider: string; strategy_id?: string };

export type HealthResponse = {
  status: string;
  app: string;
  ai_provider: string;
  ai_model: string | null;
  tradingview_ready: boolean;
};

export type InstrumentType = "crypto" | "stock" | "etf" | "commodity" | "fx" | "index" | "premarket";

export type SymbolResult = {
  symbol: string;
  exchange: string;
  tv_symbol: string;
  kind: string;
  label: string;
  /** From the instrument catalogue (WL-044); null when only the ticker is known. */
  name?: string | null;
  type?: InstrumentType | string;
  market?: string | null;
  aliases?: string;
};

/** Correlation and beta of the symbol's log returns to one benchmark (WL-036). */
export type CorrelationStat = {
  available: boolean;
  correlation?: number | null;
  beta?: number | null;
  overlap_pct?: number | null;
  samples?: number | null;
  error?: string | null;
};

export type CorrelationWindow = {
  interval: string;
  days: number;
  candles: number;
  btc: CorrelationStat;
  eth: CorrelationStat;
};

export type Correlation = {
  available: boolean;
  symbol?: string;
  market?: string | null;
  /** Keys: 30d_1h, 90d_1d. */
  windows?: Record<string, CorrelationWindow>;
  summary?: string | null;
  error?: string | null;
};

export type PulseTf = "1M" | "1w" | "1d" | "1h" | "15m";

export type PulseCell = {
  tf: PulseTf;
  available: boolean;
  price?: number | null;
  trend?: "up" | "down" | "flat" | null;
  rsi?: number | null;
  ema20?: number | null;
  ema50?: number | null;
  price_vs_ema20?: "above" | "below" | null;
  change_pct?: number | null;
  bias?: Bias | null;
  candle_open?: string | null;
  error?: string | null;
};

export type PulseSymbol = {
  symbol: string;
  available: boolean;
  price?: number | null;
  change_24h_pct?: number | null;
  error?: string | null;
  timeframes: PulseCell[];
};

export type PulseResponse = {
  symbols: PulseSymbol[];
  timeframes: string[];
  rule: string;
  generated_at: string;
};

export type CalendarKind = "macro" | "earnings" | "crypto" | "binance";

export type CalendarEvent = {
  id: number;
  source: string;
  kind: CalendarKind;
  title: string;
  /** ISO 8601 in PKT (+05:00). */
  starts_at: string;
  all_day: boolean;
  /** Earnings: before_open or after_close. */
  session?: string | null;
  impact?: "high" | "medium" | "low" | null;
  country?: string | null;
  ticker?: string | null;
  /** TradingView symbols Binance lists for the ticker, such as BINANCE:METAUSDT.P. */
  instrument_symbols: string[];
  forecast?: string | null;
  previous?: string | null;
  actual?: string | null;
  url?: string | null;
  fetched_at: string;
};

export type CalendarSource = {
  name: string;
  available?: boolean | null;
  error?: string | null;
  events?: number | null;
  fetched_at?: string | null;
};

export type CalendarResponse = { events: CalendarEvent[]; sources: CalendarSource[] };

export type JobStatus = {
  job: string;
  schedule: string;
  started_at?: string | null;
  finished_at?: string | null;
  exit_code?: number | null;
  message?: string | null;
  next_run?: string | null;
};

export type JobsResponse = { jobs: JobStatus[] };

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

export type SignalReview = {
  at: string;
  price: number | null;
  unrealized_r: number | null;
  dist_to_stop_r: number | null;
  dist_to_target_r: number | null;
  stance: "hold" | "caution" | "exit_early" | null;
  summary: string;
  verify_status?: string | null;
  revised_entry?: number | null;
  revised_stop_loss?: number | null;
  revised_take_profit?: number | null;
  levels_changed?: boolean;
  revise_reason?: string | null;
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
  confidence?: number | null;
  status: string;
  outcome?: string | null;
  r_multiple?: number | null;
  strategy_id?: string | null;
  notes?: string | null;
  live_review_json?: SignalReview[] | null;
  multi_analysis_json?: MultiAnalysis | null;
};

export type StrategyBucket = {
  id: string;
  label: string;
  n: number;
  open: number;
  wins: number;
  losses: number;
  expired: number;
  decided: number;
  hit_rate: number | null;
  avg_r: number | null;
  total_r: number;
  reliable: boolean;
};

export type SignalDashboard = {
  overall: StrategyBucket & { n: number };
  by_strategy: StrategyBucket[];
  best: string | null;
  worst: string | null;
  best_label: string | null;
  worst_label: string | null;
  min_reliable: number;
  equity_curve: {
    date: string;
    cumulative_r: number;
    cumulative_r_by_strategy: Record<string, number>;
  }[];
  volume_by_day: { date: string; count: number }[];
  outcomes_by_strategy: { id: string; label: string; wins: number; losses: number; expired: number }[];
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

type Pair = {
  symbol: string;
  exchange: string;
  timeframe: string;
  strategy_id?: string;
  optimize_mode?: OptimizeMode | string;
};

export const api = {
  health: () => request<HealthResponse>("/api/health"),
  strategies: () => request<StrategiesResponse>("/api/strategies"),
  analyze: (p: Pair) => request<AnalyzeResponse>("/api/analyze", { method: "POST", body: p }),
  chat: (p: Pair & { message: string; history: ChatMessage[] }) =>
    request<ChatResponse>("/api/chat", { method: "POST", body: p }),
  searchSymbols: (q: string, exchange: string) =>
    request<{ results: SymbolResult[] }>(
      `/api/symbols/search?q=${encodeURIComponent(q)}&exchange=${encodeURIComponent(exchange)}&limit=20`,
    ),
  pulse: () => request<PulseResponse>("/api/pulse"),
  calendar: (days: number, kind: CalendarKind | "") =>
    request<CalendarResponse>(`/api/calendar?days=${String(days)}&kind=${encodeURIComponent(kind)}`),
  jobs: () => request<JobsResponse>("/api/jobs"),
  scoreWatchlist: (timeframe: string) =>
    request<WatchlistResponse>(`/api/watchlist/score?timeframe=${encodeURIComponent(timeframe)}`),
  journal: () => request<{ entries: JournalEntry[]; stats: Stats }>("/api/journal?limit=100"),
  addJournal: (body: Record<string, unknown>) => request<JournalEntry>("/api/journal", { method: "POST", body }),
  closeJournal: (id: string, status: string, exit_price: number | null) =>
    request<JournalEntry>(`/api/journal/${encodeURIComponent(id)}/close`, { method: "POST", body: { status, exit_price } }),
  deleteJournal: (id: string) => request<{ ok: boolean }>(`/api/journal/${encodeURIComponent(id)}`, { method: "DELETE" }),
  signals: () => request<{ signals: Signal[]; stats: Stats }>("/api/signals?limit=100"),
  getSignal: (id: string) =>
    request<{ signal: Signal }>(`/api/signals/${encodeURIComponent(id)}`),
  signalDashboard: () => request<SignalDashboard>("/api/signals/dashboard"),
  verifySignals: () =>
    request<{ checked: number; updated: number; stats: Stats }>("/api/signals/verify?only_open=true&limit=50", {
      method: "POST",
    }),
  verifySignal: (id: string) =>
    request<{ signal: Signal; stats: Stats }>(`/api/signals/${encodeURIComponent(id)}/verify`, { method: "POST" }),
  reviewOpenSignals: () =>
    request<{ checked: number; updated: number; signals: Signal[]; stats: Stats }>(
      "/api/signals/review?only_open=true&limit=50",
      { method: "POST" },
    ),
  reviewSignal: (id: string) =>
    request<{ signal: Signal; review: SignalReview | null; stats: Stats; warning?: string | null }>(
      `/api/signals/${encodeURIComponent(id)}/review`,
      { method: "POST" },
    ),
};
