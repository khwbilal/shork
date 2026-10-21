# 0005: The Unefy portal is the UI reference

**Date:** 2026-10-21 · **Work items:** WL-003, WL-009 · **Status:** accepted

## Context

Sheryar asked for the UI to take its inspiration from `C:\IT22\unefy-platform`, the Unefy portal built against the Portal Design Guide v2.x.

## Decision

Adopt its tokens and patterns (Inter, the cool-grey neutral ramp, `--action` separate from `--brand`, a 224px rail folding to 64px, a 52px top bar with Ctrl K search, KPI strips, widget cards, glyph plus colour pills, an em dash for missing data, light and dark themes). Unefy's MUI and i18n rules do not apply here: this repo has plain CSS, vanilla JS and a small React app, and is English only.

## Consequences

- New UI work ports from Unefy's real measurements and token file (`src/styles/theme/unefy-tokens.ts` there).
- Conventions are listed in [ui.md](../ui.md) and ruleset section 9.
