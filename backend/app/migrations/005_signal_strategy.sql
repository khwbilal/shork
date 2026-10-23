-- 005: strategy_id on signals (WL-050).
ALTER TABLE signals ADD COLUMN strategy_id TEXT;
CREATE INDEX IF NOT EXISTS signals_strategy_id ON signals (strategy_id);
