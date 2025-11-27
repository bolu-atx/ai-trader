"""MCP Server for AI Trader - Exposes tools for Claude integration."""

import json
from datetime import date
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.db import (
    init_db,
    get_watchlist,
    get_latest_price,
    get_price_history,
    get_latest_signals,
    get_upcoming_earnings,
    get_open_trades,
    get_trade_history,
    get_recent_news,
    get_latest_recommendations,
    add_to_watchlist,
    update_stance,
    log_trade,
    insert_signal,
)
from src.fetchers.prices import fetch_ticker_info, get_current_price, update_watchlist_prices
from src.fetchers.earnings import (
    get_earnings_date,
    get_analyst_estimates,
    get_watchlist_earnings_calendar,
)
from src.fetchers.news import fetch_ticker_news_yfinance, update_watchlist_news

# Initialize database on import
init_db()

# Create server
server = Server("ai-trader")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="get_watchlist",
            description="Get the current watchlist with tickers, stance (buy/hold/sell/watch), and metadata. Returns a list of all tracked stocks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "active_only": {
                        "type": "boolean",
                        "description": "Only show active tickers (default: true)",
                        "default": True,
                    }
                },
            },
        ),
        Tool(
            name="get_ticker_summary",
            description="Get a comprehensive summary for a single ticker including price, fundamentals, signals, earnings info, and recent news. Best for deep-diving into a specific stock.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., NVDA, AAPL)",
                    }
                },
                "required": ["ticker"],
            },
        ),
        Tool(
            name="get_earnings_calendar",
            description="Get upcoming earnings dates for watchlist stocks. Use this to identify which stocks are reporting soon.",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look ahead (default: 14)",
                        "default": 14,
                    }
                },
            },
        ),
        Tool(
            name="get_signals",
            description="Get the latest signals (Danelfin scores, sentiment, etc.) for a ticker.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol",
                    }
                },
                "required": ["ticker"],
            },
        ),
        Tool(
            name="get_recent_news",
            description="Get recent news articles for a ticker or all watchlist stocks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol (optional, omit for all watchlist news)",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back (default: 7)",
                        "default": 7,
                    },
                },
            },
        ),
        Tool(
            name="get_open_trades",
            description="Get all open (unclosed) trades from the trade journal.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_trade_history",
            description="Get trade history, optionally filtered by ticker.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Filter by ticker (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of trades to return (default: 20)",
                        "default": 20,
                    },
                },
            },
        ),
        Tool(
            name="get_recommendations",
            description="Get the latest AI-generated buy/hold/sell recommendations for watchlist stocks.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="add_to_watchlist",
            description="Add a new ticker to the watchlist.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol",
                    },
                    "stance": {
                        "type": "string",
                        "description": "Initial stance: buy, hold, sell, watch",
                        "enum": ["buy", "hold", "sell", "watch"],
                        "default": "watch",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Notes about why this stock is being tracked",
                    },
                },
                "required": ["ticker"],
            },
        ),
        Tool(
            name="update_stance",
            description="Update the stance (buy/hold/sell/watch) for a ticker.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol",
                    },
                    "stance": {
                        "type": "string",
                        "description": "New stance",
                        "enum": ["buy", "hold", "sell", "watch"],
                    },
                },
                "required": ["ticker", "stance"],
            },
        ),
        Tool(
            name="log_trade",
            description="Log a trade to the journal. Records the action, price, shares, and your thesis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol",
                    },
                    "action": {
                        "type": "string",
                        "description": "Trade action",
                        "enum": ["buy", "sell", "trim", "add"],
                    },
                    "price": {
                        "type": "number",
                        "description": "Trade price",
                    },
                    "shares": {
                        "type": "integer",
                        "description": "Number of shares",
                    },
                    "thesis": {
                        "type": "string",
                        "description": "Your reasoning for this trade",
                    },
                },
                "required": ["ticker", "action", "price", "shares", "thesis"],
            },
        ),
        Tool(
            name="add_signal",
            description="Manually add a signal (e.g., Danelfin score) for a ticker.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol",
                    },
                    "source": {
                        "type": "string",
                        "description": "Signal source (e.g., 'danelfin', 'toggle', 'manual')",
                    },
                    "score": {
                        "type": "number",
                        "description": "Signal score (e.g., 1-10 for Danelfin)",
                    },
                    "sentiment": {
                        "type": "string",
                        "description": "Sentiment: bullish, bearish, neutral",
                        "enum": ["bullish", "bearish", "neutral"],
                    },
                },
                "required": ["ticker", "source", "score"],
            },
        ),
        Tool(
            name="update_prices",
            description="Fetch and update prices for all watchlist tickers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": "Period to fetch: 1d, 5d, 1mo, 3mo",
                        "default": "5d",
                    }
                },
            },
        ),
        Tool(
            name="update_news",
            description="Fetch and update news for all watchlist tickers.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""

    if name == "get_watchlist":
        active_only = arguments.get("active_only", True)
        watchlist = get_watchlist(active_only=active_only)

        # Enrich with current prices
        for item in watchlist:
            try:
                price = get_current_price(item["ticker"])
                if price:
                    item["current_price"] = price["close"]
            except Exception:
                pass

        return [TextContent(type="text", text=json.dumps(watchlist, indent=2, default=str))]

    elif name == "get_ticker_summary":
        ticker = arguments["ticker"].upper()
        data = {"ticker": ticker, "timestamp": date.today().isoformat()}

        # Price
        try:
            price = get_current_price(ticker)
            if price:
                data["price"] = price
        except Exception:
            pass

        # Info
        try:
            info = fetch_ticker_info(ticker)
            data["info"] = info
        except Exception:
            pass

        # Signals
        signals = get_latest_signals(ticker)
        if signals:
            data["signals"] = signals

        # Earnings
        try:
            earnings_date = get_earnings_date(ticker)
            if earnings_date:
                data["next_earnings"] = earnings_date

            estimates = get_analyst_estimates(ticker)
            if estimates:
                data["analyst_estimates"] = estimates
        except Exception:
            pass

        # News
        try:
            news = fetch_ticker_news_yfinance(ticker, max_items=5)
            if news:
                data["recent_news"] = news
        except Exception:
            pass

        return [TextContent(type="text", text=json.dumps(data, indent=2, default=str))]

    elif name == "get_earnings_calendar":
        days = arguments.get("days", 14)
        calendar = get_watchlist_earnings_calendar(days=days)
        return [TextContent(type="text", text=json.dumps(calendar, indent=2, default=str))]

    elif name == "get_signals":
        ticker = arguments["ticker"].upper()
        signals = get_latest_signals(ticker)
        return [TextContent(type="text", text=json.dumps(signals, indent=2, default=str))]

    elif name == "get_recent_news":
        ticker = arguments.get("ticker")
        days = arguments.get("days", 7)

        if ticker:
            # Fetch fresh news for specific ticker
            news = fetch_ticker_news_yfinance(ticker.upper(), max_items=10)
        else:
            # Get from database for all tickers
            news = get_recent_news(days=days)

        return [TextContent(type="text", text=json.dumps(news, indent=2, default=str))]

    elif name == "get_open_trades":
        trades = get_open_trades()
        return [TextContent(type="text", text=json.dumps(trades, indent=2, default=str))]

    elif name == "get_trade_history":
        ticker = arguments.get("ticker")
        limit = arguments.get("limit", 20)
        trades = get_trade_history(ticker=ticker, limit=limit)
        return [TextContent(type="text", text=json.dumps(trades, indent=2, default=str))]

    elif name == "get_recommendations":
        recs = get_latest_recommendations()
        return [TextContent(type="text", text=json.dumps(recs, indent=2, default=str))]

    elif name == "add_to_watchlist":
        ticker = arguments["ticker"].upper()
        stance = arguments.get("stance", "watch")
        notes = arguments.get("notes", "")

        # Try to fetch info
        try:
            info = fetch_ticker_info(ticker)
            add_to_watchlist(
                ticker=ticker,
                name=info.get("name", ""),
                sector=info.get("sector", ""),
                stance=stance,
                notes=notes,
            )
            return [TextContent(type="text", text=f"Added {ticker} ({info.get('name', '')}) to watchlist with stance '{stance}'")]
        except Exception as e:
            add_to_watchlist(ticker=ticker, stance=stance, notes=notes)
            return [TextContent(type="text", text=f"Added {ticker} to watchlist with stance '{stance}' (couldn't fetch info: {e})")]

    elif name == "update_stance":
        ticker = arguments["ticker"].upper()
        stance = arguments["stance"]
        update_stance(ticker, stance)
        return [TextContent(type="text", text=f"Updated {ticker} stance to '{stance}'")]

    elif name == "log_trade":
        ticker = arguments["ticker"].upper()
        action = arguments["action"]
        price = arguments["price"]
        shares = arguments["shares"]
        thesis = arguments["thesis"]

        # Get signals snapshot
        signals = get_latest_signals(ticker)
        signals_json = json.dumps(signals) if signals else None

        trade_id = log_trade(
            ticker=ticker,
            action=action,
            price=price,
            shares=shares,
            thesis=thesis,
            signals_snapshot=signals_json,
        )
        return [TextContent(type="text", text=f"Logged trade #{trade_id}: {action.upper()} {shares} {ticker} @ ${price:.2f}")]

    elif name == "add_signal":
        ticker = arguments["ticker"].upper()
        source = arguments["source"]
        score = arguments["score"]
        sentiment = arguments.get("sentiment")

        insert_signal(ticker=ticker, source=source, score=score, sentiment=sentiment)
        return [TextContent(type="text", text=f"Added {source} signal for {ticker}: {score}")]

    elif name == "update_prices":
        period = arguments.get("period", "5d")
        result = update_watchlist_prices(period=period)
        return [TextContent(type="text", text=f"Updated prices for {len(result)} tickers: {json.dumps(result)}")]

    elif name == "update_news":
        result = update_watchlist_news()
        return [TextContent(type="text", text=f"Updated news for {len(result)} tickers: {json.dumps(result)}")]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
