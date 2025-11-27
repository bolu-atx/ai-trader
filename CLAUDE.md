# AI Trader

AI-powered investment research assistant with Obsidian integration and MCP server for Claude.

## Project Overview

This is a Python CLI application that provides:
- Stock watchlist management with buy/hold/sell/watch stances
- Price tracking via yfinance
- Earnings calendar and analyst estimates
- News aggregation
- Trade journaling with thesis tracking
- External signal integration (Danelfin, Toggle AI)
- MCP server for Claude integration
- Obsidian vault integration for human-readable notes

## Tech Stack

- **Python 3.12+**
- **SQLite** for data storage (`data/trader.db`)
- **Typer** for CLI interface
- **Rich** for terminal output formatting
- **yfinance** for market data
- **MCP** (Model Context Protocol) for Claude integration
- **Obsidian** for note-taking integration

## Project Structure

```
src/
├── db.py              # SQLite schema and database operations
├── cli.py             # Click CLI commands
├── mcp_server.py      # MCP server for Claude
└── fetchers/
    ├── prices.py      # yfinance price fetching
    ├── earnings.py    # Earnings calendar
    └── news.py        # News aggregation

cron/
├── daily_update.py    # Daily data refresh (after market close)
└── weekly_brief.py    # Weekly recommendations

obsidian/ai-trader/    # Obsidian vault templates and output
data/trader.db         # SQLite database
```

## Key Commands

```bash
# Install and initialize
pip install -e .
trader init

# Watchlist
trader watchlist add NVDA --stance buy
trader watchlist list
trader watchlist stance NVDA hold

# Prices & News
trader price update --period 1mo
trader news get NVDA

# Earnings
trader earnings calendar --days 30
trader earnings info NVDA

# Trade journal
trader trade log NVDA buy 450.00 100 --thesis "Strong AI demand"
trader trade open

# Full ticker summary (JSON for AI)
trader summary NVDA
```

## Database Schema

Key tables in `data/trader.db`:
- **watchlist**: Tracked tickers with stance and notes
- **prices**: Daily OHLCV data
- **signals**: External signals (Danelfin scores, sentiment)
- **earnings**: Earnings calendar and results
- **trades**: Trade journal with thesis
- **news**: Aggregated news articles
- **recommendations**: AI-generated recommendations

## MCP Server

Run as MCP server for Claude Desktop or Claude Code:
```bash
python -m src.mcp_server
```

Available tools: `get_watchlist`, `get_ticker_summary`, `get_earnings_calendar`, `get_signals`, `get_recent_news`, `get_open_trades`, `get_trade_history`, `get_recommendations`, `add_to_watchlist`, `update_stance`, `log_trade`, `add_signal`, `update_prices`, `update_news`

## Development Guidelines

- Use `ruff` for linting (configured in pyproject.toml)
- Run tests with `pytest`
- Line length: 100 characters
- Target Python 3.12+

## Data Sources

- **yfinance**: Prices, fundamentals, news, earnings (free)
- **SEC EDGAR**: Filings (future, free)
- **Danelfin/Toggle AI**: Manual signal entry (free tier)
