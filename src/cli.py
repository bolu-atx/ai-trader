"""CLI interface for ai-trader using Typer."""

import json
from datetime import date
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from src.db import (
    init_db,
    add_to_watchlist,
    remove_from_watchlist,
    get_watchlist,
    update_stance,
    get_latest_price,
    get_price_history,
    get_latest_signals,
    get_upcoming_earnings,
    log_trade,
    get_open_trades,
    get_trade_history,
    get_recent_news,
    get_latest_recommendations,
    insert_signal,
)
from src.fetchers.prices import (
    fetch_ticker_prices,
    fetch_ticker_info,
    update_watchlist_prices,
    get_current_price,
)
from src.fetchers.earnings import (
    get_earnings_date,
    get_analyst_estimates,
    get_watchlist_earnings_calendar,
)
from src.fetchers.news import fetch_ticker_news_yfinance, update_watchlist_news

console = Console()

# Main app
app = typer.Typer(help="AI Trader - Investment research assistant.")

# Sub-commands
watchlist_app = typer.Typer(help="Manage your watchlist.")
price_app = typer.Typer(help="Price data commands.")
earnings_app = typer.Typer(help="Earnings calendar commands.")
news_app = typer.Typer(help="News commands.")
trade_app = typer.Typer(help="Trade journal commands.")
signal_app = typer.Typer(help="Signal management commands.")

app.add_typer(watchlist_app, name="watchlist")
app.add_typer(price_app, name="price")
app.add_typer(earnings_app, name="earnings")
app.add_typer(news_app, name="news")
app.add_typer(trade_app, name="trade")
app.add_typer(signal_app, name="signal")


# =============================================================================
# Database Commands
# =============================================================================


@app.command()
def init(
    db: Annotated[Optional[Path], typer.Option(help="Path to database file")] = None,
):
    """Initialize the database."""
    init_db(db)
    console.print("[green]Database initialized successfully.[/green]")


# =============================================================================
# Watchlist Commands
# =============================================================================


@watchlist_app.command("add")
def watchlist_add(
    ticker: Annotated[str, typer.Argument(help="Stock ticker symbol")],
    stance: Annotated[str, typer.Option(help="Initial stance: buy, hold, sell, watch")] = "watch",
    notes: Annotated[str, typer.Option(help="Notes about this ticker")] = "",
):
    """Add a ticker to the watchlist."""
    try:
        info = fetch_ticker_info(ticker)
        add_to_watchlist(
            ticker=ticker,
            name=info.get("name", ""),
            sector=info.get("sector", ""),
            stance=stance,
            notes=notes,
        )
        console.print(f"[green]Added {ticker.upper()} ({info.get('name', '')}) to watchlist[/green]")
    except Exception as e:
        add_to_watchlist(ticker=ticker, stance=stance, notes=notes)
        console.print(f"[yellow]Added {ticker.upper()} to watchlist (couldn't fetch info: {e})[/yellow]")


@watchlist_app.command("remove")
def watchlist_remove(
    ticker: Annotated[str, typer.Argument(help="Stock ticker symbol")],
):
    """Remove a ticker from the watchlist."""
    remove_from_watchlist(ticker)
    console.print(f"[yellow]Removed {ticker.upper()} from watchlist[/yellow]")


@watchlist_app.command("list")
def watchlist_list(
    show_all: Annotated[bool, typer.Option("--all", help="Show inactive tickers too")] = False,
):
    """List all tickers in the watchlist."""
    items = get_watchlist(active_only=not show_all)

    if not items:
        console.print("[yellow]Watchlist is empty. Add tickers with 'trader watchlist add TICKER'[/yellow]")
        return

    table = Table(title="Watchlist")
    table.add_column("Ticker", style="cyan")
    table.add_column("Name")
    table.add_column("Sector")
    table.add_column("Stance", style="bold")
    table.add_column("Added")
    table.add_column("Notes")

    stance_colors = {
        "buy": "green",
        "hold": "yellow",
        "sell": "red",
        "watch": "blue",
    }

    for item in items:
        stance = item["stance"]
        stance_color = stance_colors.get(stance, "white")
        table.add_row(
            item["ticker"],
            item["name"] or "",
            item["sector"] or "",
            f"[{stance_color}]{stance}[/{stance_color}]",
            item["added_date"],
            item["notes"] or "",
        )

    console.print(table)


@watchlist_app.command("stance")
def watchlist_stance(
    ticker: Annotated[str, typer.Argument(help="Stock ticker symbol")],
    stance: Annotated[str, typer.Argument(help="New stance: buy, hold, sell, watch")],
):
    """Update stance for a ticker."""
    if stance not in ("buy", "hold", "sell", "watch"):
        console.print(f"[red]Invalid stance: {stance}. Must be buy, hold, sell, or watch.[/red]")
        raise typer.Exit(1)
    update_stance(ticker, stance)
    console.print(f"[green]Updated {ticker.upper()} stance to {stance}[/green]")


# =============================================================================
# Price Commands
# =============================================================================


@price_app.command("get")
def price_get(
    ticker: Annotated[str, typer.Argument(help="Stock ticker symbol")],
):
    """Get current price for a ticker."""
    p = get_current_price(ticker)
    if p:
        console.print(f"[cyan]{ticker.upper()}[/cyan] @ {p['date']}")
        console.print(f"  Open:   ${p['open']:.2f}")
        console.print(f"  High:   ${p['high']:.2f}")
        console.print(f"  Low:    ${p['low']:.2f}")
        console.print(f"  Close:  ${p['close']:.2f}")
        console.print(f"  Volume: {p['volume']:,}")
    else:
        console.print(f"[red]No price data for {ticker.upper()}[/red]")


@price_app.command("update")
def price_update(
    period: Annotated[str, typer.Option(help="Period to fetch: 1d, 5d, 1mo, 3mo")] = "5d",
):
    """Update prices for all watchlist tickers."""
    console.print(f"Fetching {period} prices for watchlist...")
    result = update_watchlist_prices(period=period)

    if result:
        for ticker, count in result.items():
            console.print(f"  [green]{ticker}[/green]: {count} records")
    else:
        console.print("[yellow]No tickers in watchlist[/yellow]")


# =============================================================================
# Earnings Commands
# =============================================================================


@earnings_app.command("calendar")
def earnings_calendar(
    days: Annotated[int, typer.Option(help="Days to look ahead")] = 30,
):
    """Show upcoming earnings for watchlist."""
    calendar = get_watchlist_earnings_calendar(days=days)

    if not calendar:
        console.print(f"[yellow]No earnings scheduled in the next {days} days[/yellow]")
        return

    table = Table(title=f"Upcoming Earnings (next {days} days)")
    table.add_column("Date", style="cyan")
    table.add_column("Days")
    table.add_column("Ticker", style="bold")
    table.add_column("Name")
    table.add_column("Stance")

    for e in calendar:
        table.add_row(
            e["report_date"],
            str(e["days_until"]),
            e["ticker"],
            e["name"],
            e["stance"],
        )

    console.print(table)


@earnings_app.command("info")
def earnings_info(
    ticker: Annotated[str, typer.Argument(help="Stock ticker symbol")],
):
    """Get earnings info for a ticker."""
    date_info = get_earnings_date(ticker)
    estimates = get_analyst_estimates(ticker)

    console.print(f"\n[bold cyan]{ticker.upper()} Earnings Info[/bold cyan]")

    if date_info:
        console.print(f"  Next Earnings: {date_info.get('report_date', 'Unknown')}")

    if estimates:
        console.print(f"\n  [bold]Analyst Estimates:[/bold]")
        console.print(f"    Forward EPS:     {estimates.get('forward_eps')}")
        console.print(f"    Trailing EPS:    {estimates.get('trailing_eps')}")
        console.print(f"    Earnings Growth: {estimates.get('earnings_growth')}")
        console.print(f"    Revenue Growth:  {estimates.get('revenue_growth')}")
        console.print(f"    Recommendation:  {estimates.get('recommendation')}")
        console.print(f"    Price Target:    ${estimates.get('target_mean_price')} (${estimates.get('target_low_price')} - ${estimates.get('target_high_price')})")
        console.print(f"    Analysts:        {estimates.get('number_of_analysts')}")


# =============================================================================
# News Commands
# =============================================================================


@news_app.command("get")
def news_get(
    ticker: Annotated[str, typer.Argument(help="Stock ticker symbol")],
    count: Annotated[int, typer.Option(help="Number of articles")] = 5,
):
    """Get recent news for a ticker."""
    articles = fetch_ticker_news_yfinance(ticker, max_items=count)

    if not articles:
        console.print(f"[yellow]No news found for {ticker.upper()}[/yellow]")
        return

    console.print(f"\n[bold cyan]{ticker.upper()} News[/bold cyan]\n")
    for article in articles:
        console.print(f"[dim]{article['date']}[/dim] [{article['source']}]")
        console.print(f"  {article['headline']}")
        if article.get("summary"):
            console.print(f"  [dim]{article['summary'][:100]}...[/dim]")
        console.print()


@news_app.command("update")
def news_update():
    """Update news for all watchlist tickers."""
    console.print("Fetching news for watchlist...")
    result = update_watchlist_news()

    if result:
        for ticker, count in result.items():
            console.print(f"  [green]{ticker}[/green]: {count} articles")
    else:
        console.print("[yellow]No tickers in watchlist[/yellow]")


# =============================================================================
# Trade Commands
# =============================================================================


@trade_app.command("log")
def trade_log(
    ticker: Annotated[str, typer.Argument(help="Stock ticker symbol")],
    action: Annotated[str, typer.Argument(help="Trade action: buy, sell, trim, add")],
    price: Annotated[float, typer.Argument(help="Trade price")],
    shares: Annotated[int, typer.Argument(help="Number of shares")],
    thesis: Annotated[str, typer.Option(prompt=True, help="Your reasoning for this trade")] = "",
):
    """Log a new trade."""
    if action not in ("buy", "sell", "trim", "add"):
        console.print(f"[red]Invalid action: {action}. Must be buy, sell, trim, or add.[/red]")
        raise typer.Exit(1)

    # Capture current signals as snapshot
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

    console.print(f"[green]Logged trade #{trade_id}: {action.upper()} {shares} {ticker.upper()} @ ${price:.2f}[/green]")


@trade_app.command("open")
def trade_open():
    """Show open trades."""
    trades = get_open_trades()

    if not trades:
        console.print("[yellow]No open trades[/yellow]")
        return

    table = Table(title="Open Trades")
    table.add_column("ID")
    table.add_column("Date")
    table.add_column("Ticker", style="cyan")
    table.add_column("Action")
    table.add_column("Price")
    table.add_column("Shares")
    table.add_column("Thesis")

    for t in trades:
        table.add_row(
            str(t["id"]),
            t["date"],
            t["ticker"],
            t["action"],
            f"${t['price']:.2f}",
            str(t["shares"]),
            (t["thesis"] or "")[:30] + "..." if len(t.get("thesis") or "") > 30 else (t["thesis"] or ""),
        )

    console.print(table)


@trade_app.command("history")
def trade_history(
    ticker: Annotated[Optional[str], typer.Option(help="Filter by ticker")] = None,
    limit: Annotated[int, typer.Option(help="Number of trades to show")] = 20,
):
    """Show trade history."""
    trades = get_trade_history(ticker=ticker, limit=limit)

    if not trades:
        console.print("[yellow]No trades found[/yellow]")
        return

    table = Table(title="Trade History")
    table.add_column("ID")
    table.add_column("Date")
    table.add_column("Ticker", style="cyan")
    table.add_column("Action")
    table.add_column("Price")
    table.add_column("Shares")
    table.add_column("Return")

    for t in trades:
        ret = t.get("outcome_return")
        ret_str = f"{ret:+.1f}%" if ret is not None else "-"
        ret_color = "green" if ret and ret > 0 else "red" if ret and ret < 0 else "white"

        table.add_row(
            str(t["id"]),
            t["date"],
            t["ticker"],
            t["action"],
            f"${t['price']:.2f}",
            str(t["shares"]),
            f"[{ret_color}]{ret_str}[/{ret_color}]",
        )

    console.print(table)


# =============================================================================
# Signal Commands
# =============================================================================


@signal_app.command("add")
def signal_add(
    ticker: Annotated[str, typer.Argument(help="Stock ticker symbol")],
    source: Annotated[str, typer.Argument(help="Signal source (e.g., danelfin, toggle)")],
    score: Annotated[float, typer.Argument(help="Signal score")],
    sentiment: Annotated[Optional[str], typer.Option(help="Sentiment: bullish, bearish, neutral")] = None,
):
    """Manually add a signal (e.g., Danelfin score)."""
    if sentiment and sentiment not in ("bullish", "bearish", "neutral"):
        console.print(f"[red]Invalid sentiment: {sentiment}. Must be bullish, bearish, or neutral.[/red]")
        raise typer.Exit(1)
    insert_signal(ticker=ticker, source=source, score=score, sentiment=sentiment)
    console.print(f"[green]Added {source} signal for {ticker.upper()}: {score}[/green]")


@signal_app.command("show")
def signal_show(
    ticker: Annotated[str, typer.Argument(help="Stock ticker symbol")],
):
    """Show latest signals for a ticker."""
    signals = get_latest_signals(ticker)

    if not signals:
        console.print(f"[yellow]No signals for {ticker.upper()}[/yellow]")
        return

    table = Table(title=f"{ticker.upper()} Signals")
    table.add_column("Source")
    table.add_column("Date")
    table.add_column("Score")
    table.add_column("Sentiment")

    for s in signals:
        table.add_row(
            s["source"],
            s["date"],
            str(s["score"]) if s["score"] else "-",
            s["sentiment"] or "-",
        )

    console.print(table)


# =============================================================================
# Summary Command
# =============================================================================


@app.command()
def summary(
    ticker: Annotated[str, typer.Argument(help="Stock ticker symbol")],
):
    """Get a full summary for a ticker (for AI consumption)."""
    ticker = ticker.upper()

    # Gather all data
    data = {
        "ticker": ticker,
        "timestamp": date.today().isoformat(),
    }

    # Price
    price = get_current_price(ticker)
    if price:
        data["price"] = price

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
    earnings_date = get_earnings_date(ticker)
    if earnings_date:
        data["next_earnings"] = earnings_date

    estimates = get_analyst_estimates(ticker)
    if estimates:
        data["analyst_estimates"] = estimates

    # News
    news = fetch_ticker_news_yfinance(ticker, max_items=5)
    if news:
        data["recent_news"] = news

    # Output as JSON for AI consumption
    console.print_json(json.dumps(data, indent=2, default=str))


# =============================================================================
# Recommendations Command
# =============================================================================


@app.command()
def recommendations():
    """Show latest AI recommendations."""
    recs = get_latest_recommendations()

    if not recs:
        console.print("[yellow]No recommendations yet. Run weekly update to generate.[/yellow]")
        return

    table = Table(title="Latest Recommendations")
    table.add_column("Ticker", style="cyan")
    table.add_column("Name")
    table.add_column("Recommendation", style="bold")
    table.add_column("Confidence")
    table.add_column("Rationale")

    rec_colors = {
        "strong_buy": "bold green",
        "buy": "green",
        "hold": "yellow",
        "sell": "red",
        "strong_sell": "bold red",
    }

    for r in recs:
        rec = r["recommendation"]
        color = rec_colors.get(rec, "white")
        table.add_row(
            r["ticker"],
            r.get("name") or "",
            f"[{color}]{rec.upper()}[/{color}]",
            f"{r['confidence']:.0%}" if r.get("confidence") else "-",
            (r["rationale"] or "")[:40] + "..." if len(r.get("rationale") or "") > 40 else (r["rationale"] or ""),
        )

    console.print(table)


# Entry point
def cli():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    cli()
