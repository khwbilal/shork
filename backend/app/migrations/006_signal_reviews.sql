-- 006: live review history on signals (WL-052). Original plan columns stay frozen.
ALTER TABLE signals ADD COLUMN live_review_json TEXT;
