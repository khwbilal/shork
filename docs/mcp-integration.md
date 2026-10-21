# MCP integration (Claude Code)

The app itself calls the TradingView package directly as a Python library. It does **not** need MCP.

Separately, the same package ships an **MCP server** (`tradingview-mcp`). You can register it in your coding assistant so you can ask it things like "screen Binance for 4h breakouts" while working on this repo.

> **Security:** the official server is the PyPI package **`tradingview-mcp-server`**, which is Python-only. Do **not** use `npx @atilaahmettaner/tradingview-mcp`; fake npm copies have shipped malware.

## Claude Code

The repo root has **`.mcp.json`**, which Claude Code picks up automatically for this project:

```json
{
  "mcpServers": {
    "tradingview": {
      "command": "uvx",
      "args": ["--python", "3.13", "--from", "tradingview-mcp-server", "tradingview-mcp"]
    }
  }
}
```

1. Make sure `uvx` is on your PATH (`uvx --version`).
2. Open the project in Claude Code and approve the `tradingview` server when asked.
3. Check it with `/mcp`.

If Claude Code can't find `uvx`, replace `"uvx"` with the full path: `which uvx` on macOS/Linux, `where.exe uvx` on Windows (usually `C:\Users\<you>\.local\bin\uvx.exe`).
