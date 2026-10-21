import { useEffect, useMemo, useState } from "react";
import { TradeLevels, fetchHealth } from "./api";
import ChatPanel from "./components/ChatPanel";
import TradingViewChart from "./components/TradingViewChart";

const TIMEFRAMES = ["15m", "1h", "4h", "1D"] as const;
const EXCHANGES = ["BINANCE", "KUCOIN", "BYBIT", "MEXC"] as const;

function formatLevel(n: number | null | undefined) {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toLocaleString(undefined, { maximumFractionDigits: 6 });
}

export default function App() {
  const [symbol, setSymbol] = useState("SOLUSDT");
  const [exchange, setExchange] = useState<string>("BINANCE");
  const [timeframe, setTimeframe] = useState<string>("1h");
  const [levels, setLevels] = useState<TradeLevels | null>(null);
  const [provider, setProvider] = useState("checking…");
  const [tvReady, setTvReady] = useState<boolean | null>(null);

  const tvSymbol = useMemo(
    () => `${exchange}:${symbol.replace(/[^A-Za-z0-9]/g, "").toUpperCase()}`,
    [exchange, symbol],
  );

  useEffect(() => {
    fetchHealth()
      .then((h) => {
        setProvider(h.ai_provider);
        setTvReady(h.tradingview_ready);
      })
      .catch(() => {
        setProvider("backend offline");
        setTvReady(false);
      });
  }, []);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <strong>Crypto Chart AI</strong>
          <span>TradingView data → Cursor/OpenAI analysis · local gptchart-style desk</span>
        </div>
        <div className="controls">
          <input
            className="symbol"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            aria-label="Symbol"
            placeholder="SOLUSDT"
          />
          <select
            value={exchange}
            onChange={(e) => setExchange(e.target.value)}
            aria-label="Exchange"
          >
            {EXCHANGES.map((ex) => (
              <option key={ex} value={ex}>
                {ex}
              </option>
            ))}
          </select>
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            aria-label="Timeframe"
          >
            {TIMEFRAMES.map((tf) => (
              <option key={tf} value={tf}>
                {tf}
              </option>
            ))}
          </select>
        </div>
      </header>

      <main className="workspace">
        <section className="chart-pane">
          <div className="meta">
            <span>{tvSymbol}</span>
            <div className="levels">
              <span className={`pill ${(levels?.bias ?? "neutral").toLowerCase()}`}>
                Bias {levels?.bias ?? "—"}
              </span>
              <span className="pill">Entry {formatLevel(levels?.entry)}</span>
              <span className="pill">SL {formatLevel(levels?.stop_loss)}</span>
              <span className="pill">TP {formatLevel(levels?.take_profit)}</span>
            </div>
            <span style={{ marginLeft: "auto", opacity: 0.7 }}>
              TV lib {tvReady == null ? "…" : tvReady ? "ready" : "missing"}
            </span>
          </div>
          <TradingViewChart tvSymbol={tvSymbol} interval={timeframe} />
        </section>

        <ChatPanel
          symbol={symbol}
          exchange={exchange}
          timeframe={timeframe}
          onLevels={setLevels}
          providerLabel={provider}
        />
      </main>
    </div>
  );
}
