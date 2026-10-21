-- 001: journal and signals (WL-028). Columns mirror the dicts the API returns.
-- seq keeps insertion order stable (an INTEGER PRIMARY KEY survives VACUUM);
-- it is internal and never returned. id is the public 8-character id.

CREATE TABLE IF NOT EXISTS journal (
    seq         INTEGER PRIMARY KEY,
    id          TEXT NOT NULL UNIQUE,
    created_at  TEXT,
    symbol      TEXT,
    timeframe   TEXT,
    side        TEXT,
    setup       TEXT,
    entry       REAL,
    stop_loss   REAL,
    take_profit REAL,
    confluence  REAL,
    notes       TEXT,
    status      TEXT,
    exit_price  REAL,
    closed_at   TEXT,
    r_multiple  REAL
);

CREATE INDEX IF NOT EXISTS journal_created_at ON journal (created_at);

CREATE TABLE IF NOT EXISTS signals (
    seq             INTEGER PRIMARY KEY,
    id              TEXT NOT NULL UNIQUE,
    created_at      TEXT,
    symbol          TEXT,
    timeframe       TEXT,
    bias            TEXT,
    entry           REAL,
    stop_loss       REAL,
    take_profit     REAL,
    price_at_signal REAL,
    setup           TEXT,
    trade_allowed   INTEGER,  -- boolean: 1, 0 or NULL
    confluence      REAL,
    confidence      REAL,
    status          TEXT,
    outcome         TEXT,
    verified_at     TEXT,
    bars_checked    INTEGER,
    hit_price       REAL,
    hit_at          TEXT,
    r_multiple      REAL,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS signals_created_at ON signals (created_at);
CREATE INDEX IF NOT EXISTS signals_symbol ON signals (symbol);
