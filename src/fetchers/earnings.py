"""Fetch earnings calendar and data."""

from datetime import datetime, timedelta

import yfinance as yf

from src.db import get_watchlist, insert_earnings


def get_earnings_date(ticker: str) -> dict | None:
    """
    Get upcoming earnings date for a ticker.

    Returns dict with earnings info or None if not available.
    """
    stock = yf.Ticker(ticker)

    # Get earnings dates
    try:
        calendar = stock.calendar
        if calendar is None or calendar.empty:
            return None

        # calendar can be a DataFrame or dict depending on yfinance version
        if hasattr(calendar, "to_dict"):
            cal_dict = calendar.to_dict()
            earnings_date = cal_dict.get("Earnings Date", [None])[0]
        else:
            earnings_date = calendar.get("Earnings Date")

        if earnings_date is None:
            return None

        # Handle if it's a list
        if isinstance(earnings_date, list):
            earnings_date = earnings_date[0] if earnings_date else None

        if earnings_date is None:
            return None

        # Convert to string if datetime
        if hasattr(earnings_date, "strftime"):
            earnings_date = earnings_date.strftime("%Y-%m-%d")

        return {
            "ticker": ticker.upper(),
            "report_date": earnings_date,
        }
    except Exception as e:
        print(f"Error getting earnings date for {ticker}: {e}")
        return None


def get_earnings_history(ticker: str, limit: int = 8) -> list[dict]:
    """
    Get historical earnings for a ticker.

    Returns list of earnings records (most recent first).
    """
    stock = yf.Ticker(ticker)

    try:
        # Get earnings history
        earnings = stock.earnings_history
        if earnings is None or earnings.empty:
            return []

        records = []
        for _, row in earnings.head(limit).iterrows():
            records.append(
                {
                    "ticker": ticker.upper(),
                    "report_date": row.name.strftime("%Y-%m-%d")
                    if hasattr(row.name, "strftime")
                    else str(row.name),
                    "estimate_eps": row.get("epsEstimate"),
                    "actual_eps": row.get("epsActual"),
                    "surprise_pct": row.get("surprisePercent"),
                }
            )
        return records
    except Exception as e:
        print(f"Error getting earnings history for {ticker}: {e}")
        return []


def get_analyst_estimates(ticker: str) -> dict | None:
    """
    Get analyst estimates for a ticker.

    Returns dict with EPS and revenue estimates.
    """
    stock = yf.Ticker(ticker)

    try:
        info = stock.info
        return {
            "ticker": ticker.upper(),
            "forward_eps": info.get("forwardEps"),
            "trailing_eps": info.get("trailingEps"),
            "peg_ratio": info.get("pegRatio"),
            "earnings_growth": info.get("earningsGrowth"),
            "revenue_growth": info.get("revenueGrowth"),
            "recommendation": info.get("recommendationKey"),
            "target_mean_price": info.get("targetMeanPrice"),
            "target_high_price": info.get("targetHighPrice"),
            "target_low_price": info.get("targetLowPrice"),
            "number_of_analysts": info.get("numberOfAnalystOpinions"),
        }
    except Exception as e:
        print(f"Error getting estimates for {ticker}: {e}")
        return None


def update_watchlist_earnings() -> list[dict]:
    """
    Fetch and store upcoming earnings for all active watchlist tickers.

    Returns list of upcoming earnings.
    """
    watchlist = get_watchlist(active_only=True)
    upcoming = []

    for item in watchlist:
        ticker = item["ticker"]
        earnings = get_earnings_date(ticker)
        if earnings and earnings.get("report_date"):
            # Store in database
            insert_earnings(
                ticker=ticker,
                report_date=earnings["report_date"],
            )
            upcoming.append(earnings)

    return upcoming


def get_watchlist_earnings_calendar(days: int = 30) -> list[dict]:
    """
    Get earnings calendar for watchlist tickers in the next N days.

    Returns list sorted by report date.
    """
    watchlist = get_watchlist(active_only=True)
    calendar = []

    today = datetime.now().date()
    end_date = today + timedelta(days=days)

    for item in watchlist:
        ticker = item["ticker"]
        earnings = get_earnings_date(ticker)

        if earnings and earnings.get("report_date"):
            try:
                report_date = datetime.strptime(earnings["report_date"], "%Y-%m-%d").date()
                if today <= report_date <= end_date:
                    calendar.append(
                        {
                            "ticker": ticker,
                            "name": item.get("name", ""),
                            "report_date": earnings["report_date"],
                            "days_until": (report_date - today).days,
                            "stance": item.get("stance", "hold"),
                        }
                    )
            except ValueError:
                continue

    # Sort by report date
    calendar.sort(key=lambda x: x["report_date"])
    return calendar


if __name__ == "__main__":
    # Test fetching
    print("Testing earnings fetcher...")

    print("\nNVDA earnings date:")
    print(get_earnings_date("NVDA"))

    print("\nNVDA earnings history:")
    for e in get_earnings_history("NVDA", limit=4):
        print(e)

    print("\nNVDA analyst estimates:")
    print(get_analyst_estimates("NVDA"))
