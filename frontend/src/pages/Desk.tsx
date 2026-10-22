import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import AutoAwesome from "@mui/icons-material/AutoAwesome";
import BookmarkAddOutlined from "@mui/icons-material/BookmarkAddOutlined";
import { useEffect, useRef, useState } from "react";
import { api, type ChatMessage, type Market, type TradeLevels } from "../api";
import ChatPanel, { type UiMessage } from "../components/ChatPanel";
import { ConfluenceCard, CorrelationCard, FlowCard, LevelsBoard, LiquidityCard, SetupCard } from "../components/DeskCards";
import { useFeedback } from "../components/feedback";
import PulseStrip from "../components/PulseStrip";
import TradingViewChart from "../components/TradingViewChart";
import { ActionButton, KpiStrip, Na, PageHeader, V, type KpiTile } from "../components/ui";
import { GLYPH, biasClass, currentPrice, fmtConf, fmtPct, fmtPx, fmtSigned, humanize, isNum, rewardRisk } from "../lib/format";

const RUN_HINT = "Run a full analysis";
const GREETING =
  "Pick a pair with Ctrl K, then run a full analysis. I'll pull TradingView and Binance context, score it, and give you a plan with entry, stop and target. Ask follow-ups below.";

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
  const or = (v: string | null | undefined) => v ?? <Na />;
  return [
    { label: "Bias", tone: cls, value: `${GLYPH[cls]} ${levels.bias || "Neutral"}`, note: <>Trend {or(levels.trend)}</> },
    {
      label: "Confluence",
      tone: biasClass(conf.bias),
      value: <V value={fmtSigned(conf.score)} />,
      unit: "/ 10",
      note: <>Prefers {or(conf.bias)}</>,
    },
    {
      label: "Setup",
      tone: "text",
      value: setup.type ? humanize(setup.type) : <Na />,
      note: setup.trade_allowed === false ? "Blocked by chop filter" : "Trade allowed",
    },
    {
      label: "Entry",
      value: <V value={fmtPx(levels.entry)} />,
      note: (
        <>
          SL {or(fmtPx(levels.stop_loss))} · TP {or(fmtPx(levels.take_profit))}
        </>
      ),
    },
    {
      label: "Reward : risk",
      value: rr === null ? <Na reason="Needs entry, stop and target" /> : rr.toFixed(1),
      unit: rr === null ? undefined : ": 1",
      note: <>Confidence {or(fmtConf(levels.confidence))}</>,
    },
    {
      label: "Price",
      value: <V value={fmtPx(currentPrice(market))} />,
      note: <>24h {or(fmtPct(market.flow?.price_change_24h_pct ?? market.yahoo_price?.change_pct, 2))}</>,
    },
  ];
}

function subtitle(exchange: string, timeframe: string, market: Market | null): string {
  if (!market) return `${exchange} · ${timeframe} · run a full analysis to score this pair.`;
  const parts = [`${exchange} · ${timeframe}`];
  const conf = market.confluence;
  if (isNum(conf?.score)) parts.push(`confluence ${fmtSigned(conf.score) ?? ""} / 10`);
  if (market.setup?.type) {
    parts.push(`${humanize(market.setup.type)}${market.setup.trade_allowed === false ? " (no trade)" : ""}`);
  }
  return parts.join(" · ");
}

export default function Desk({
  symbol,
  exchange,
  tvSymbol,
  timeframe,
  dark,
  active,
  onSignalRecorded,
  onJournalChanged,
}: Readonly<{
  symbol: string;
  exchange: string;
  tvSymbol: string;
  timeframe: string;
  dark: boolean;
  active: boolean;
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
      if (res.provider === "offline") toast("No AI selected, so this is the deterministic plan only. Restart and pick one.");
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
    <Stack spacing={2}>
      <PageHeader
        title={symbol}
        subtitle={subtitle(exchange, timeframe, market)}
        actions={
          <>
            <ActionButton icon={<BookmarkAddOutlined />} disabled={!levels} onClick={() => void logToJournal()}>
              Log to journal
            </ActionButton>
            <ActionButton icon={<AutoAwesome />} primary busy={busy} busyLabel="Analysing…" onClick={() => void runAnalyze()}>
              Full analysis
            </ActionButton>
          </>
        }
      />

      <PulseStrip active={active} />

      <KpiStrip tiles={deskKpis(levels, market)} />

      <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "minmax(0, 1fr)", lg: "minmax(0, 1fr) 380px" }, alignItems: "start" }}>
        <Stack spacing={2} sx={{ minWidth: 0 }}>
          <Card sx={{ minWidth: 0 }}>
            <Stack direction="row" spacing={1} sx={{ alignItems: "center", px: 2, minHeight: 48, borderBottom: 1, borderColor: "divider" }}>
              <Typography variant="h3" component="h3" noWrap sx={{ flex: 1, minWidth: 0, fontFamily: (t) => t.typography.fontFamilyMono }}>
                {tvSymbol}
              </Typography>
              {source ? (
                <Typography variant="caption" noWrap sx={{ color: "text.secondary" }}>
                  Data: {source}
                </Typography>
              ) : null}
            </Stack>
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "minmax(0, 1fr) 220px" } }}>
              <TradingViewChart tvSymbol={tvSymbol} timeframe={timeframe} dark={dark} />
              <Box sx={{ p: 1.5, borderLeft: { md: 1 }, borderTop: { xs: 1, md: 0 }, borderColor: "divider", minWidth: 0 }}>
                <LevelsBoard levels={levels} market={market} />
              </Box>
            </Box>
          </Card>
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "repeat(2, minmax(0, 1fr))" } }}>
            <ConfluenceCard market={market} />
            <SetupCard market={market} />
            <FlowCard market={market} />
            <LiquidityCard market={market} />
          </Box>
          <CorrelationCard market={market} />
        </Stack>
        <ChatPanel
          symbol={symbol}
          messages={messages}
          busy={busy}
          onSend={(t) => void runChat(t)}
          onClear={() => {
            setHistory([]);
            setMessages([{ id: nextId.current++, role: "assistant", text: GREETING }]);
          }}
        />
      </Box>
    </Stack>
  );
}
