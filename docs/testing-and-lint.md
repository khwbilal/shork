# Tests and lint

How the code is checked before a change counts as done. The full gate, with every step and when it applies, is in the [ruleset](reference/ruleset.md) section 6.

## Run them

```bash
cd backend
.venv/Scripts/python.exe -m pytest -q          # about 95 tests, under a second, offline
.venv/Scripts/python.exe -m ruff check app tests

cd ../frontend
npm run lint                                   # ESLint 9
```

`uv sync` installs pytest and ruff (they are in the `dev` dependency group of `backend/pyproject.toml`). `npm install` installs ESLint.

## Tests (pytest)

Added in WL-018. Tests live in `backend/tests/` and never touch the network, a billable AI or the real `backend/.env`.

| File | Unit | What it pins |
|---|---|---|
| `test_config.py` | `config.resolve_provider` | `none`, pinned providers with no fall-through, aliases, the `auto` order, `auto` skipping `claude_code` without a token |
| `test_guards.py` | `main._apply_reward_risk_guard`, `main._apply_confluence_guardrail` | Wrong-side levels and R:R below 1:1 become Neutral, exactly 1:1 passes; the confluence guard as it is today (its policy is WL-021); both guards in pipeline order |
| `test_prompt_block.py` | `market.context_to_prompt_block` | Pair, timeframe, price, `setup` and `confluence` first; empty values dropped, `False` and `0` kept; low-value sections dropped whole; the hard cut keeps `setup` and `confluence` ([incident WL-012](incidents/WL-012.md)) |
| `test_symbols.py` | `symbols.search_symbols` | `<q>USDT` first, the selected exchange first, `ALL` means no preference, perp boost, dedupe, limit, caching, no `ALL:` pseudo-exchange |
| `test_choose_provider.py` | `choose_provider.set_env_values` | A missing file is created, other lines and comments kept, duplicate keys all updated, new keys appended in order |

`tests/conftest.py` has one fixture that applies to every test:

- clears the `AI_*` and key variables;
- points `Settings` at an empty temp env file;
- redirects `choose_provider.ENV_FILE` to a temp file;
- blocks `httpx` sends.

A new test needs none of that set up by hand.

Some tests pin current behaviour that has an open item:

- WL-026: a confidence of 0.0 becomes 0.4 when the trade is blocked.
- WL-027: the hard cut can run 14 characters over the budget.
- WL-021: the guard policy.

When one of those items is fixed, update the pinning test in the same item.

**Not covered yet:** endpoint tests (for example `/api/analyze` with `AI_PROVIDER=none`, which the smoke test covers by hand) and the provider generate functions.

## Lint

Added in WL-019.

- **Python: ruff.** It uses only the default rules (`E4`, `E7`, `E9`, `F`), with the config in `backend/pyproject.toml`. It is a linter only: `ruff format` is not used, so do not reformat code.
- **React UI: ESLint 9.** The flat config is `frontend/eslint.config.js`. It uses `@eslint/js` recommended, typescript-eslint recommended (without type information), and react-hooks with rules-of-hooks as an error and exhaustive-deps as a warning. `eslint-plugin-react-hooks` stays on v5, because v7's recommended set adds the React Compiler rules.
- **The no-build UI** (`backend/app/static/app.js`) is not linted. It is checked only by `node --check`.

## Gotcha

Edits made on Windows can turn LF files into CRLF (seen in WL-019). The code is LF. After an edit, `file backend/app/*.py | grep CRLF` should print nothing; `sed -i 's/\r$//' <file>` fixes it.
