#!/usr/bin/env bash
# Start Crypto Chart AI on macOS / Linux
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"

# Common uv locations
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install: brew install uv"
  echo "See mac-setup.md"
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "Installing backend deps (first run)..."
  uv sync --python 3.13
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created backend/.env — add CURSOR_API_KEY or OPENAI_API_KEY, then restart."
fi

echo "Open http://127.0.0.1:8000"
exec uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
