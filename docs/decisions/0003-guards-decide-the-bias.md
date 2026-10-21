# 0003: Deterministic guards decide the bias, not the AI

**Date:** recorded 2026-10-21 (the confluence guard predates this repo's history; the reward:risk guard is WL-007) · **Status:** accepted; the Neutral upgrade is under review in WL-021

## Context

LLM trade calls vary between runs and providers. The backend already computes a confluence score and a setup classification from the same data.

## Decision

After the AI replies, `main.py` applies, in order: `_apply_confluence_guardrail` (chop or |score| under 2.5 forces Neutral; never the opposite side of a strong score; |score| of 3.5 or more upgrades a Neutral to the score's side) and `_apply_reward_risk_guard` (levels on the wrong side of entry, or under 1:1, force Neutral). When the result differs from the model's own bias, the reply starts with a `DESK OVERRIDE:` line (WL-013).

## Consequences

- The same snapshot gives the same allowed bias whichever provider answers; the AI explains and sets levels.
- The prompt snapshot must always contain `setup` and `confluence` (incident [WL-012](../incidents/WL-012.md)).
- Whether an AI "no trade" should be overridable at all is open (WL-021).
