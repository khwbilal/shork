# Crypto Chart AI: documentation

A local crypto analysis desk: a live TradingView chart next to an AI analyst. The backend gathers real market context (technical indicators, multi-timeframe trend, whale positioning, order book, liquidation map), scores it, and then asks an AI (your **Claude subscription**, the Claude API, Cursor or OpenAI; chosen at startup) for a trade plan that has to respect that score.

> Market data may be delayed or incomplete.

## Start here

| If you want to… | Read |
|---|---|
| Pick up development where it was left | [Project state & handoff](project-state.md) |
| Run it for the first time | [Getting started](getting-started.md) |
| Set up a Mac from nothing | [Mac setup](mac-setup.md) |
| Use your Claude subscription, or switch provider | [AI providers](ai-providers.md) |
| See every `.env` setting | [Configuration](configuration.md) |
| Fix something that isn't working | [Troubleshooting](troubleshooting.md) |

## Way of working

| What | Read |
|---|---|
| The rules for every session ("hi claude" starts them) | [Ruleset](reference/ruleset.md) |
| Work items, open and done | [Work log](work-log.md) |
| Why things are the way they are | [Decisions](decisions/Decisions.md) |
| Non-obvious failures and what they taught | [Incidents](incidents/README.md) |
| Run the tests and linters | [Tests and lint](testing-and-lint.md) |

## How it works

| Topic | Read |
|---|---|
| Components, request flow, where data is stored | [Architecture](architecture.md) |
| How one analysis request assembles its market snapshot | [Analysis pipeline](analysis-pipeline.md) |
| HTTP endpoints | [API reference](api-reference.md) |
| UI pages, design tokens, and conventions | [User interface](ui.md) |
| Using the TradingView MCP server in Claude Code | [MCP integration](mcp-integration.md) |
| Where data is stored, tables, migrations | [Database](database.md) |
| Daily jobs (instruments, calendar, backup) and restoring a backup | [Scheduled jobs](scheduled-jobs.md) |
| Which stocks, ETFs and commodities Binance lists | [Binance instruments](binance-instruments.md) |

## Features

| Feature | What it does |
|---|---|
| [Analysis & chat](features/analysis-and-chat.md) | Full analysis → trade plan (bias, entry, stop, target), then follow-up Q&A |
| [Confluence score](features/confluence-score.md) | Weighted −10…+10 score that the AI is not allowed to contradict |
| [Setup classifier](features/setup-classifier.md) | Chop / mean-revert / breakout / trend continuation, plus the chop filter |
| [Flow, order book & liquidity](features/flow-and-liquidity.md) | Whale vs retail positioning, funding, OI, depth imbalance, liquidation clusters |
| [Watchlist scorer](features/watchlist.md) | Ranks ten majors by setup quality |
| [Trade journal](features/journal.md) | Log plans, close them as win/loss/BE, track hit rate and R |
| [Signal verification](features/signals.md) | Auto-archives every Buy/Sell and checks it against later candles |
| [Symbol search](features/symbol-search.md) | Search over the local catalogue of every Binance pair, stock, ETF and commodity, by symbol or name |
| [Calendar](features/calendar.md) | Macro events, earnings of Binance-listed stocks and Binance announcements, today plus 7 days |
