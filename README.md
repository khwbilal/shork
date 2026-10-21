# Crypto Chart AI

Local **gptchart.ai-style** desk: live TradingView chart + chat that injects real technical context, then answers with Cursor agents (or OpenAI).

## What it does

1. You pick any pair (`SOLUSDT`, `BTCUSDT`, …) and timeframe.
2. Backend pulls TA / multi-timeframe context via [`tradingview-mcp-server`](https://github.com/atilaahmettaner/tradingview-mcp) (official Python package — **not** npm).
3. That context is forwarded into **Cursor SDK** (preferred) or OpenAI.
4. Chat returns bias / entry / SL / TP style analysis in the panel beside the chart.

## Quick start

### 1. API key

Copy `backend/.env.example` → `backend/.env` and set **one** of:

- `CURSOR_API_KEY` — [Cursor Dashboard → Integrations](https://cursor.com/dashboard/integrations) (same AI family as this IDE)
- `OPENAI_API_KEY` — fallback

### 2. Run (one command)

**Windows**
```powershell
cd "e:\Trading analysis via tradingview"
.\start.ps1
```

**Mac** (full zero-to-run guide: [mac-setup.md](mac-setup.md))
```bash
cd "Trading analysis via tradingview"
chmod +x start.sh
./start.sh
```

Open **http://127.0.0.1:8000** — chart + chat are served by the API (no Node required).

### Optional React UI (Vite)

If you have Node installed:

```powershell
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173 (proxies `/api` to port 8000).

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /api/health` | AI provider + TradingView package status |
| `POST /api/analyze` | Full analysis + structured levels |
| `POST /api/chat` | Follow-up Q&A with fresh market context |
| `GET /api/market/{symbol}` | Raw TA payload (debug) |

## Security note

Do **not** use `npx @atilaahmettaner/tradingview-mcp`. The official project is Python-only; fake npm copies have shipped malware.

## Disclaimer

Not financial advice. Market data may be delayed or incomplete. You are solely responsible for trading decisions.
