# 0007: SQLite for app data

**Date:** 2026-10-21 · **Status:** accepted

## Context

Sheryar asked for a small database ("maybe MySQL") for journals, trades and the rest (WL-028). Most planned items need tables. These include instruments, calendar, backtests, picks, paper trades and notes, plus financials for 8 quarters.

## Decision

SQLite. Claude recommended it twice, the second time after WL-044 to WL-046 were added, and Sheryar confirmed it: "go with SQlite".

## Why

- **The data is small.** The biggest tables hold a few thousand rows (2,183 instruments), and SQLite handles millions.
- **WAL mode** lets the server read while a scheduled job writes.
- **FTS5** gives the prefix search the autocomplete needs.
- **A backup is one file** (WL-030).
- **MySQL would bring a server**, a service, a password in `.env` and an admin install. It only pays off with several users, several machines or remote access. None of these apply, since the server stays on `127.0.0.1`.

## Consequences

- One file, `backend/data/app.db`, with migrations in `backend/app/migrations/`. See [Database](../database.md).
- Database code goes through `db.py` and the repository functions in each module, so a later move to MySQL touches one layer.
