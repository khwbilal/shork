import { useCallback, useEffect, useState } from "react";
import { api, type HealthResponse } from "./api";
import { FeedbackProvider } from "./components/feedback";
import SearchPalette from "./components/SearchPalette";
import { PAGES, Rail, TIMEFRAMES, TopBar, type PageKey } from "./components/Shell";
import { readPref, readRecents, rememberRecent, writePref } from "./lib/storage";
import Desk from "./pages/Desk";
import Journal from "./pages/Journal";
import Signals from "./pages/Signals";
import Watchlist from "./pages/Watchlist";

function pageFromHash(): PageKey {
  const name = window.location.hash.replace(/^#\/?/, "").split("/")[0];
  return name in PAGES ? (name as PageKey) : "desk";
}

function systemDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function initialTimeframe(): string {
  const tf = readPref("cca_tf");
  return tf && (TIMEFRAMES as readonly string[]).includes(tf) ? tf : "1h";
}

export default function App() {
  const recent = readRecents()[0];
  const [page, setPage] = useState<PageKey>(pageFromHash);
  const [symbol, setSymbol] = useState(recent?.symbol ?? "SOLUSDT");
  const [exchange, setExchange] = useState(recent?.exchange ?? "BINANCE");
  const [tvSymbol, setTvSymbol] = useState(recent?.tv_symbol ?? "BINANCE:SOLUSDT");
  const [timeframe, setTimeframe] = useState(initialTimeframe);
  const [theme, setTheme] = useState<string | null>(() => readPref("cca_theme"));
  const [prefersDark, setPrefersDark] = useState(systemDark);
  const [folded, setFolded] = useState(() => readPref("cca_rail_folded") === "1");
  const [navOpen, setNavOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [journalOpen, setJournalOpen] = useState(0);
  const [signalsOpen, setSignalsOpen] = useState(0);
  const [journalVersion, setJournalVersion] = useState(0);
  const [signalsVersion, setSignalsVersion] = useState(0);

  const dark = theme === "dark" || (theme !== "light" && prefersDark);

  useEffect(() => {
    if (theme === "light" || theme === "dark") document.documentElement.dataset.theme = theme;
    else delete document.documentElement.dataset.theme;
  }, [theme]);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setPrefersDark(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    const onHash = () => {
      setPage(pageFromHash());
      setNavOpen(false);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
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

  const onJournalStats = useCallback((s: { open?: number }) => setJournalOpen(s.open ?? 0), []);
  const onSignalStats = useCallback((s: { open?: number }) => setSignalsOpen(s.open ?? 0), []);

  return (
    <FeedbackProvider>
      <div className={`shell${folded ? " folded" : ""}${navOpen ? " nav-open" : ""}`}>
        <Rail
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
        <div className="scrim" onClick={() => setNavOpen(false)} />
        <div className="main">
          <TopBar
            page={page}
            symbol={symbol}
            exchange={exchange}
            timeframe={timeframe}
            dark={dark}
            onMenu={() => setNavOpen(true)}
            onSearch={() => setPaletteOpen(true)}
            onExchange={(ex) => pickPair(symbol, ex)}
            onTimeframe={(tf) => {
              writePref("cca_tf", tf);
              setTimeframe(tf);
            }}
            onToggleTheme={() => {
              const next = dark ? "light" : "dark";
              writePref("cca_theme", next);
              setTheme(next);
            }}
          />
          {/* Pages stay mounted so the desk keeps its plan and chat while you browse. */}
          <section className="page" hidden={page !== "desk"}>
            <Desk
              symbol={symbol}
              exchange={exchange}
              tvSymbol={tvSymbol}
              timeframe={timeframe}
              dark={dark}
              onSignalRecorded={() => setSignalsVersion((v) => v + 1)}
              onJournalChanged={() => setJournalVersion((v) => v + 1)}
            />
          </section>
          <section className="page" hidden={page !== "watchlist"}>
            <Watchlist
              timeframe={timeframe}
              onOpen={(s) => {
                pickPair(s, "BINANCE");
                goTo("desk");
              }}
            />
          </section>
          <section className="page" hidden={page !== "journal"}>
            <Journal active={page === "journal"} version={journalVersion} onStats={onJournalStats} />
          </section>
          <section className="page" hidden={page !== "signals"}>
            <Signals active={page === "signals"} version={signalsVersion} onStats={onSignalStats} />
          </section>
        </div>
      </div>
      {paletteOpen ? (
        <SearchPalette
          exchange={exchange}
          onClose={() => setPaletteOpen(false)}
          onPickPair={(s, ex, tv) => {
            pickPair(s, ex, tv);
            goTo("desk");
          }}
          onPickPage={goTo}
        />
      ) : null}
    </FeedbackProvider>
  );
}
