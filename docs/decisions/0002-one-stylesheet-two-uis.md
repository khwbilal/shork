# 0002: One stylesheet serves both UIs

**Date:** 2026-10-21 · **Work item:** WL-009 · **Status:** superseded by [0008](0008-react-mui-only.md) (2026-10-22)

## Context

There are two frontends: the built-in UI (`backend/app/static/`, no Node needed) and the React UI (`frontend/`). Two stylesheets would drift.

## Decision

`backend/app/static/app.css` is the only stylesheet. The React app imports it directly (`frontend/src/main.tsx`); `vite.config.ts` allows reading `..` (`server.fs.allow`). Class names are shared, and the React components render the same markup.

## Consequences

- A token or component style change applies to both UIs at once.
- A visible behaviour change must be made in both UIs (ruleset 9.1).
- The React gate (`npx tsc -b && npm run build`) also runs after any `app.css` change.
