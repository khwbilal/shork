# 0008: The portal is React + MUI only

**Date:** 2026-10-22 · **Work item:** WL-047 · **Status:** accepted · Supersedes [0002](0002-one-stylesheet-two-uis.md)

## Context

The autocomplete for WL-044 raised the question of whether to use MUI. The React UI was hand-built on the shared `app.css`, and the built-in UI in `backend/app/static/` has no build step, so MUI cannot run there. Claude recommended building an MUI-style widget without the library (option 1).

## Decision

Sheryar chose option 2, "everything MUI" (2026-10-21), and approved the ruleset change that retires the built-in UI ("yes", 2026-10-22).

## Consequences

- One UI: `frontend/` on React 19 with MUI, and one theme in `frontend/src/theme.ts` (light and dark). The theme carries over the existing palette values.
- FastAPI serves the React build, so `http://127.0.0.1:8000` keeps working. The start scripts build the UI first, which means Node is needed to run the app.
- The built-in UI is frozen until WL-047 lands, then removed. Its files are kept in a scratchpad backup.
- Ruleset 1.2 changes 9.1, 9.2 and 9.3 and drops the `node --check` gate step.
- Every feature is built once.
