import { Fragment, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { readRecents } from "../lib/storage";
import Icon from "./Icon";
import { EmptyState } from "./ui";
import { PAGES, type PageKey } from "./Shell";

type Item =
  | { kind: "pair"; group: string; symbol: string; exchange: string; tv: string; label: string }
  | { kind: "page"; group: string; key: PageKey; label: string };

function defaultItems(): Item[] {
  const recent: Item[] = readRecents().map((r) => ({
    kind: "pair",
    group: "Recent",
    symbol: r.symbol,
    exchange: r.exchange,
    tv: r.tv_symbol,
    label: r.exchange,
  }));
  const pages: Item[] = (Object.keys(PAGES) as PageKey[]).map((key) => ({
    kind: "page",
    group: "Go to",
    key,
    label: PAGES[key],
  }));
  return [...recent, ...pages];
}

export default function SearchPalette({
  exchange,
  onClose,
  onPickPair,
  onPickPage,
}: Readonly<{
  exchange: string;
  onClose: () => void;
  onPickPair: (symbol: string, exchange?: string, tv?: string) => void;
  onPickPage: (page: PageKey) => void;
}>) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<Item[]>(defaultItems);
  const [index, setIndex] = useState(0);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!query.trim()) {
      setItems(defaultItems());
      setStatus("idle");
      setIndex(0);
      return;
    }
    let cancelled = false;
    setStatus("loading");
    const timer = setTimeout(() => {
      api
        .searchSymbols(query, exchange)
        .then((res) => {
          if (cancelled) return;
          setItems(
            res.results.map((r) => ({
              kind: "pair",
              group: "Pairs",
              symbol: r.symbol,
              exchange: r.exchange,
              tv: r.tv_symbol,
              label: r.label,
            })),
          );
          setIndex(0);
          setStatus("idle");
        })
        .catch(() => {
          if (!cancelled) setStatus("error");
        });
    }, 160);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, exchange]);

  useEffect(() => {
    listRef.current?.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: "nearest" });
  }, [index]);

  function choose(i: number) {
    const it = items[i];
    onClose();
    if (!it) {
      if (query.trim()) onPickPair(query.trim());
      return;
    }
    if (it.kind === "page") onPickPage(it.key);
    else onPickPair(it.symbol, it.exchange, it.tv);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    const n = items.length;
    if (e.key === "ArrowDown" && n) {
      e.preventDefault();
      setIndex((i) => (i + 1) % n);
    } else if (e.key === "ArrowUp" && n) {
      e.preventDefault();
      setIndex((i) => (i - 1 + n) % n);
    } else if (e.key === "Enter") {
      e.preventDefault();
      choose(n ? index : -1);
    } else if (e.key === "Escape") {
      onClose();
    }
  }

  let body: React.ReactNode;
  if (status === "loading" && query.trim()) {
    body = <EmptyState text="Searching… the first search loads the Binance pair list." icon="search" />;
  } else if (status === "error") {
    body = <EmptyState text="Search is unavailable — is the backend running?" icon="search" />;
  } else if (!items.length) {
    body = <EmptyState text="No matches — try BTC, ZEC or SOLUSDT.P" icon="search" />;
  } else {
    body = items.map((it, i) => (
      <Fragment key={it.kind === "page" ? `page-${it.key}` : `${it.group}-${it.tv}`}>
        {i === 0 || items[i - 1].group !== it.group ? <div className="group">{it.group}</div> : null}
        <button
          type="button"
          className="palette-item"
          role="option"
          aria-selected={i === index}
          onMouseEnter={() => setIndex(i)}
          onClick={() => choose(i)}
        >
          {it.kind === "page" ? (
            <>
              <Icon name="arrowRight" small />
              <strong>{it.label}</strong>
            </>
          ) : (
            <>
              <strong>{it.symbol}</strong>
              <span>{it.label}</span>
              <span className="chip tag">{it.exchange}</span>
            </>
          )}
        </button>
      </Fragment>
    ));
  }

  return (
    <div
      className="overlay"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="palette" role="dialog" aria-modal="true" aria-label="Search pairs">
        <div className="palette-input">
          <Icon name="search" />
          <input
            autoFocus
            autoComplete="off"
            spellCheck={false}
            placeholder="Search a pair — BTC, ZEC, SOLUSDT.P…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
          />
          <kbd>Esc</kbd>
        </div>
        <div className="palette-list" role="listbox" ref={listRef}>
          {body}
        </div>
        <div className="palette-foot">
          <span>
            <kbd>↑</kbd> <kbd>↓</kbd> move
          </span>
          <span>
            <kbd>↵</kbd> open
          </span>
          <span>
            <kbd>Esc</kbd> close
          </span>
        </div>
      </div>
    </div>
  );
}
