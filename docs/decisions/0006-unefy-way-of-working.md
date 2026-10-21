# 0006: The unefy way of working, adapted

**Date:** 2026-10-21 · **Work item:** WL-015 · **Status:** accepted

## Context

Sheryar asked that sessions on this repo work like those on unefy-platform, and pasted its session-start prompt. That prompt predates the unefy ruleset v2.0 (WL-109 there), which removed tmux and moved docs and merges to the end of a batch; the repo version wins.

## Decision

[ruleset.md](../reference/ruleset.md) 1.0 mirrors unefy ruleset v2.0 section by section, with these changes:

| unefy rule | Here |
|---|---|
| Branch, PR and worktree per item; merge into `acceptance` | Dormant: no git ([0004](0004-no-git-for-now.md)); one agent at a time or non-overlapping files; back up before rewriting |
| Gate: typecheck, ESLint, Jest, `next build`, SonarQube | `compileall`, `node --check`, `tsc -b` plus `vite build`, an offline smoke test, Playwright screenshots for UI; lint and tests are WL-019 and WL-018 |
| `npm run scan` (Trivy) | `trivy fs` over `uv.lock` and `package-lock.json` with the same severity and ignore-unfixed rules |
| Version check: npm, Docker, Sonar, JDK | `uv pip list --outdated`, `npm outdated`, `npm audit`, Node, uv, Trivy, Claude CLI |
| MUI, i18n, Design Guide citations, BE contract in a backend repo | Not applicable; replaced by UI conventions from [ui.md](../ui.md) and API contract updates across schema and both UIs |
| tmux workbench | Left out, as in unefy v2.0 |
| `/context` base load | Sheryar runs it; the assistant cannot |

Kept as is: issue first, log found work in the same turn, sub agent per item with a lean brief, ask before an agent for a bug, docs pass last, decisions and incidents, no em or en dashes or exclamation marks, real exit codes, patch and minor bumps without asking and majors asked, self-review every 10 prompts, one question per message, "hi claude" session start.

## Consequences

- Every session starts from `CLAUDE.md`, which points to the ruleset and [project-state.md](../project-state.md).
- Changing the rules goes through ruleset 0.1 (diff, ok, version bump).
