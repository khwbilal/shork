-- 003: instrument catalogue (WL-044). Binance spot pairs and USD-M contracts,
-- refreshed daily by the `instruments` job. Rows are never deleted: a symbol
-- missing from exchangeInfo becomes status 'delisted'.

CREATE TABLE IF NOT EXISTS instruments (
    id         INTEGER PRIMARY KEY,
    symbol     TEXT NOT NULL,              -- exchange symbol, e.g. BTCUSDT, NVDAUSDT
    market     TEXT NOT NULL,              -- spot | usdm
    type       TEXT NOT NULL,              -- crypto | stock | etf | commodity | fx | index | premarket
    base       TEXT,
    quote      TEXT,
    name       TEXT,
    region     TEXT,                       -- US | HK | KR | CN, NULL for non-equities
    status     TEXT NOT NULL DEFAULT 'trading',  -- trading | delisted
    first_seen TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (symbol, market)
);

CREATE INDEX IF NOT EXISTS instruments_status ON instruments (status);

-- Prefix search on symbol, base and name ("nvd*", "gold*"). External content:
-- the refresh job rebuilds it after each run.
CREATE VIRTUAL TABLE IF NOT EXISTS instruments_fts USING fts5 (
    symbol, base, name,
    content = 'instruments',
    content_rowid = 'id'
);
