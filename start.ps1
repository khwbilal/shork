# Start Crypto Chart AI (API + built-in UI)
$ErrorActionPreference = "Stop"
$env:Path = "C:\Users\khwaj\.local\bin;$env:Path"
Set-Location "$PSScriptRoot\backend"

if (-not (Test-Path ".venv\Scripts\uvicorn.exe")) {
  Write-Host "Installing backend deps..."
  uv sync --python 3.13
}

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created backend\.env — add CURSOR_API_KEY or OPENAI_API_KEY"
}

Write-Host "Open http://127.0.0.1:8000"
& .\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
