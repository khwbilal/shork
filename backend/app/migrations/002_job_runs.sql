-- 002: one row per scheduled job run (WL-029).

CREATE TABLE IF NOT EXISTS job_runs (
    id          INTEGER PRIMARY KEY,
    job         TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    exit_code   INTEGER,
    message     TEXT
);

CREATE INDEX IF NOT EXISTS job_runs_job_started ON job_runs (job, started_at);
