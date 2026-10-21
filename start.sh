#!/usr/bin/env bash
# Start Crypto Chart AI on macOS / Linux
#   ./start.sh                         ask which AI to use, then start
#   ./start.sh --provider claude_code  skip the menu (claude_code | claude | cursor | openai | none)
#   ./start.sh --keep                  skip the menu and keep AI_PROVIDER from backend/.env
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"

# Common uv locations
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install: brew install uv  (or: curl -LsSf https://astral.sh/uv/install.sh | sh)"
  echo "See docs/getting-started.md"
  exit 1
fi

# Install / update dependencies (quick when nothing changed)
uv sync --python 3.13 --quiet

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created backend/.env from .env.example"
fi

uv run --quiet python -m app.choose_provider "$@"

echo ""
echo "Open http://127.0.0.1:8000"
exec uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
