# AI Trader

AI-powered investment research assistant with Obsidian integration and MCP server for Claude.

## Goals

Build a structured, disciplined investment research workflow that:
- Aggregates knowledge from multiple sources into a queryable database
- Integrates with Obsidian for human-readable notes and journals
- Exposes tools via MCP for AI-assisted analysis
- Automates weekly research briefs and recommendations

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Obsidian Vault                              │
│  /ai-trader                                                     │
│  ├── /daily          # Weekly briefs, daily notes              │
│  ├── /tickers        # Per-ticker research                     │
│  ├── /journal        # Trade decisions                         │
│  ├── /earnings       # Pre/post earnings analysis              │
│  └── watchlist.md    # Current watchlist                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Server / CLI                             │
│  Tools: get_watchlist, get_ticker_summary, log_trade, etc.     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SQLite Database                              │
│  Tables: watchlist, prices, signals, earnings, trades, news    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Data Fetchers                                │
│  yfinance, SEC EDGAR, RSS feeds                                │
└─────────────────────────────────────────────────────────────────┘
```

## Phases

### Phase 1: Foundation (Current)
- [x] Project structure and dependencies
- [x] SQLite database schema
- [x] Data fetchers (prices, earnings, news)
- [x] CLI interface
- [x] MCP server for Claude integration
- [x] Cron jobs (daily/weekly updates)
- [x] Obsidian templates

### Phase 2: Signal Integration
- [ ] Danelfin score integration (manual or scraping)
- [ ] Toggle AI integration
- [ ] Custom sentiment analysis on news
- [ ] SEC filing summarization with LLM

### Phase 3: Enhanced Recommendations
- [ ] LLM-powered recommendation engine
- [ ] Backtesting framework for signal validation
- [ ] Portfolio-level risk analysis
- [ ] Correlation analysis between holdings

### Phase 4: Automation
- [ ] E*Trade/Fidelity portfolio sync (read-only)
- [ ] Automated earnings prep notes
- [ ] Alert system (email/SMS for key events)
- [ ] Performance tracking dashboard

## Installation

```bash
# Clone and enter directory
cd ai-trader

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -e .

# Initialize database
trader init
```

## Usage

### CLI Commands

```bash
# Watchlist management
trader watchlist add NVDA --stance buy --notes "AI leader"
trader watchlist list
trader watchlist stance NVDA hold
trader watchlist remove NVDA

# Price data
trader price get NVDA
trader price update --period 1mo

# Earnings
trader earnings calendar --days 30
trader earnings info NVDA

# News
trader news get NVDA --count 10
trader news update

# Signals (manual entry for Danelfin, etc.)
trader signal add NVDA danelfin 8.5 --sentiment bullish
trader signal show NVDA

# Trade journal
trader trade log NVDA buy 450.00 100 --thesis "Strong AI demand"
trader trade open
trader trade history --ticker NVDA

# Full summary (JSON output for AI)
trader summary NVDA

# Recommendations
trader recommendations
```

### Cron Jobs

```bash
# Daily update (after market close, Mon-Fri)
# Add to crontab: 0 17 * * 1-5
python cron/daily_update.py

# Weekly brief (Sunday evening)
# Add to crontab: 0 18 * * 0
python cron/weekly_brief.py
```

### MCP Server (Claude Integration)

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "ai-trader": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/path/to/ai-trader"
    }
  }
}
```

Or for Claude Code, add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "ai-trader": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/path/to/ai-trader"
    }
  }
}
```

Available MCP tools:
- `get_watchlist` - Get current watchlist with metrics
- `get_ticker_summary` - Deep dive on a single ticker
- `get_earnings_calendar` - Upcoming earnings
- `get_signals` - Latest signals for a ticker
- `get_recent_news` - Recent news articles
- `get_open_trades` - Open positions
- `get_trade_history` - Trade journal
- `get_recommendations` - AI recommendations
- `add_to_watchlist` - Add ticker
- `update_stance` - Update buy/hold/sell stance
- `log_trade` - Record a trade
- `add_signal` - Add manual signal
- `update_prices` - Refresh price data
- `update_news` - Refresh news

### Obsidian Integration

1. Symlink or copy `obsidian/ai-trader` to your Obsidian vault
2. Use templates in `templates/` folder for consistent formatting
3. Weekly briefs auto-generate to `daily/YYYY-MM-DD-weekly.md`

## Data Sources

| Source | Data | Cost |
|--------|------|------|
| yfinance | Prices, fundamentals, news, earnings | Free |
| SEC EDGAR | Filings (10-K, 10-Q, 8-K) | Free |
| RSS Feeds | Market news | Free |
| Danelfin | AI scores | Free tier (manual entry) |
| Toggle AI | Insights | Free tier (manual entry) |

## Project Structure

```
ai-trader/
├── src/
│   ├── __init__.py
│   ├── db.py              # SQLite schema + operations
│   ├── cli.py             # Click CLI
│   ├── mcp_server.py      # MCP server for Claude
│   ├── fetchers/
│   │   ├── prices.py      # yfinance wrapper
│   │   ├── earnings.py    # Earnings calendar
│   │   └── news.py        # News aggregation
│   └── signals/
│       └── recommender.py # (Phase 2)
├── cron/
│   ├── daily_update.py    # Daily data refresh
│   └── weekly_brief.py    # Weekly recommendations
├── obsidian/
│   └── ai-trader/
│       ├── templates/     # Obsidian templates
│       ├── daily/         # Auto-generated briefs
│       ├── tickers/       # Per-ticker notes
│       ├── journal/       # Trade journal
│       └── earnings/      # Earnings analysis
├── data/
│   └── trader.db          # SQLite database
├── pyproject.toml
└── README.md
```

## License

MIT
