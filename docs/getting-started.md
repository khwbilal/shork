# Getting started

You need three things:

- **[uv](https://docs.astral.sh/uv/)**: it installs Python 3.13 and the dependencies for you.
- **An AI to write the analysis**: your **Claude subscription** (via the [Claude Code](https://docs.claude.com/en/docs/claude-code) CLI), a Claude API key, a Cursor key, or an OpenAI key. You choose when the app starts.
- **A browser.**

Node.js is only needed for the optional React UI.

## 1. Install uv

**Windows (PowerShell)**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS / Linux**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh     # or: brew install uv
```

Open a new terminal and check that `uv --version` works. On a Mac with nothing installed yet, follow [Mac setup](mac-setup.md) instead.

## 2. (For the Claude subscription) sign in to Claude Code

To use your Claude Pro / Max plan instead of an API key:

```bash
npm install -g @anthropic-ai/claude-code    # skip if `claude --version` already works
claude auth login
```

For the API-key providers (Claude API, Cursor, OpenAI) there's nothing to prepare. The start script asks for the key.

## 3. Run

**Windows**

```powershell
.\start.ps1
```

**macOS / Linux**

```bash
chmod +x start.sh
./start.sh
```

Both scripts install or update the dependencies (a few minutes the first time), create `backend/.env` from the template if it's missing, and then **ask which AI to use**. They show which options are ready, ask for any missing key (input hidden) or Claude sign-in, and save your choice to `backend/.env`. See [AI providers](ai-providers.md#choosing-a-provider-at-startup). Then open **http://127.0.0.1:8000**.

Skip the question next time with `.\start.ps1 -Keep` (or `-Provider claude_code`); on macOS/Linux, `./start.sh --keep`.

To run it by hand:

```bash
cd backend
uv sync --python 3.13
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## 4. Check the AI is connected

```bash
curl -s http://127.0.0.1:8000/api/health
```

```json
{"status":"ok","app":"Crypto Chart AI","ai_provider":"claude_code","ai_model":"plan default","tradingview_ready":true}
```

The rail at the bottom left of the UI shows the same thing: a green dot with the provider (e.g. **Claude subscription**) and model. If it reads **No AI**, see [Troubleshooting](troubleshooting.md#no-ai).

## 5. First analysis

1. Press **Ctrl K** (⌘K on a Mac), type a coin (`sol`, `zec`, `BTWUSDT.P`), and press Enter.
2. Pick a timeframe in the top bar (15m / 1h / 4h / 1D).
3. Click **Full analysis**. The first run takes 10 to 20 seconds while market data is fetched.
4. Read the plan in the Analyst panel. The KPI strip, structure levels, and insight cards fill in at the same time.
5. Ask a follow-up ("Where is the invalidation?"), or click **Log to journal**.

## Optional: React UI

The built-in UI on port 8000 needs no Node. The same app also exists as a Vite + React + TypeScript project, with the same pages and the same stylesheet:

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 — proxies /api to :8000
```
