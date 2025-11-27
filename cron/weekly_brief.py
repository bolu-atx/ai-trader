#!/usr/bin/env python3
"""Weekly brief generator - Run Sunday evening to prepare for the week.

Generates:
1. Weekly recommendations based on signals
2. Earnings preview for the week
3. Markdown brief for Obsidian

Recommended crontab entry (Sunday 6 PM):
0 18 * * 0 cd /path/to/ai-trader && /path/to/python cron/weekly_brief.py >> logs/weekly.log 2>&1
"""

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import (
    init_db,
    get_watchlist,
    get_latest_signals,
    get_latest_price,
    get_recent_news,
    insert_recommendation,
)
from src.fetchers.prices import update_watchlist_prices, fetch_ticker_info
from src.fetchers.earnings import get_watchlist_earnings_calendar, get_analyst_estimates
from src.fetchers.news import update_watchlist_news

# Obsidian vault path - UPDATE THIS
OBSIDIAN_PATH = Path(__file__).parent.parent / "obsidian" / "ai-trader"


def generate_recommendation(ticker: str, signals: list[dict], estimates: dict | None) -> dict:
    """
    Generate a recommendation based on available signals.

    This is a simple rule-based system. You can enhance this with:
    - More sophisticated scoring
    - LLM-based analysis
    - Additional signal sources
    """
    score = 5.0  # Neutral starting point
    factors = []

    # Factor in Danelfin score if available
    for signal in signals:
        if signal["source"] == "danelfin" and signal["score"]:
            danelfin_score = signal["score"]
            if danelfin_score >= 8:
                score += 2
                factors.append(f"Strong Danelfin score ({danelfin_score}/10)")
            elif danelfin_score >= 6:
                score += 1
                factors.append(f"Good Danelfin score ({danelfin_score}/10)")
            elif danelfin_score <= 3:
                score -= 2
                factors.append(f"Weak Danelfin score ({danelfin_score}/10)")
            elif danelfin_score <= 5:
                score -= 1
                factors.append(f"Below-average Danelfin score ({danelfin_score}/10)")

        # Factor in sentiment
        if signal.get("sentiment"):
            if signal["sentiment"] == "bullish":
                score += 0.5
                factors.append(f"Bullish {signal['source']} sentiment")
            elif signal["sentiment"] == "bearish":
                score -= 0.5
                factors.append(f"Bearish {signal['source']} sentiment")

    # Factor in analyst estimates
    if estimates:
        rec = estimates.get("recommendation", "").lower()
        if rec in ["strong_buy", "buy"]:
            score += 1
            factors.append(f"Analyst consensus: {rec}")
        elif rec in ["sell", "strong_sell"]:
            score -= 1
            factors.append(f"Analyst consensus: {rec}")

        # Earnings growth
        eg = estimates.get("earnings_growth")
        if eg and eg > 0.2:
            score += 0.5
            factors.append(f"Strong earnings growth ({eg:.0%})")
        elif eg and eg < -0.1:
            score -= 0.5
            factors.append(f"Negative earnings growth ({eg:.0%})")

    # Convert score to recommendation
    if score >= 8:
        rec = "strong_buy"
    elif score >= 6.5:
        rec = "buy"
    elif score >= 4:
        rec = "hold"
    elif score >= 2.5:
        rec = "sell"
    else:
        rec = "strong_sell"

    # Confidence based on number of factors
    confidence = min(0.3 + (len(factors) * 0.15), 0.95)

    return {
        "recommendation": rec,
        "confidence": confidence,
        "score": score,
        "factors": factors,
    }


def generate_weekly_markdown(
    watchlist: list[dict],
    recommendations: dict[str, dict],
    earnings_calendar: list[dict],
) -> str:
    """Generate weekly brief markdown for Obsidian."""
    today = date.today()
    week_end = today + timedelta(days=7)

    lines = [
        f"# Weekly Brief - {today.strftime('%B %d, %Y')}",
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "---",
        "",
        "## Summary",
        "",
        f"- **Watchlist**: {len(watchlist)} tickers",
        f"- **Earnings this week**: {len([e for e in earnings_calendar if e['days_until'] <= 7])}",
        "",
    ]

    # Recommendations summary
    rec_counts = {"strong_buy": 0, "buy": 0, "hold": 0, "sell": 0, "strong_sell": 0}
    for rec in recommendations.values():
        rec_counts[rec["recommendation"]] += 1

    lines.extend([
        "### Recommendations Breakdown",
        "",
        f"- Strong Buy: {rec_counts['strong_buy']}",
        f"- Buy: {rec_counts['buy']}",
        f"- Hold: {rec_counts['hold']}",
        f"- Sell: {rec_counts['sell']}",
        f"- Strong Sell: {rec_counts['strong_sell']}",
        "",
        "---",
        "",
        "## Earnings This Week",
        "",
    ])

    week_earnings = [e for e in earnings_calendar if e["days_until"] <= 7]
    if week_earnings:
        lines.append("| Date | Ticker | Name | Stance |")
        lines.append("|------|--------|------|--------|")
        for e in week_earnings:
            lines.append(f"| {e['report_date']} | **{e['ticker']}** | {e['name']} | {e['stance']} |")
    else:
        lines.append("*No earnings scheduled this week*")

    lines.extend(["", "---", "", "## Watchlist Detail", ""])

    # Detail for each ticker
    for item in sorted(watchlist, key=lambda x: recommendations.get(x["ticker"], {}).get("score", 5), reverse=True):
        ticker = item["ticker"]
        rec = recommendations.get(ticker, {})

        lines.extend([
            f"### {ticker} - {item.get('name', '')}",
            "",
            f"**Sector**: {item.get('sector', 'N/A')}",
            f"**Current Stance**: {item.get('stance', 'N/A')}",
            f"**Recommendation**: {rec.get('recommendation', 'N/A').upper()} ({rec.get('confidence', 0):.0%} confidence)",
            "",
        ])

        if rec.get("factors"):
            lines.append("**Factors**:")
            for factor in rec["factors"]:
                lines.append(f"- {factor}")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Footer
    lines.extend([
        "## Notes",
        "",
        "*Add your observations here*",
        "",
        "---",
        "",
        f"[[{(today - timedelta(days=7)).strftime('%Y-%m-%d')}-weekly|Previous Week]]",
    ])

    return "\n".join(lines)


def main():
    """Generate weekly brief and recommendations."""
    print(f"\n{'='*60}")
    print(f"Weekly Brief Generator - {date.today().isoformat()}")
    print(f"{'='*60}\n")

    # Initialize
    init_db()

    # First, update data
    print("Updating data...")
    update_watchlist_prices(period="1mo")
    update_watchlist_news(max_per_ticker=10)

    # Get watchlist
    watchlist = get_watchlist(active_only=True)
    if not watchlist:
        print("No tickers in watchlist!")
        return

    print(f"\nProcessing {len(watchlist)} tickers...\n")

    # Generate recommendations
    recommendations = {}
    for item in watchlist:
        ticker = item["ticker"]
        print(f"  Analyzing {ticker}...")

        signals = get_latest_signals(ticker)
        try:
            estimates = get_analyst_estimates(ticker)
        except Exception:
            estimates = None

        rec = generate_recommendation(ticker, signals, estimates)
        recommendations[ticker] = rec

        # Store in database
        insert_recommendation(
            ticker=ticker,
            recommendation=rec["recommendation"],
            confidence=rec["confidence"],
            rationale="; ".join(rec["factors"]) if rec["factors"] else "Insufficient data",
            factors=json.dumps(rec["factors"]),
        )

        print(f"    -> {rec['recommendation'].upper()} ({rec['confidence']:.0%})")

    # Get earnings calendar
    earnings_calendar = get_watchlist_earnings_calendar(days=14)

    # Generate markdown
    print("\nGenerating Obsidian markdown...")
    markdown = generate_weekly_markdown(watchlist, recommendations, earnings_calendar)

    # Write to Obsidian
    OBSIDIAN_PATH.mkdir(parents=True, exist_ok=True)
    daily_path = OBSIDIAN_PATH / "daily"
    daily_path.mkdir(exist_ok=True)

    filename = f"{date.today().isoformat()}-weekly.md"
    filepath = daily_path / filename

    with open(filepath, "w") as f:
        f.write(markdown)

    print(f"Written to: {filepath}")

    # Print summary
    print(f"\n{'='*60}")
    print("Weekly Brief Summary")
    print(f"{'='*60}")

    print("\nTop Picks (Buy/Strong Buy):")
    buys = [(t, r) for t, r in recommendations.items() if r["recommendation"] in ["buy", "strong_buy"]]
    buys.sort(key=lambda x: x[1]["score"], reverse=True)
    for ticker, rec in buys[:5]:
        print(f"  {ticker}: {rec['recommendation'].upper()} ({rec['confidence']:.0%})")

    print("\nCaution (Sell/Strong Sell):")
    sells = [(t, r) for t, r in recommendations.items() if r["recommendation"] in ["sell", "strong_sell"]]
    sells.sort(key=lambda x: x[1]["score"])
    for ticker, rec in sells[:5]:
        print(f"  {ticker}: {rec['recommendation'].upper()} ({rec['confidence']:.0%})")

    if earnings_calendar:
        print("\nUpcoming Earnings (next 7 days):")
        for e in earnings_calendar:
            if e["days_until"] <= 7:
                print(f"  {e['report_date']}: {e['ticker']} ({e['name']})")

    print(f"\n{'='*60}")
    print("Weekly brief complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
