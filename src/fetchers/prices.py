"""Fetch price data from Yahoo Finance."""

from datetime import datetime, timedelta

import yfinance as yf

from src.db import get_watchlist, insert_prices


def fetch_ticker_prices(ticker: str, period: str = "1mo") -> list[dict]:
    """
    Fetch price history for a single ticker.

    Args:
        ticker: Stock ticker symbol
        period: yfinance period string (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)

    Returns:
        List of price records
    """
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period)

    prices = []
    for date_idx, row in hist.iterrows():
        prices.append(
            {
                "ticker": ticker.upper(),
                "date": date_idx.strftime("%Y-%m-%d"),
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"]),
            }
        )
    return prices


def fetch_ticker_info(ticker: str) -> dict:
    """
    Fetch basic info for a ticker.

    Returns dict with: name, sector, industry, marketCap, etc.
    """
    stock = yf.Ticker(ticker)
    info = stock.info
    return {
        "ticker": ticker.upper(),
        "name": info.get("longName") or info.get("shortName", ""),
        "sector": info.get("sector", ""),
        "industry": info.get("industry", ""),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "dividend_yield": info.get("dividendYield"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "avg_volume": info.get("averageVolume"),
    }


def fetch_multiple_tickers(tickers: list[str], period: str = "1mo") -> dict[str, list[dict]]:
    """
    Fetch prices for multiple tickers efficiently.

    Returns dict mapping ticker -> list of price records
    """
    result = {}
    # yfinance supports batch downloads
    tickers_str = " ".join(tickers)
    data = yf.download(tickers_str, period=period, group_by="ticker", progress=False)

    for ticker in tickers:
        ticker_upper = ticker.upper()
        try:
            if len(tickers) == 1:
                hist = data
            else:
                hist = data[ticker_upper]

            prices = []
            for date_idx, row in hist.iterrows():
                prices.append(
                    {
                        "ticker": ticker_upper,
                        "date": date_idx.strftime("%Y-%m-%d"),
                        "open": round(row["Open"], 2) if not row.isna()["Open"] else None,
                        "high": round(row["High"], 2) if not row.isna()["High"] else None,
                        "low": round(row["Low"], 2) if not row.isna()["Low"] else None,
                        "close": round(row["Close"], 2) if not row.isna()["Close"] else None,
                        "volume": int(row["Volume"]) if not row.isna()["Volume"] else None,
                    }
                )
            result[ticker_upper] = prices
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            result[ticker_upper] = []

    return result


def update_watchlist_prices(period: str = "5d") -> dict[str, int]:
    """
    Fetch and store prices for all active watchlist tickers.

    Returns dict mapping ticker -> count of records inserted
    """
    watchlist = get_watchlist(active_only=True)
    tickers = [w["ticker"] for w in watchlist]

    if not tickers:
        return {}

    all_prices = fetch_multiple_tickers(tickers, period=period)

    result = {}
    for ticker, prices in all_prices.items():
        if prices:
            count = insert_prices(prices)
            result[ticker] = count

    return result


def get_current_price(ticker: str) -> dict | None:
    """Get the current/latest price for a ticker."""
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1d")
    if hist.empty:
        return None

    row = hist.iloc[-1]
    return {
        "ticker": ticker.upper(),
        "date": hist.index[-1].strftime("%Y-%m-%d"),
        "open": round(row["Open"], 2),
        "high": round(row["High"], 2),
        "low": round(row["Low"], 2),
        "close": round(row["Close"], 2),
        "volume": int(row["Volume"]),
    }


if __name__ == "__main__":
    # Test fetching
    print("Testing price fetcher...")
    prices = fetch_ticker_prices("AAPL", period="5d")
    for p in prices:
        print(p)
