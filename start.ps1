# Start Crypto Chart AI (API + built-in UI)
#   .\start.ps1                       ask which AI to use, then start
#   .\start.ps1 -Provider claude_code skip the menu (claude_code | claude | cursor | openai | none)
#   .\start.ps1 -Keep                 skip the menu and keep AI_PROVIDER from backend\.env
param(
  [string]$Provider = "",
  [switch]$Keep
)
$ErrorActionPreference = "Stop"
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
Set-Location "$PSScriptRoot\backend"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Write-Host "uv not found. Install it with:"
  Write-Host '  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'
  Write-Host "See docs\getting-started.md"
  exit 1
}

# Install / update dependencies (quick when nothing changed)
uv sync --python 3.13 --quiet
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created backend\.env from .env.example"
}

$chooseArgs = @()
if ($Provider) { $chooseArgs += @("--provider", $Provider) }
if ($Keep) { $chooseArgs += "--keep" }
& .\.venv\Scripts\python.exe -m app.choose_provider @chooseArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Open http://127.0.0.1:8000"
& .\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
