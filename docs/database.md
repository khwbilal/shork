# Database

All app data lives in one SQLite file. The engine was chosen in WL-028 ([decision 0007](decisions/0007-sqlite.md)).

## Where

- File: `backend/data/app.db`, plus `app.db-wal` and `app.db-shm` beside it (normal in WAL mode). The folder is gitignored.
- `DB_PATH` in `backend/.env` points the app at another file. Blank means the default. Tests and smoke runs use it so they never touch the real database.
- Daily copies go to `backups/` at the repo root, as described in [Scheduled jobs](scheduled-jobs.md#backup).

## How it is used

- Only the stdlib `sqlite3` module is used, with no ORM. `backend/app/db.py` holds `connect()`, `migrate()`, `init_db()`, the JSON import and small row helpers.
- Every call opens its own connection, so FastAPI worker threads never share one.
- The database runs in WAL mode with foreign keys on, and rows come back as dicts.
- Each table has an internal `seq INTEGER PRIMARY KEY` that keeps insertion order stable. It is never returned. The public `id` is the 8-character string the API has always used.

## Tables

| Table | Migration | Item | Holds |
|---|---|---|---|
| `journal` | 001 | WL-028 | [Trade journal](features/journal.md) entries |
| `signals` | 001 | WL-028 | [Signal archive](features/signals.md) |
| `schema_version` | 001 | WL-028 | Applied migrations: version, name, applied_at |
| `job_runs` | 002 | WL-029 | One row per [scheduled job](scheduled-jobs.md) run: job, started_at, finished_at, exit_code, message |
| `instruments` and `instruments_fts` | 003 | WL-044 | The [instrument catalogue](features/symbol-search.md#instrument-catalogue), plus an FTS5 prefix index on symbol, base and name |
| `calendar_events` and `calendar_sources` | 004 | WL-039 | The [calendar](features/calendar.md) and the status of each source |

## Adding a migration

1. Create `backend/app/migrations/NNN_<name>.sql` with the next number. Use `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`.
2. It runs once, in number order, at startup (or on the first `connect()`). It runs in one transaction together with its `schema_version` row.
3. Never edit an applied file. Put any change in a new number.
4. If the table backs an API, add its column tuple to `db.py`. Then add tests that use the temporary `DB_PATH` from `tests/conftest.py`.

## JSON import (one time)

Before WL-028, data lived in `backend/data/journal.json` and `signals.json`. At startup, any such file in the database's folder is imported in a transaction. Rows whose id already exists are skipped, so the import can safely run again. The file is then renamed to `*.json.imported`; it is never deleted. A file that fails to parse is logged and left in place.

## Restore

See [Scheduled jobs: restore a backup](scheduled-jobs.md#restore-a-backup).
