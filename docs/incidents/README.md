# Incidents

One report per work item that hit a non-obvious failure ([ruleset](../reference/ruleset.md) section 3). Copy [_TEMPLATE.md](_TEMPLATE.md) to `WL-nnn.md` and add a row here. Security-sensitive details stay out of the repo.

| Item | Date | What | Status |
|---|---|---|---|
| [WL-025](WL-025.md) | 2026-10-21 | Test servers kept running after they were "stopped"; a stale backend served port 8000 | fixed |
| [WL-016](WL-016.md) | 2026-10-21 | One analysis came back offline although `claude_code` was selected | open; not reproduced |
| [WL-012](WL-012.md) | 2026-10-21 | The AI never saw the confluence score: the prompt snapshot was cut at 5,000 characters | fixed |
