# Scheduled jobs

Windows has no cron, so jobs run from the **Task Scheduler** through a `.bat` file per job (added in WL-029). The machine runs on Pakistan Standard Time, so every time below is local PKT.

## Jobs

| Job | When | What | Item |
|---|---|---|---|
| `instruments` | daily 15:30 | Refreshes the [instrument catalogue](features/symbol-search.md#instrument-catalogue) from Binance | WL-044 |
| `calendar` | daily 16:00 | Refreshes the [calendar](features/calendar.md) for today plus 7 days | WL-039 |
| `backup` | daily 20:00 | Copies the database to `backups/YYYY-MM-DD.db` | WL-030 |

## How it works

- Task `\CryptoChartAI\<job>` starts `scripts\jobs\<job>.bat`, which runs `backend\.venv\Scripts\python.exe -m app.jobs <job>`.
- Exit codes are 0 for ok, 1 for failed, and 2 for an unknown job or wrong usage.
- Tasks run only while you are logged on (no password is stored) and with no window. A run missed because the PC was asleep happens at the next wake (StartWhenAvailable).
- **Register or update** all tasks: `powershell -ExecutionPolicy Bypass -File scripts\jobs\register.ps1`. **Remove** them all by adding `-Remove`.

## Seeing runs

- `GET /api/jobs` shows the last run of each job (start, end, exit code, message) and its next run.
- The `job_runs` table has the full history.
- `backend/data/logs/jobs.log` has the start and end of each run, plus the traceback when one fails.
- **Do not trust the Task Scheduler's "Last Run Result"**: it always shows 0, even when a job fails. The hidden window runs through `conhost.exe --headless`, which always exits 0. Read `/api/jobs` instead. WL-048 makes failures visible in the portal.

## Adding a job

1. Write `backend/app/jobs/<name>.py` with `run() -> str`. Return a short ASCII summary, and raise on failure.
2. Add `"<name>": Job("<name>", <module>.run, "daily HH:MM")` to `JOBS` in `backend/app/jobs/__init__.py`.
3. Copy `scripts/jobs/backup.bat` to `<name>.bat` and change the job name. Keep CRLF line endings, because cmd.exe needs them.
4. Add `@{ Name = '<name>'; At = 'HH:MM'; Bat = '<name>.bat' }` to `$Jobs` at the top of `register.ps1`, then rerun it.
5. Add tests that use the temporary `DB_PATH` and `BACKUP_DIR` from `tests/conftest.py`.

## Backup

- The job uses SQLite's online backup API, so it is safe while the server writes.
- It writes a temp file first, switches the copy to a single self-contained file (journal mode DELETE), runs `PRAGMA integrity_check`, and only then replaces the day's file. A second run on the same day overwrites that day's file.
- **Retention:** the newest 30 `YYYY-MM-DD.db` files are kept. Other files in `backups/` are never touched.
- `BACKUP_DIR` in `backend/.env` changes the folder.

## Restore a backup

Tested on 2026-10-21 on a scratchpad copy.

1. Stop the server.
2. Move `backend\data\app.db`, `app.db-wal` and `app.db-shm` aside, for example into `backend\data\pre-restore\`.
3. Copy `backups\<date>.db` to `backend\data\app.db`.
4. Start the server. Startup re-applies WAL mode and any newer migrations.
5. Check that `GET /api/signals` and `GET /api/journal` show the expected rows.

To look inside a backup without touching the live database, copy it anywhere and set `DB_PATH` to the copy.
