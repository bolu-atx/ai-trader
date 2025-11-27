"""Fetch news from various sources."""

import feedparser
from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf

from src.db import get_watchlist, insert_news


# RSS feeds for financial news (free sources)
RSS_FEEDS = {
    "yahoo_finance": "https://finance.yahoo.com/news/rssindex",
    "seeking_alpha": "https://seekingalpha.com/market_currents.xml",
    "marketwatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "cnbc": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
}


def fetch_ticker_news_yfinance(ticker: str, max_items: int = 10) -> list[dict]:
    """
    Fetch news for a ticker using yfinance.

    Returns list of news items.
    """
    stock = yf.Ticker(ticker)

    try:
        news = stock.news
        if not news:
            return []

        items = []
        for article in news[:max_items]:
            # Parse publish time
            pub_time = article.get("providerPublishTime")
            if pub_time:
                pub_date = datetime.fromtimestamp(pub_time).strftime("%Y-%m-%d")
            else:
                pub_date = datetime.now().strftime("%Y-%m-%d")

            items.append(
                {
                    "ticker": ticker.upper(),
                    "headline": article.get("title", ""),
                    "summary": article.get("summary", ""),
                    "source": article.get("publisher", "Yahoo Finance"),
                    "url": article.get("link", ""),
                    "date": pub_date,
                    "sentiment": None,  # Could add sentiment analysis here
                }
            )
        return items
    except Exception as e:
        print(f"Error fetching news for {ticker}: {e}")
        return []


def fetch_rss_feed(feed_url: str, max_items: int = 20) -> list[dict]:
    """
    Fetch and parse an RSS feed.

    Returns list of news items.
    """
    try:
        feed = feedparser.parse(feed_url)
        items = []

        for entry in feed.entries[:max_items]:
            # Parse date
            pub_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d")
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                pub_date = datetime(*entry.updated_parsed[:6]).strftime("%Y-%m-%d")
            else:
                pub_date = datetime.now().strftime("%Y-%m-%d")

            items.append(
                {
                    "ticker": None,  # General market news
                    "headline": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:500],  # Truncate long summaries
                    "source": feed.feed.get("title", "RSS"),
                    "url": entry.get("link", ""),
                    "date": pub_date,
                    "sentiment": None,
                }
            )
        return items
    except Exception as e:
        print(f"Error fetching RSS feed {feed_url}: {e}")
        return []


def fetch_market_news(sources: list[str] | None = None, max_per_source: int = 10) -> list[dict]:
    """
    Fetch general market news from RSS feeds.

    Args:
        sources: List of source keys from RSS_FEEDS, or None for all
        max_per_source: Max items per source

    Returns list of news items.
    """
    if sources is None:
        sources = list(RSS_FEEDS.keys())

    all_news = []
    for source in sources:
        if source in RSS_FEEDS:
            news = fetch_rss_feed(RSS_FEEDS[source], max_items=max_per_source)
            all_news.extend(news)

    # Sort by date descending
    all_news.sort(key=lambda x: x["date"], reverse=True)
    return all_news


def update_watchlist_news(max_per_ticker: int = 5) -> dict[str, int]:
    """
    Fetch and store news for all active watchlist tickers.

    Returns dict mapping ticker -> count of news items stored.
    """
    watchlist = get_watchlist(active_only=True)
    result = {}

    for item in watchlist:
        ticker = item["ticker"]
        news_items = fetch_ticker_news_yfinance(ticker, max_items=max_per_ticker)

        count = 0
        for news in news_items:
            try:
                insert_news(
                    headline=news["headline"],
                    source=news["source"],
                    url=news["url"],
                    ticker=news["ticker"],
                    summary=news["summary"],
                    sentiment=news["sentiment"],
                    news_date=news["date"],
                )
                count += 1
            except Exception:
                pass  # Duplicate or error

        result[ticker] = count

    return result


def search_news_for_tickers(
    tickers: list[str], keywords: list[str] | None = None
) -> list[dict]:
    """
    Search for news mentioning specific tickers or keywords.

    This is a simple implementation - could be enhanced with
    actual news API (NewsAPI, etc.) for better results.
    """
    all_news = []

    for ticker in tickers:
        news = fetch_ticker_news_yfinance(ticker)
        all_news.extend(news)

    # If keywords provided, filter
    if keywords:
        keywords_lower = [k.lower() for k in keywords]
        filtered = []
        for item in all_news:
            text = f"{item['headline']} {item['summary']}".lower()
            if any(kw in text for kw in keywords_lower):
                filtered.append(item)
        return filtered

    return all_news


if __name__ == "__main__":
    # Test fetching
    print("Testing news fetcher...")

    print("\nNVDA news (yfinance):")
    for news in fetch_ticker_news_yfinance("NVDA", max_items=3):
        print(f"  - {news['date']}: {news['headline'][:60]}...")

    print("\nMarket news (RSS):")
    for news in fetch_market_news(sources=["yahoo_finance"], max_per_source=3):
        print(f"  - {news['date']}: {news['headline'][:60]}...")
