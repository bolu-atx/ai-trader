#!/usr/bin/env python3
"""Daily update script - Run via cron each evening after market close.

Recommended crontab entry (5 PM PT / 8 PM ET, Mon-Fri):
0 17 * * 1-5 cd /path/to/ai-trader && /path/to/python cron/daily_update.py >> logs/daily.log 2>&1
"""

import sys
from datetime import date
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import init_db, get_watchlist
from src.fetchers.prices import update_watchlist_prices
from src.fetchers.news import update_watchlist_news
from src.fetchers.earnings import update_watchlist_earnings


def main():
    """Run daily updates."""
    print(f"\n{'='*60}")
    print(f"Daily Update - {date.today().isoformat()}")
    print(f"{'='*60}\n")

    # Initialize DB if needed
    init_db()

    # Check watchlist
    watchlist = get_watchlist(active_only=True)
    if not watchlist:
        print("No tickers in watchlist. Add some with 'trader watchlist add TICKER'")
        return

    print(f"Updating {len(watchlist)} tickers: {', '.join(w['ticker'] for w in watchlist)}\n")

    # Update prices
    print("Fetching prices...")
    try:
        price_results = update_watchlist_prices(period="5d")
        for ticker, count in price_results.items():
            print(f"  {ticker}: {count} price records")
    except Exception as e:
        print(f"  Error fetching prices: {e}")

    # Update news
    print("\nFetching news...")
    try:
        news_results = update_watchlist_news(max_per_ticker=5)
        for ticker, count in news_results.items():
            print(f"  {ticker}: {count} articles")
    except Exception as e:
        print(f"  Error fetching news: {e}")

    # Update earnings calendar
    print("\nUpdating earnings calendar...")
    try:
        earnings = update_watchlist_earnings()
        for e in earnings:
            print(f"  {e['ticker']}: reports {e['report_date']}")
    except Exception as e:
        print(f"  Error updating earnings: {e}")

    print(f"\n{'='*60}")
    print("Daily update complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
