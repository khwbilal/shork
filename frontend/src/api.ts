export type TradeLevels = {
  bias: "Buy" | "Sell" | "Neutral";
  entry: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  confidence: number | null;
  reasoning: string;
};

export type ChatMessage = {
  role: "user" | "assistant" | "system";
  content: string;
};

export type AnalyzeResponse = {
  symbol: string;
  exchange: string;
  timeframe: string;
  tv_symbol: string;
  market: Record<string, unknown>;
  levels: TradeLevels;
  analysis: string;
  provider: string;
  disclaimer: string;
};

export type ChatResponse = {
  symbol: string;
  reply: string;
  market_snapshot: Record<string, unknown> | null;
  provider: string;
  disclaimer: string;
};

export type HealthResponse = {
  status: string;
  app: string;
  ai_provider: string;
  tradingview_ready: boolean;
};

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export function fetchHealth() {
  return fetch("/api/health").then((r) => parse<HealthResponse>(r));
}

export function analyzePair(body: {
  symbol: string;
  exchange: string;
  timeframe: string;
  custom_prompt?: string;
}) {
  return fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => parse<AnalyzeResponse>(r));
}

export function chatPair(body: {
  symbol: string;
  exchange: string;
  timeframe: string;
  message: string;
  history: ChatMessage[];
}) {
  return fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => parse<ChatResponse>(r));
}
