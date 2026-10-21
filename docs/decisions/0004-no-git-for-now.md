# 0004: No git for now

**Date:** 2026-10-21 · **Status:** accepted

## Context

The folder is not a git repository. Initialising git was offered at the end of the first sessions.

## Decision

Sheryar: "ignore git for now". Git is not initialised, and sessions do not suggest it.

## Consequences

- No history and no revert: back up a file to the scratchpad before a risky or scripted edit, and name changed files in the work-log entry.
- No branches or worktrees: work items run one at a time, or on file sets that do not overlap (ruleset 2.3).
- [project-state.md](../project-state.md) and the [work log](../work-log.md) are the only record of what changed.
- If git is enabled later, ruleset section 4.3 says which unefy rules switch on; supersede this note then.
