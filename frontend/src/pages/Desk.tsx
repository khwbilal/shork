import { useEffect, useRef, useState } from "react";
import { api, type ChatMessage, type Market, type TradeLevels } from "../api";
import ChatPanel, { type UiMessage } from "../components/ChatPanel";
import { ConfluenceCard, FlowCard, LevelsBoard, LiquidityCard, SetupCard } from "../components/DeskCards";
import { useFeedback } from "../components/feedback";
import TradingViewChart from "../components/TradingViewChart";
import { Button, KpiStrip, Na, V, type KpiTile } from "../components/ui";
import { GLYPH, biasClass, currentPrice, fmtConf, fmtPct, fmtPx, fmtSigned, humanize, isNum, rewardRisk } from "../lib/format";

const RUN_HINT = "Run a full analysis";
const GREETING =
  "Pick a pair with Ctrl K, then run a full analysis. I'll pull TradingView + Binance context, score it, and give you a plan with entry, stop and target. Ask follow-ups below.";

const DATA_SOURCE: Record<string, string> = { binance_local: "Binance (local TA)", tradingview: "TradingView TA" };

function deskKpis(levels: TradeLevels | null, market: Market | null): KpiTile[] {
  if (!levels || !market) {
    return [
      { label: "Bias", value: <Na reason={RUN_HINT} />, note: RUN_HINT },
      { label: "Confluence", value: <Na reason={RUN_HINT} />, note: "Score −10 to +10" },
      { label: "Setup", value: <Na reason={RUN_HINT} />, note: "Chop filter" },
      { label: "Entry", value: <Na reason={RUN_HINT} />, note: "Stop · Target" },
      { label: "Reward : risk", value: <Na reason={RUN_HINT} />, note: "Confidence" },
      { label: "Price", value: <Na reason={RUN_HINT} />, note: "24h change" },
    ];
  }
  const conf = market.confluence ?? {};
  const setup = market.setup ?? {};
  const rr = rewardRisk(levels.entry, levels.stop_loss, levels.take_profit);
  const cls = biasClass(levels.bias);
  return [
    { label: "Bias", cls, value: `${GLYPH[cls]} ${levels.bias || "Neutral"}`, note: `Trend ${levels.trend ?? "—"}` },
    {
      label: "Confluence",
      cls: biasClass(conf.bias),
      value: <V value={fmtSigned(conf.score)} />,
      unit: "/ 10",
      note: `Prefers ${conf.bias ?? "—"}`,
    },
    {
      label: "Setup",
      cls: "text",
      value: setup.type ? humanize(setup.type) : <Na />,
      note: setup.trade_allowed === false ? "Blocked by chop filter" : "Trade allowed",
    },
    {
      label: "Entry",
      value: <V value={fmtPx(levels.entry)} />,
      note: `SL ${fmtPx(levels.stop_loss) ?? "—"} · TP ${fmtPx(levels.take_profit) ?? "—"}`,
    },
    {
      label: "Reward : risk",
      value: rr === null ? <Na reason="Needs entry, stop and target" /> : rr.toFixed(1),
      unit: rr === null ? undefined : ": 1",
      note: `Confidence ${fmtConf(levels.confidence) ?? "—"}`,
    },
    {
      label: "Price",
      value: <V value={fmtPx(currentPrice(market))} />,
      note: `24h ${fmtPct(market.flow?.price_change_24h_pct ?? market.yahoo_price?.change_pct, 2) ?? "—"}`,
    },
  ];
}

function subtitle(exchange: string, timeframe: string, market: Market | null): string {
  if (!market) return `${exchange} · ${timeframe} — run a full analysis to score this pair.`;
  const parts = [`${exchange} · ${timeframe}`];
  const conf = market.confluence;
  if (isNum(conf?.score)) parts.push(`confluence ${fmtSigned(conf.score) ?? ""} / 10`);
  if (market.setup?.type) {
    parts.push(`${humanize(market.setup.type)}${market.setup.trade_allowed === false ? " (no trade)" : ""}`);
  }
  return parts.join(" — ");
}

export default function Desk({
  symbol,
  exchange,
  tvSymbol,
  timeframe,
  dark,
  onSignalRecorded,
  onJournalChanged,
}: Readonly<{
  symbol: string;
  exchange: string;
  tvSymbol: string;
  timeframe: string;
  dark: boolean;
  onSignalRecorded: () => void;
  onJournalChanged: () => void;
}>) {
  const { toast } = useFeedback();
  const [levels, setLevels] = useState<TradeLevels | null>(null);
  const [market, setMarket] = useState<Market | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([{ id: 0, role: "assistant", text: GREETING }]);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const nextId = useRef(1);
  const firstRender = useRef(true);

  const push = (m: Omit<UiMessage, "id">): number => {
    const id = nextId.current++;
    setMessages((list) => [...list, { ...m, id }]);
    return id;
  };
  const drop = (id: number) => setMessages((list) => list.filter((m) => m.id !== id));

  // A plan belongs to one pair and timeframe; clear it when either changes.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    setLevels(null);
    setMarket(null);
    setHistory([]);
    push({ role: "assistant", text: `Switched to ${exchange}:${symbol} · ${timeframe}.`, quiet: true });
  }, [symbol, exchange, timeframe]);

  async function runAnalyze() {
    if (busy) return;
    setBusy(true);
    push({ role: "user", text: `Full analysis for ${exchange}:${symbol} (${timeframe})` });
    const pending = push({ role: "assistant", text: "Pulling market data and thinking…", thinking: true });
    try {
      const res = await api.analyze({ symbol, exchange, timeframe });
      drop(pending);
      setLevels(res.levels);
      setMarket(res.market);
      push({ role: "assistant", text: res.analysis, levels: res.levels, provider: res.provider });
      setHistory((h) => [
        ...h,
        { role: "user", content: `Full analysis for ${exchange}:${symbol}` },
        { role: "assistant", content: res.analysis },
      ]);
      if (res.provider === "offline") toast("No AI selected — showing the deterministic plan only. Restart and pick one.");
      if (res.market.recorded_signal_id) {
        toast("Signal archived for later verification.");
        onSignalRecorded();
      }
    } catch (err) {
      drop(pending);
      push({ role: "assistant", text: `Error: ${(err as Error).message}`, error: true });
    } finally {
      setBusy(false);
    }
  }

  async function runChat(message: string) {
    if (busy) return;
    setBusy(true);
    push({ role: "user", text: message });
    const pending = push({ role: "assistant", text: "Thinking…", thinking: true });
    try {
      const res = await api.chat({ symbol, exchange, timeframe, message, history: history.slice(-8) });
      drop(pending);
      push({ role: "assistant", text: res.reply, provider: res.provider });
      setHistory((h) => [...h, { role: "user", content: message }, { role: "assistant", content: res.reply }]);
    } catch (err) {
      drop(pending);
      push({ role: "assistant", text: `Error: ${(err as Error).message}`, error: true });
    } finally {
      setBusy(false);
    }
  }

  async function logToJournal() {
    if (!levels) return;
    const side = levels.bias === "Sell" ? "Sell" : "Buy";
    try {
      await api.addJournal({
        symbol,
        timeframe,
        side,
        setup: market?.setup?.type ?? null,
        entry: levels.entry,
        stop_loss: levels.stop_loss,
        take_profit: levels.take_profit,
        confluence: market?.confluence?.score ?? null,
        notes: levels.reasoning,
      });
      toast(`Logged ${symbol} ${side} to the journal.`);
      onJournalChanged();
    } catch (err) {
      toast(`Journal error: ${(err as Error).message}`);
    }
  }

  const source = market?.data_source ? (DATA_SOURCE[market.data_source] ?? market.data_source) : "";

  return (
    <>
      <div className="page-header">
        <div>
          <h2>{symbol}</h2>
          <p>{subtitle(exchange, timeframe, market)}</p>
        </div>
        <div className="actions">
          <Button icon="bookPlus" disabled={!levels} onClick={logToJournal}>
            Log to journal
          </Button>
          <Button icon="sparkles" primary busy={busy} busyLabel="Analysing…" onClick={runAnalyze}>
            Full analysis
          </Button>
        </div>
      </div>

      <KpiStrip tiles={deskKpis(levels, market)} />

      <div className="desk-grid">
        <div className="desk-left">
          <div className="card chart-card">
            <div className="card-head">
              <h3>{tvSymbol}</h3>
              <div className="right">
                <span className="card-sub">{source ? `Data: ${source}` : ""}</span>
              </div>
            </div>
            <div className="card-body">
              <TradingViewChart tvSymbol={tvSymbol} timeframe={timeframe} dark={dark} />
              <LevelsBoard levels={levels} market={market} />
            </div>
          </div>
          <div className="insight-grid">
            <ConfluenceCard market={market} />
            <SetupCard market={market} />
            <FlowCard market={market} />
            <LiquidityCard market={market} />
          </div>
        </div>
        <ChatPanel
          symbol={symbol}
          messages={messages}
          busy={busy}
          onSend={runChat}
          onClear={() => {
            setHistory([]);
            setMessages([{ id: nextId.current++, role: "assistant", text: GREETING }]);
          }}
        />
      </div>
    </>
  );
}
