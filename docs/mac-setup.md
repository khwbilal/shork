# Crypto Chart AI: Mac setup (from zero)

Full guide for a Mac with **no Python / Node / tools installed yet**.  
Goal: run the app at **http://127.0.0.1:8000**.

> **Security:** Do **not** install any npm package named `@atilaahmettaner/tradingview-mcp`. This project is Python-only. Official package: `tradingview-mcp-server` on PyPI.

---

## What you need

| Tool | Why |
|------|-----|
| **Homebrew** | Installs developer tools easily |
| **uv** | Installs Python + project dependencies (you don’t manage Python yourself) |
| **Git** | Clone / pull the project (optional if you already have the folder) |
| **Claude subscription** (Claude Code CLI) or an API key | Powers the AI analysis chat |
| Browser | Chrome / Safari / Arc |

Node.js is **optional** (only for the separate React UI). The built-in UI needs no Node.

---

## Step 1: Open Terminal

- Press `Cmd + Space`, type **Terminal**, press Enter  
- Or: **Applications → Utilities → Terminal**

Keep this Terminal window open for all steps below.

---

## Step 2: Install Homebrew

Paste and run:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the on-screen prompts (password, Enter).

### Apple Silicon (M1 / M2 / M3 / M4)

After install, Homebrew usually asks you to add it to PATH. Run the lines it prints, typically:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

### Intel Mac

```bash
echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/usr/local/bin/brew shellenv)"
```

Verify:

```bash
brew --version
```

---

## Step 3: Install uv (Python package manager)

```bash
brew install uv
```

Or without Homebrew:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then reload your shell:

```bash
source ~/.zprofile 2>/dev/null || source ~/.zshrc 2>/dev/null || true
```

Verify:

```bash
uv --version
uvx --version
```

`uv` will download a compatible Python (3.13) automatically later, so you do **not** need to install Python from python.org first.

---

## Step 4: Get the project on your Mac

### Option A: You already have the folder (USB / zip / AirDrop)

```bash
cd ~/Desktop   # or wherever you put it
cd "Trading analysis via tradingview"
```

### Option B: Clone with Git

```bash
brew install git
cd ~
git clone <YOUR_REPO_URL> "Trading analysis via tradingview"
cd "Trading analysis via tradingview"
```

If you don’t use Git, copy the whole project folder onto the Mac and `cd` into it.

Confirm you’re in the right place:

```bash
ls
# you should see: backend  frontend  README.md  start.ps1  mac-setup.md  ...
```

---

## Step 5: Create the API key file

```bash
cd backend
cp .env.example .env
open -e .env
```

(`open -e` opens TextEdit. Or use VS Code: `code .env`)

### Choose your AI

You don't have to edit `.env` by hand: `./start.sh` asks which AI to use (Claude subscription, Claude API, Cursor or OpenAI) and saves your choice and key. To use your **Claude subscription**, install and sign in to Claude Code once:

```bash
brew install node
npm install -g @anthropic-ai/claude-code
claude auth login
```

Or add a Claude **API key** by hand:

1. Open [console.anthropic.com → Settings → API keys](https://console.anthropic.com/settings/keys)
2. Create a key (it starts with `sk-ant-`) and make sure the workspace has credit
3. Put it in `.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-your_real_key_here
```

An OpenAI key (`OPENAI_API_KEY=sk-...`) also works as an alternative. See [AI providers](ai-providers.md).

Save the file (`Cmd + S`).  
Do **not** commit `.env` or share the key.

Optional (news/sentiment):

```bash
MARKETAUX_API_TOKEN=your_token
```

---

## Step 6: Install Python dependencies

Still inside `backend`:

```bash
cd ~/Desktop/"Trading analysis via tradingview"/backend
# adjust path if your folder is elsewhere

uv sync --python 3.13
```

First run downloads Python 3.13 + packages (a few minutes).  
When it finishes you should see a `.venv` folder.

---

## Step 7: Start the app

From the `backend` folder:

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Or with the venv directly:

```bash
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

You should see something like:

```text
Uvicorn running on http://127.0.0.1:8000
Application startup complete
```

### Open in browser

```bash
open http://127.0.0.1:8000
```

Or paste **http://127.0.0.1:8000** into Safari/Chrome.

Leave the Terminal window running while you use the app.  
Stop with **`Ctrl + C`**.

---

## Step 8: Quick check that AI is configured

In another Terminal tab:

```bash
curl -s http://127.0.0.1:8000/api/health
```

You want:

```json
{"status":"ok","app":"Crypto Chart AI","ai_provider":"claude","ai_model":"claude-opus-5-5","tradingview_ready":true}
```

- `ai_provider: "none"` → key missing / not saved / wrong `.env` path  
- `tradingview_ready: false` → run `uv sync` again inside `backend`

---

## Everyday commands (copy/paste)

```bash
# 1) Go to project backend
cd ~/Desktop/"Trading analysis via tradingview"/backend

# 2) Ensure PATH has brew + uv (if needed)
eval "$(/opt/homebrew/bin/brew shellenv)"   # Apple Silicon
# eval "$(/usr/local/bin/brew shellenv)"    # Intel

# 3) Start
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 4) Open UI
open http://127.0.0.1:8000
```

One-shot helper (after setup):

```bash
cd ~/Desktop/"Trading analysis via tradingview"/backend && \
  uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Or use the included script:

```bash
cd ~/Desktop/"Trading analysis via tradingview"
chmod +x start.sh
./start.sh
```

---

## Optional: React frontend (needs Node)

Only if you want the Vite UI on port 5173:

```bash
brew install node
cd ~/Desktop/"Trading analysis via tradingview"/frontend
npm install
npm run dev
open http://localhost:5173
```

Backend must still be running on port **8000**.

---

## Optional: TradingView MCP inside Claude Code (Mac)

So Claude Code can call TradingView tools directly while you work on this repo:

1. Install `uv` (already done above) and check `uvx --version`.
2. Open the project folder in Claude Code. It reads `.mcp.json` at the repo root and asks you to approve the `tradingview` server.
3. Run `/mcp` to confirm it is connected.

If Claude Code can't find `uvx`, put the full path from `which uvx` in `.mcp.json` (e.g. `/Users/YOUR_USERNAME/.local/bin/uvx`). More in [MCP integration](mcp-integration.md).

---

## Troubleshooting

### `brew: command not found`
Re-run the Homebrew PATH `eval` lines from Step 2, then open a **new** Terminal tab.

### `uv: command not found`
```bash
brew install uv
# or
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zprofile
```

### `ai_provider: none` / “AI provider is not configured”
- Confirm `.env` is at `backend/.env` (not project root only)
- Key saved with no quotes/spaces unless needed
- Claude keys start with `sk-ant-`
- `.env` is re-read on every request; no restart needed

### Port 8000 already in use
```bash
lsof -i :8000
kill <PID>
```

Or use another port:

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
open http://127.0.0.1:8001
```

### Slow / empty analysis
TradingView’s public TA can rate-limit. The app falls back to **Binance** candles + whale/flow data automatically, so wait for the first run to finish.

### Permission errors on install
```bash
sudo chown -R $(whoami) ~/.local
```

### macOS Gatekeeper blocks a binary
System Settings → Privacy & Security → allow the blocked tool, or reinstall via Homebrew.

---

## What the app does (short)

1. Search a pair (e.g. `SOLUSDT`, `ZECUSDT`, `BTWUSDT.P`)
2. Chart loads (TradingView widget)
3. **Full analysis** pulls technicals + whale/funding/OI when available
4. Claude returns bias, entry, stop, target, support, resistance

---

## Checklist

- [ ] Homebrew installed  
- [ ] `uv --version` works  
- [ ] Project folder on disk  
- [ ] `./start.sh` menu shows your chosen AI as `[ready ]`  
- [ ] `uv sync --python 3.13` succeeded inside `backend`  
- [ ] `uv run uvicorn ...` shows startup complete  
- [ ] Browser opens http://127.0.0.1:8000  
- [ ] `/api/health` shows your provider (e.g. `ai_provider: claude_code`)
