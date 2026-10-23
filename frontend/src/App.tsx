import Box from "@mui/material/Box";
import { useColorScheme } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useCallback, useEffect, useState } from "react";
import { api, type HealthResponse } from "./api";
import { FeedbackProvider } from "./components/feedback";
import { Rail, TopBar } from "./components/Shell";
import { PAGES, TIMEFRAMES, type PageKey } from "./lib/nav";
import { readPref, readRecents, rememberRecent, writePref } from "./lib/storage";
import CalendarPage from "./pages/Calendar";
import Dashboard from "./pages/Dashboard";
import Desk from "./pages/Desk";
import Journal from "./pages/Journal";
import SignalDetail from "./pages/SignalDetail";
import Signals from "./pages/Signals";
import Watchlist from "./pages/Watchlist";

function parseHash(): { page: PageKey; signalId: string | null } {
  const parts = window.location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const name = parts[0] ?? "desk";
  const page = name in PAGES ? (name as PageKey) : "desk";
  const signalId = page === "signals" && parts[1] ? parts[1] : null;
  return { page, signalId };
}

function initialTimeframe(): string {
  const tf = readPref("cca_tf");
  return tf && (TIMEFRAMES as readonly string[]).includes(tf) ? tf : "1h";
}

export default function App() {
  const recent = readRecents()[0];
  const initialHash = parseHash();
  const [page, setPage] = useState<PageKey>(initialHash.page);
  const [signalId, setSignalId] = useState<string | null>(initialHash.signalId);
  const [symbol, setSymbol] = useState(recent?.symbol ?? "SOLUSDT");
  const [exchange, setExchange] = useState(recent?.exchange ?? "BINANCE");
  const [tvSymbol, setTvSymbol] = useState(recent?.tv_symbol ?? "BINANCE:SOLUSDT");
  const [timeframe, setTimeframe] = useState(initialTimeframe);
  const [folded, setFolded] = useState(() => readPref("cca_rail_folded") === "1");
  const [navOpen, setNavOpen] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [journalOpen, setJournalOpen] = useState(0);
  const [signalsOpen, setSignalsOpen] = useState(0);
  const [journalVersion, setJournalVersion] = useState(0);
  const [signalsVersion, setSignalsVersion] = useState(0);

  const desktop = useMediaQuery((t) => t.breakpoints.up("md"), { noSsr: true });
  const { mode, systemMode } = useColorScheme();
  const dark = (mode === "system" ? systemMode : mode) === "dark";

  useEffect(() => {
    const onHash = () => {
      const h = parseHash();
      setPage(h.page);
      setSignalId(h.signalId);
      setNavOpen(false);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    api
      .health()
      .then((h) => setHealth(h))
      .catch(() => setHealthError(true));
  }, []);

  const pickPair = useCallback(
    (sym: string, ex?: string, tv?: string) => {
      const s = sym.trim().toUpperCase();
      if (!s) return;
      const e = (ex ?? exchange).toUpperCase();
      const t = (tv ?? `${e}:${s}`).toUpperCase();
      setSymbol(s);
      setExchange(e);
      setTvSymbol(t);
      rememberRecent({ symbol: s, exchange: e, tv_symbol: t });
    },
    [exchange],
  );

  const goTo = (p: PageKey) => {
    window.location.hash = `#/${p}`;
  };

  const goToSignal = (id: string) => {
    window.location.hash = `#/signals/${encodeURIComponent(id)}`;
  };

  const openOnDesk = (s: string, ex?: string, tv?: string) => {
    pickPair(s, ex, tv);
    goTo("desk");
  };

  const onJournalStats = useCallback((s: { open?: number }) => setJournalOpen(s.open ?? 0), []);
  const onSignalStats = useCallback((s: { open?: number }) => setSignalsOpen(s.open ?? 0), []);

  return (
    <FeedbackProvider>
      <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
        <Rail
          desktop={desktop}
          mobileOpen={navOpen}
          onCloseMobile={() => setNavOpen(false)}
          page={page}
          health={health}
          healthError={healthError}
          journalOpen={journalOpen}
          signalsOpen={signalsOpen}
          folded={folded}
          onToggleFold={() => {
            writePref("cca_rail_folded", folded ? "0" : "1");
            setFolded(!folded);
          }}
        />
        <Box sx={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
          <TopBar
            page={page}
            symbol={symbol}
            exchange={exchange}
            timeframe={timeframe}
            desktop={desktop}
            onMenu={() => setNavOpen(true)}
            onExchange={(ex) => pickPair(symbol, ex)}
            onTimeframe={(tf) => {
              writePref("cca_tf", tf);
              setTimeframe(tf);
            }}
            onPickPair={openOnDesk}
            onPickPage={goTo}
          />
          {/* Pages stay mounted so the desk keeps its plan and chat while you browse. */}
          <Box component="main" sx={{ p: { xs: 2, md: 3 }, minWidth: 0, flex: 1 }}>
            <Box hidden={page !== "desk"}>
              <Desk
                symbol={symbol}
                exchange={exchange}
                tvSymbol={tvSymbol}
                timeframe={timeframe}
                dark={dark}
                active={page === "desk"}
                onSignalRecorded={() => setSignalsVersion((v) => v + 1)}
                onJournalChanged={() => setJournalVersion((v) => v + 1)}
              />
            </Box>
            <Box hidden={page !== "dashboard"}>
              <Dashboard active={page === "dashboard"} version={signalsVersion} />
            </Box>
            <Box hidden={page !== "watchlist"}>
              <Watchlist timeframe={timeframe} onOpen={(s) => openOnDesk(s, "BINANCE")} />
            </Box>
            <Box hidden={page !== "calendar"}>
              <CalendarPage active={page === "calendar"} onOpenPair={openOnDesk} />
            </Box>
            <Box hidden={page !== "journal"}>
              <Journal active={page === "journal"} version={journalVersion} onStats={onJournalStats} />
            </Box>
            <Box hidden={page !== "signals"}>
              {signalId ? (
                <SignalDetail
                  signalId={signalId}
                  onBack={() => goTo("signals")}
                  onReviewed={() => setSignalsVersion((v) => v + 1)}
                />
              ) : (
                <Signals
                  active={page === "signals" && !signalId}
                  version={signalsVersion}
                  onStats={onSignalStats}
                  onOpenSignal={goToSignal}
                />
              )}
            </Box>
          </Box>
        </Box>
      </Box>
    </FeedbackProvider>
  );
}
