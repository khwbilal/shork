import type { HealthResponse } from "../api";
import Icon, { type IconName } from "./Icon";

export const PAGES = { desk: "Desk", watchlist: "Watchlist", journal: "Journal", signals: "Signals" } as const;
export type PageKey = keyof typeof PAGES;

export const TIMEFRAMES = ["15m", "1h", "4h", "1D"] as const;
const EXCHANGES = ["BINANCE", "KUCOIN", "BYBIT", "MEXC"] as const;

export const PROVIDER_LABEL: Record<string, string> = {
  claude: "Claude API",
  claude_code: "Claude subscription",
  cursor: "Cursor",
  openai: "OpenAI",
  offline: "No AI",
  none: "No AI",
};

function NavItem({
  page,
  icon,
  current,
  count,
}: Readonly<{ page: PageKey; icon: IconName; current: PageKey; count?: number }>) {
  return (
    <a
      className="nav-item"
      href={`#/${page}`}
      title={PAGES[page]}
      aria-current={current === page ? "page" : undefined}
    >
      <Icon name={icon} />
      <span className="label">{PAGES[page]}</span>
      {count ? <span className="count">{count}</span> : null}
    </a>
  );
}

export function Rail({
  page,
  health,
  healthError,
  journalOpen,
  signalsOpen,
  onToggleFold,
  folded,
}: Readonly<{
  page: PageKey;
  health: HealthResponse | null;
  healthError: boolean;
  journalOpen: number;
  signalsOpen: number;
  folded: boolean;
  onToggleFold: () => void;
}>) {
  const on = Boolean(health && health.ai_provider !== "none");
  let name = "Checking…";
  let detail = "—";
  if (healthError) {
    name = "Backend offline";
    detail = "Start the API on :8000";
  } else if (health) {
    name = PROVIDER_LABEL[health.ai_provider] ?? health.ai_provider;
    detail = on ? (health.ai_model ?? "") : "Pick one in start.ps1 / start.sh";
  }
  let chipState = "";
  if (healthError || (health && !on)) chipState = "off";
  else if (on) chipState = "on";

  return (
    <aside className="rail" aria-label="Main navigation">
      <div className="rail-logo">
        <div className="logo-mark">
          <Icon name="activity" />
        </div>
        <div className="logo-text">
          <strong>Chart AI</strong>
          <span>Crypto analysis desk</span>
        </div>
      </div>
      <nav className="rail-nav">
        <NavItem page="desk" icon="chart" current={page} />
        <NavItem page="watchlist" icon="list" current={page} />
        <h4>Track record</h4>
        <NavItem page="journal" icon="book" current={page} count={journalOpen} />
        <NavItem page="signals" icon="target" current={page} count={signalsOpen} />
      </nav>
      <div className="rail-foot">
        <div className={`provider-chip ${chipState}`} title={`AI: ${name}${health?.ai_model ? ` (${health.ai_model})` : ""}`}>
          <span className="dot" />
          <div>
            <strong>{name}</strong>
            <span>{detail}</span>
          </div>
        </div>
        <button
          className="rail-toggle"
          type="button"
          aria-label={folded ? "Expand navigation" : "Collapse navigation"}
          onClick={onToggleFold}
        >
          <Icon name="chevronsLeft" />
        </button>
      </div>
    </aside>
  );
}

export function TopBar({
  page,
  symbol,
  exchange,
  timeframe,
  dark,
  onMenu,
  onSearch,
  onExchange,
  onTimeframe,
  onToggleTheme,
}: Readonly<{
  page: PageKey;
  symbol: string;
  exchange: string;
  timeframe: string;
  dark: boolean;
  onMenu: () => void;
  onSearch: () => void;
  onExchange: (ex: string) => void;
  onTimeframe: (tf: string) => void;
  onToggleTheme: () => void;
}>) {
  return (
    <header className="topbar">
      <button className="icon-btn menu-btn" type="button" aria-label="Open navigation" onClick={onMenu}>
        <Icon name="menu" />
      </button>
      <h1>{PAGES[page]}</h1>
      <div className="scope">
        <button className="scope-pair" type="button" title="Change pair" onClick={onSearch}>
          <span>{symbol}</span>
          <Icon name="chevronDown" small />
        </button>
        <select className="select" aria-label="Exchange" value={exchange} onChange={(e) => onExchange(e.target.value)}>
          {EXCHANGES.map((ex) => (
            <option key={ex}>{ex}</option>
          ))}
        </select>
        <div className="segmented" role="group" aria-label="Timeframe">
          {TIMEFRAMES.map((tf) => (
            <button key={tf} type="button" aria-pressed={tf === timeframe} onClick={() => onTimeframe(tf)}>
              {tf}
            </button>
          ))}
        </div>
      </div>
      <div className="topbar-spacer" />
      <button className="search-trigger" type="button" onClick={onSearch}>
        <Icon name="search" small />
        <span>Search pairs…</span>
        <kbd>Ctrl K</kbd>
      </button>
      <button
        className="icon-btn"
        type="button"
        aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
        onClick={onToggleTheme}
      >
        <Icon name={dark ? "sun" : "moon"} />
      </button>
    </header>
  );
}
