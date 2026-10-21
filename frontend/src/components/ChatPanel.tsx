import { useEffect, useRef, useState, type FormEvent } from "react";
import type { TradeLevels } from "../api";
import { fmtConf, fmtPx, rewardRisk, biasClass } from "../lib/format";
import Icon from "./Icon";
import { PROVIDER_LABEL } from "./Shell";
import { BiasPill, V } from "./ui";

export type UiMessage = {
  id: number;
  role: "user" | "assistant";
  text: string;
  levels?: TradeLevels;
  provider?: string;
  error?: boolean;
  thinking?: boolean;
  quiet?: boolean;
};

const SUGGESTIONS = [
  "Is this a long setup?",
  "Where is the invalidation?",
  "What would flip the bias?",
  "Summarise the risk",
];

/** Bold the leading `KEY:` of each line in the analyst's desk card. */
function AnalysisText({ text }: Readonly<{ text: string }>) {
  const lines = text.split("\n");
  return (
    <>
      {lines.map((line, i) => {
        const m = /^([A-Z][A-Z0-9/:&' ]{1,18}):(.*)$/.exec(line);
        const key = `${String(i)}-${line.slice(0, 12)}`;
        return (
          <span key={key}>
            {m ? (
              <>
                <strong>{m[1]}:</strong>
                {m[2]}
              </>
            ) : (
              line
            )}
            {i < lines.length - 1 ? "\n" : null}
          </span>
        );
      })}
    </>
  );
}

function TradeCard({ levels }: Readonly<{ levels: TradeLevels }>) {
  const rr = rewardRisk(levels.entry, levels.stop_loss, levels.take_profit);
  return (
    <div className={`trade-card ${biasClass(levels.bias)}`}>
      <div className="head">
        <BiasPill bias={levels.bias} />
        <span className="card-sub">Confidence {fmtConf(levels.confidence) ?? "—"}</span>
      </div>
      <div className="grid">
        <div>
          <span>Entry</span>
          <strong><V value={fmtPx(levels.entry)} /></strong>
        </div>
        <div>
          <span>Stop</span>
          <strong><V value={fmtPx(levels.stop_loss)} /></strong>
        </div>
        <div>
          <span>Target</span>
          <strong><V value={fmtPx(levels.take_profit)} /></strong>
        </div>
        <div>
          <span>Support</span>
          <strong><V value={fmtPx(levels.support)} /></strong>
        </div>
        <div>
          <span>Resistance</span>
          <strong><V value={fmtPx(levels.resistance)} /></strong>
        </div>
        <div>
          <span>R : R</span>
          <strong><V value={rr === null ? null : `${rr.toFixed(1)} : 1`} /></strong>
        </div>
      </div>
    </div>
  );
}

function Message({ m }: Readonly<{ m: UiMessage }>) {
  const who = m.role === "user" ? "You" : m.provider ? `Analyst · ${PROVIDER_LABEL[m.provider] ?? m.provider}` : "Analyst";
  return (
    <div className={`msg ${m.error ? "assistant error" : m.role}`}>
      {m.quiet ? null : <div className="who">{who}</div>}
      {m.levels ? <TradeCard levels={m.levels} /> : null}
      {m.thinking ? (
        <div className="bubble thinking">
          <span className="dots">
            <i />
            <i />
            <i />
          </span>
          {m.text}
        </div>
      ) : (
        <div className="bubble">{m.role === "assistant" ? <AnalysisText text={m.text} /> : m.text}</div>
      )}
    </div>
  );
}

export default function ChatPanel({
  symbol,
  messages,
  busy,
  onSend,
  onClear,
}: Readonly<{
  symbol: string;
  messages: UiMessage[];
  busy: boolean;
  onSend: (text: string) => void;
  onClear: () => void;
}>) {
  const [input, setInput] = useState("");
  const logRef = useRef<HTMLOutputElement>(null);
  const textRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  function autoGrow() {
    const t = textRef.current;
    if (!t) return;
    t.style.height = "auto";
    t.style.height = `${Math.min(t.scrollHeight, 140)}px`;
  }

  function submit(e?: FormEvent) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    requestAnimationFrame(autoGrow);
    onSend(text);
  }

  return (
    <aside className="card chat-card" aria-label="AI analyst chat">
      <div className="card-head">
        <h3>
          <Icon name="message" />
          Analyst
        </h3>
        <div className="right">
          <button className="link-btn" type="button" onClick={onClear}>
            Clear
          </button>
        </div>
      </div>
      <output className="chat-log" aria-live="polite" ref={logRef}>
        {messages.map((m) => (
          <Message key={m.id} m={m} />
        ))}
      </output>
      <form className="composer" onSubmit={submit}>
        <div className="suggestions">
          {SUGGESTIONS.map((s) => (
            <button key={s} type="button" disabled={busy} onClick={() => onSend(s)}>
              {s}
            </button>
          ))}
        </div>
        <div className="input-wrap">
          <textarea
            ref={textRef}
            rows={1}
            placeholder={`Ask about ${symbol}…`}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              autoGrow();
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) submit(e);
            }}
          />
          <button className="send-btn" type="submit" aria-label="Send" disabled={busy}>
            <Icon name="send" small />
          </button>
        </div>
      </form>
    </aside>
  );
}
