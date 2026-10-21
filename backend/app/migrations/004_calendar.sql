-- 004: calendar events and source status (WL-039, WL-045 earnings part).
-- starts_at is ISO 8601 in PKT (+05:00) so text order is time order.
-- ticker is '' (not NULL) for non-earnings rows so the UNIQUE key works.

CREATE TABLE IF NOT EXISTS calendar_events (
    id                 INTEGER PRIMARY KEY,
    source             TEXT NOT NULL,      -- forexfactory | nasdaq | binance
    kind               TEXT NOT NULL,      -- macro | earnings | crypto | binance
    title              TEXT NOT NULL,
    starts_at          TEXT NOT NULL,
    all_day            INTEGER NOT NULL DEFAULT 0,
    session            TEXT,               -- earnings: before_open | after_close | NULL
    impact             TEXT,               -- high | medium | low | NULL
    country            TEXT,
    ticker             TEXT NOT NULL DEFAULT '',
    instrument_symbols TEXT,               -- JSON list of TradingView symbols
    forecast           TEXT,
    previous           TEXT,
    actual             TEXT,
    url                TEXT,
    fetched_at         TEXT NOT NULL,
    UNIQUE (source, kind, title, starts_at, ticker)
);

CREATE INDEX IF NOT EXISTS calendar_events_starts ON calendar_events (starts_at);

CREATE TABLE IF NOT EXISTS calendar_sources (
    name       TEXT PRIMARY KEY,
    available  INTEGER,                    -- 1, 0 or NULL (never fetched)
    error      TEXT,
    events     INTEGER,
    fetched_at TEXT
);
