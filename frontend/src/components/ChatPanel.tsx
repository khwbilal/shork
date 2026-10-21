import { FormEvent, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  ChatMessage,
  TradeLevels,
  analyzePair,
  chatPair,
} from "../api";

type Props = {
  symbol: string;
  exchange: string;
  timeframe: string;
  onLevels: (levels: TradeLevels | null) => void;
  providerLabel: string;
};

type UiMessage = {
  role: "user" | "assistant";
  content: string;
};

function formatAnalysis(analysis: string, _levels: TradeLevels) {
  return analysis;
}

export default function ChatPanel({
  symbol,
  exchange,
  timeframe,
  onLevels,
  providerLabel,
}: Props) {
  const [messages, setMessages] = useState<UiMessage[]>([
    {
      role: "assistant",
      content:
        "Pick a pair (e.g. SOLUSDT), then ask anything — or hit **Full analysis** for a gptchart-style bias / entry / SL / TP readout.",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function runAnalyze() {
    setBusy(true);
    setMessages((m) => [
      ...m,
      { role: "user", content: `Full analysis for ${exchange}:${symbol} (${timeframe})` },
    ]);
    try {
      const res = await analyzePair({ symbol, exchange, timeframe });
      onLevels(res.levels);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: formatAnalysis(res.analysis, res.levels),
        },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: `Error: ${err instanceof Error ? err.message : String(err)}`,
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", content: text }]);

    const history: ChatMessage[] = messages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .slice(-8)
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      const res = await chatPair({
        symbol,
        exchange,
        timeframe,
        message: text,
        history,
      });
      setMessages((m) => [...m, { role: "assistant", content: res.reply }]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: `Error: ${err instanceof Error ? err.message : String(err)}`,
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chat-pane">
      <div className="chat-header">
        <h2>AI analysis chat</h2>
        <p>
          Live TradingView technical context is injected on every message for{" "}
          <strong>
            {exchange}:{symbol}
          </strong>
          .
        </p>
        <div className="status">Provider: {providerLabel}</div>
      </div>

      <div className="messages">
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            <div className="who">{m.role === "user" ? "YOU" : "ANALYST"}</div>
            {m.role === "assistant" ? (
              <div className="markdown">
                <ReactMarkdown>{m.content}</ReactMarkdown>
              </div>
            ) : (
              m.content
            )}
          </div>
        ))}
        {busy && (
          <div className="bubble assistant">
            <div className="who">ANALYST</div>
            Fetching market data and thinking…
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form className="composer" onSubmit={onSubmit}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={`Ask about ${symbol}… e.g. "Is this a long setup on ${timeframe}?"`}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void onSubmit(e);
            }
          }}
        />
        <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
          <button className="btn" type="submit" disabled={busy || !input.trim()}>
            Send
          </button>
          <button
            className="btn ghost"
            type="button"
            disabled={busy}
            onClick={() => void runAnalyze()}
          >
            Full analysis
          </button>
        </div>
      </form>
      <div className="disclaimer">
        Not financial advice. Outputs are educational / informational only. Trading
        involves substantial risk of loss.
      </div>
    </div>
  );
}
