# Ruleset: Crypto Chart AI development

Version 1.1, 2026-10-21. Owner: Sheryar. Scope: all work on this repo (FastAPI backend in `backend/`, built-in UI in `backend/app/static/`, React UI in `frontend/`, `docs/`). Adapted from the unefy-platform FE ruleset v2.0 (`C:\IT22\unefy-platform\instructions\ruleset-fe-development.md`); see [decision 0006](../decisions/0006-unefy-way-of-working.md) for what was kept, changed and left out. Sits on top of `CLAUDE.md` and `docs/`; where it is silent they win, and a verified repo fact beats this file.

## 0. Tailoring and self-review

0.1 Sheryar may change this ruleset at any time in plain words. The LLM shows the exact diff, waits for an ok, then applies it and bumps the version and change log. Nothing is edited silently.

0.2 Every 10th prompt the LLM reviews itself (where did Sheryar repeat or correct himself; what was wrong or unverified) and shows a short finding list, a proposed diff and one request. It applies nothing before he answers. Nothing to fix: one line, reset the count.

0.3 Sections are Required, Conditional (only when the change touches that area) or Not required. When unsure, ask once.

0.4 Precedence: Sheryar's current message, then this file, then defaults. Repo facts beat memory and this file.

## 1. Work items (Required)

Tracker of record: [docs/work-log.md](../work-log.md), ids `WL-nnn`.

1.1 Every unit of work gets a work-log entry (id, title, context, acceptance criteria) **before the first code edit**. Take the next free id from the log. Scan for duplicates first.

1.2 One item, one change set. While the repo has no git (2026-10-21, section 4) there are no branches; an item is done when its gate is green and its docs pass is written.

1.3 Status is open / in progress / blocked / done; a done item keeps its row with the outcome. Never invent hours or dates.

1.4 Create items immediately when work is found (a bump, a CVE, a review gap, a follow-up), in the same turn. Ask about what to *do*, never about whether to *log*.

## 2. Sub agents and context budget (Required)

2.1 An item that is more than a small edit goes to the `wl-worker` sub agent ([.claude/agents/wl-worker.md](../../.claude/agents/wl-worker.md)) with minimal context: the item text, the files to touch, the API contract and the relevant doc section. The main chat plans, logs, briefs, reviews and relays.

2.2 Ask before spawning an agent for an error or bug: show the issue, the context passed and the plan; list several errors at once.

2.3 **No git means no worktrees:** run at most one agent at a time, or agents whose file sets do not overlap. Back up any file an agent will rewrite to the scratchpad first.

2.4 An agent does code and gate only. It does not edit `docs/` or `docs/work-log.md`; its report ends with a few lines for the docs pass. Prefer continuing an existing agent over spawning a cold one; a mechanical item may use a smaller model.

2.5 **Docs come last, once:** when the items of a batch are done, the main chat runs one documentation pass (work-log outcomes, feature docs, hubs, decisions, incidents, [project-state.md](../project-state.md)).

2.6 Keep the token load small: `CLAUDE.md`, `MEMORY.md` and the agent definition stay lean, detail goes to `docs/`. Ask Sheryar for the `/context` base load at session start (target under 10K). MCP servers stay off unless a task needs them. Agents keep command output short (`tail`, `Select-Object -Last N`).

## 3. Documentation (Required, written in the docs pass of 2.5)

- A feature added or substantially changed: its page in `docs/features/` (or a new one) with a file map, the why, the API contract, gotchas and an extension checklist, linked from [docs/README.md](../README.md).
- A non-obvious choice: `docs/decisions/NNNN-*.md`, listed in [Decisions](../decisions/Decisions.md); supersede with a new note, never rewrite an old one.
- A non-obvious failure: `docs/incidents/WL-nnn.md` from the [template](../incidents/_TEMPLATE.md), listed in the [incidents README](../incidents/README.md). An item with nothing surprising says "no incidents" in its work-log entry.
- Every new doc is linked from its hub with a standard markdown link (no wiki links).
- Record every limitation or known issue noticed, with date and status, even outside the task.
- [project-state.md](../project-state.md) is updated at the end of every session.
- Memory: only what the repo does not already record, one fact per file.
- If Sheryar edits code, update the affected docs and say which.
- Project text (docs, memory, commit messages once git exists): **no em dashes, no en dashes, no exclamation marks.** Older docs still contain dashes; [WL-020](../work-log.md) sweeps them.

## 4. Git (Not required, dormant)

4.1 Sheryar decided on 2026-10-21 to **leave git out for now** ([decision 0004](../decisions/0004-no-git-for-now.md)). Do not initialise git or suggest it.

4.2 Because nothing can be reverted: back up a file before a risky or scripted edit, and record changed files in the item's work-log entry.

4.3 If Sheryar enables git later, adopt the unefy rules: Conventional Commits with the `WL-nnn` id, one branch per item, commit or push only when asked, never `--no-verify`. Then update this section and the version.

## 5. Errors (Required)

One failing check, build or bug is one item: capture the real output and exit code (write to a file, never trust a piped `echo $?`), log it, ask before an agent (2.2), fix, add a check.

## 6. Quality gate (Required)

6.1 Done means every applicable step exits 0. Write output to a file and read the real code: `cmd > out.txt 2>&1; echo "REAL EXIT: $?"`.

| Step | Command (from the repo root) | When |
|---|---|---|
| Python compiles | `backend/.venv/Scripts/python.exe -m compileall -q backend/app` | any backend change |
| Python tests | `cd backend && .venv/Scripts/python.exe -m pytest -q` | any backend change |
| Python lint | `cd backend && .venv/Scripts/python.exe -m ruff check app tests` | any backend change |
| React lint | `cd frontend && npx eslint .` | any React change |
| Built-in UI parses | `node --check backend/app/static/app.js` | any static UI change |
| React types and build | `cd frontend && npx tsc -b && npm run build` (delete `frontend/dist` afterwards) | any React or `app.css` change |
| Smoke test | start uvicorn on a spare port with `AI_PROVIDER=none`, then `GET /api/health` is 200 and `POST /api/analyze` returns `provider: "offline"` | any backend change |
| UI check | Playwright from `C:/IT22/unefy-platform/node_modules/playwright`: desktop and 390px phone, light and dark, no page errors, no horizontal overflow | visible UI changes |
| Security scan | see 7.2 | dependency changes, before declaring a batch done |

6.2 Tests and lint are described in [testing-and-lint.md](../testing-and-lint.md). A change to a tested unit updates its test in the same item.

6.3 **Never call a billable AI in a check.** `AI_PROVIDER=claude_code` spends Sheryar's plan usage and `claude` / `cursor` / `openai` spend money: use them only when the item is about AI output, say so before the call, and keep it to one request.

6.4 Report real results; never mark an item done while a step is red. Never weaken or delete a check without asking.

## 7. Security and versions (Required)

7.1 No secrets or personal data in logs, fixtures, errors, docs or memory. Never print or copy the values in `backend/.env`; refer to keys by name. Keep the server on `127.0.0.1` (the API has no auth). The `claude_code` provider is for Sheryar's personal local use only.

7.2 Security scan (Trivy is installed via winget):

```bash
trivy fs --scanners vuln,secret,misconfig --severity HIGH,CRITICAL --ignore-unfixed \
  --skip-dirs backend/.venv --skip-dirs frontend/node_modules --skip-dirs frontend/dist \
  --exit-code 1 . > trivy.txt 2>&1; echo "REAL EXIT: $?"
```

It fails only on **fixable** High/Critical findings; do not lower that. A fixable CVE becomes its own work item and bump, never folded into an unrelated change. An accepted finding goes in a `.trivyignore` with a reason on the line, never a bare waiver.

7.3 On "hi claude", check versions: `uv pip list --outdated` (in `backend/`), `npm outdated` and `npm audit` (in `frontend/`), the Trivy scan, and the toolchain (`node -v` is 24.x LTS, `uv --version`, `uv self update --dry-run`, `trivy --version`, `claude --version` and `claude auth status`). Report current to latest. Patch and minor bumps inside the current major are logged and done without asking; majors are asked first with what they break. Transitive Python packages move with their parent (`uv lock --upgrade-package <parent>`), not pinned directly. Machine-level tools needing winget or admin rights are listed for Sheryar to run.

## 8. API contracts (Conditional)

When an endpoint is added or its shape changes: update [api-reference.md](../api-reference.md), the schema in `backend/app/schemas.py`, and the types in `frontend/src/api.ts` in the same item, and check both UIs read the new shape.

## 9. Front end standards (Required for UI work)

9.1 Both UIs move together: a visible change lands in the built-in UI **and** the React UI in the same item, or a follow-up item is logged for the other.

9.2 One stylesheet: `backend/app/static/app.css` serves both UIs. Colours come from the tokens on `:root`; no hex in a component rule. Discuss before changing shared tokens.

9.3 Conventions from [ui.md](../ui.md): direction ink (green/red) for Buy/Sell and win/loss only, every pill has a glyph; missing data is an em dash with a reason (`na()` / `<Na>`); escape every interpolated value (`esc()`, React escapes by default); `askDialog()` / `ask()` instead of `prompt` / `confirm`; one primary button per view; mobile body text 16px and 48px targets.

9.4 The design reference is the Unefy portal (`C:\IT22\unefy-platform`, Portal Design Guide v2.x). Port from real measurements; say when something was measured from a screenshot.

## 10. Working style (Required)

10.1 One step or question per message, placed last. Batch independent low-risk tool calls.

10.2 Announce large tree changes (moves, renames, new top-level folders) and get approval first; update every path reference after a move.

10.3 Report faithfully: failures with output, skipped steps named, done stated plainly.

10.4 **"hi claude"** starts the session: confirm this ruleset, start the prompt count, read [project-state.md](../project-state.md), then report in a few lines: the docs review (open work-log items and "to fill in" lines, hub coverage, every feature doc's file map naming files that still exist), the version and security check (7.3) and the machine check (Node 24, uv, Trivy, Claude CLI login). List gaps and log items for them; fix nothing yet.

10.5 At handover: update [project-state.md](../project-state.md), and say which items are open and which files changed.

10.6 After a scripted edit, grep for the result. Prefer the Edit tool; for large scripted edits write a `.js` file to the scratchpad and run it (long heredocs with backticks break the Bash tool).

10.7 Windows traps (details in [project-state.md](../project-state.md#gotchas-learned-the-hard-way-windows)): Vite serves on `localhost` (IPv6) not `127.0.0.1`; set `PYTHONIOENCODING=utf-8` for ad-hoc Python output; subprocess-based providers must run in a thread.

## 11. Change log

| Version | Date | Change | Approved by |
|---|---|---|---|
| 1.0 | 2026-10-21 | First version, adapted from the unefy-platform FE ruleset v2.0 (WL-015): Python and React gate instead of Next.js, SonarQube and Jest; git, branches and worktrees dormant by owner decision; Trivy command for `uv.lock` and `package-lock.json`; tmux left out as in unefy v2.0. | Sheryar (asked for it, 2026-10-21) |
| 1.1 | 2026-10-21 | pytest, ruff and ESLint join the gate (6.1, 6.2; WL-018, WL-019). | Sheryar (2026-10-21) |
