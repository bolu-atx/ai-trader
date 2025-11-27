"""SQLite database schema and operations for ai-trader."""

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "trader.db"


def get_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Get a database connection with row factory."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Initialize the database schema."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Watchlist - tickers you're tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            ticker TEXT PRIMARY KEY,
            name TEXT,
            sector TEXT,
            stance TEXT DEFAULT 'hold',  -- buy, hold, sell, watch
            added_date TEXT NOT NULL,
            notes TEXT,
            active INTEGER DEFAULT 1
        )
    """)

    # Daily prices
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, date)
        )
    """)

    # External signals (Danelfin scores, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            source TEXT NOT NULL,  -- 'danelfin', 'toggle', 'manual'
            score REAL,
            sentiment TEXT,  -- 'bullish', 'bearish', 'neutral'
            raw_data TEXT,  -- JSON for additional data
            UNIQUE(ticker, date, source)
        )
    """)

    # Earnings calendar and results
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS earnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            report_date TEXT NOT NULL,
            fiscal_quarter TEXT,  -- 'Q1 2025'
            estimate_eps REAL,
            actual_eps REAL,
            surprise_pct REAL,
            estimate_revenue REAL,
            actual_revenue REAL,
            guidance TEXT,  -- 'raised', 'lowered', 'maintained', 'none'
            notes TEXT,
            UNIQUE(ticker, report_date)
        )
    """)

    # Trade journal
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            action TEXT NOT NULL,  -- 'buy', 'sell', 'trim', 'add'
            date TEXT NOT NULL,
            price REAL NOT NULL,
            shares INTEGER NOT NULL,
            thesis TEXT,
            signals_snapshot TEXT,  -- JSON of signals at time of trade
            outcome_notes TEXT,
            outcome_return REAL,
            closed_date TEXT
        )
    """)

    # News and research
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,  -- NULL for market-wide news
            date TEXT NOT NULL,
            headline TEXT NOT NULL,
            summary TEXT,
            source TEXT,
            url TEXT,
            sentiment TEXT,  -- 'positive', 'negative', 'neutral'
            relevance_score REAL,
            UNIQUE(url)
        )
    """)

    # Weekly recommendations (AI-generated)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            recommendation TEXT NOT NULL,  -- 'strong_buy', 'buy', 'hold', 'sell', 'strong_sell'
            confidence REAL,  -- 0-1
            rationale TEXT,
            factors TEXT,  -- JSON of contributing factors
            UNIQUE(ticker, date)
        )
    """)

    # Create indexes for common queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_ticker ON prices(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_ticker ON news(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_date ON news(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_earnings_date ON earnings(report_date)")

    conn.commit()
    conn.close()


# =============================================================================
# Watchlist Operations
# =============================================================================


def add_to_watchlist(
    ticker: str,
    name: str = "",
    sector: str = "",
    stance: str = "watch",
    notes: str = "",
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Add a ticker to the watchlist."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO watchlist (ticker, name, sector, stance, added_date, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(ticker) DO UPDATE SET
            name = excluded.name,
            sector = excluded.sector,
            stance = excluded.stance,
            notes = excluded.notes,
            active = 1
        """,
        (ticker.upper(), name, sector, stance, date.today().isoformat(), notes),
    )
    conn.commit()
    conn.close()


def remove_from_watchlist(ticker: str, db_path: Path = DEFAULT_DB_PATH) -> None:
    """Soft-remove a ticker from watchlist (set inactive)."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE watchlist SET active = 0 WHERE ticker = ?",
        (ticker.upper(),),
    )
    conn.commit()
    conn.close()


def get_watchlist(active_only: bool = True, db_path: Path = DEFAULT_DB_PATH) -> list[dict]:
    """Get all tickers in the watchlist."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    query = "SELECT * FROM watchlist"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY ticker"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_stance(ticker: str, stance: str, db_path: Path = DEFAULT_DB_PATH) -> None:
    """Update the stance for a ticker."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE watchlist SET stance = ? WHERE ticker = ?",
        (stance, ticker.upper()),
    )
    conn.commit()
    conn.close()


# =============================================================================
# Price Operations
# =============================================================================


def insert_prices(prices_data: list[dict], db_path: Path = DEFAULT_DB_PATH) -> int:
    """Insert price records. Returns count of inserted rows."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    inserted = 0
    for p in prices_data:
        try:
            cursor.execute(
                """
                INSERT INTO prices (ticker, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker, date) DO UPDATE SET
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    close = excluded.close,
                    volume = excluded.volume
                """,
                (p["ticker"], p["date"], p["open"], p["high"], p["low"], p["close"], p["volume"]),
            )
            inserted += 1
        except Exception:
            continue
    conn.commit()
    conn.close()
    return inserted


def get_latest_price(ticker: str, db_path: Path = DEFAULT_DB_PATH) -> Optional[dict]:
    """Get the most recent price for a ticker."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 1
        """,
        (ticker.upper(),),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_price_history(
    ticker: str, days: int = 30, db_path: Path = DEFAULT_DB_PATH
) -> list[dict]:
    """Get price history for a ticker."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM prices
        WHERE ticker = ?
        ORDER BY date DESC
        LIMIT ?
        """,
        (ticker.upper(), days),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# =============================================================================
# Signal Operations
# =============================================================================


def insert_signal(
    ticker: str,
    source: str,
    score: Optional[float] = None,
    sentiment: Optional[str] = None,
    raw_data: Optional[str] = None,
    signal_date: Optional[str] = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Insert a signal record."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO signals (ticker, date, source, score, sentiment, raw_data)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(ticker, date, source) DO UPDATE SET
            score = excluded.score,
            sentiment = excluded.sentiment,
            raw_data = excluded.raw_data
        """,
        (
            ticker.upper(),
            signal_date or date.today().isoformat(),
            source,
            score,
            sentiment,
            raw_data,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_signals(ticker: str, db_path: Path = DEFAULT_DB_PATH) -> list[dict]:
    """Get the most recent signal from each source for a ticker."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT s1.* FROM signals s1
        INNER JOIN (
            SELECT source, MAX(date) as max_date
            FROM signals
            WHERE ticker = ?
            GROUP BY source
        ) s2 ON s1.source = s2.source AND s1.date = s2.max_date
        WHERE s1.ticker = ?
        """,
        (ticker.upper(), ticker.upper()),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# =============================================================================
# Earnings Operations
# =============================================================================


def insert_earnings(
    ticker: str,
    report_date: str,
    fiscal_quarter: Optional[str] = None,
    estimate_eps: Optional[float] = None,
    actual_eps: Optional[float] = None,
    estimate_revenue: Optional[float] = None,
    actual_revenue: Optional[float] = None,
    guidance: Optional[str] = None,
    notes: Optional[str] = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Insert or update an earnings record."""
    surprise_pct = None
    if actual_eps is not None and estimate_eps is not None and estimate_eps != 0:
        surprise_pct = ((actual_eps - estimate_eps) / abs(estimate_eps)) * 100

    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO earnings (ticker, report_date, fiscal_quarter, estimate_eps, actual_eps,
                              surprise_pct, estimate_revenue, actual_revenue, guidance, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ticker, report_date) DO UPDATE SET
            fiscal_quarter = excluded.fiscal_quarter,
            estimate_eps = excluded.estimate_eps,
            actual_eps = excluded.actual_eps,
            surprise_pct = excluded.surprise_pct,
            estimate_revenue = excluded.estimate_revenue,
            actual_revenue = excluded.actual_revenue,
            guidance = excluded.guidance,
            notes = excluded.notes
        """,
        (
            ticker.upper(),
            report_date,
            fiscal_quarter,
            estimate_eps,
            actual_eps,
            surprise_pct,
            estimate_revenue,
            actual_revenue,
            guidance,
            notes,
        ),
    )
    conn.commit()
    conn.close()


def get_upcoming_earnings(days: int = 14, db_path: Path = DEFAULT_DB_PATH) -> list[dict]:
    """Get upcoming earnings for watchlist tickers."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute(
        """
        SELECT e.*, w.name, w.stance
        FROM earnings e
        JOIN watchlist w ON e.ticker = w.ticker
        WHERE e.report_date >= ?
          AND e.report_date <= date(?, '+' || ? || ' days')
          AND w.active = 1
          AND e.actual_eps IS NULL
        ORDER BY e.report_date
        """,
        (today, today, days),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# =============================================================================
# Trade Operations
# =============================================================================


def log_trade(
    ticker: str,
    action: str,
    price: float,
    shares: int,
    thesis: Optional[str] = None,
    signals_snapshot: Optional[str] = None,
    trade_date: Optional[str] = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    """Log a trade. Returns the trade ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO trades (ticker, action, date, price, shares, thesis, signals_snapshot)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ticker.upper(),
            action,
            trade_date or date.today().isoformat(),
            price,
            shares,
            thesis,
            signals_snapshot,
        ),
    )
    trade_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return trade_id


def close_trade(
    trade_id: int,
    outcome_notes: str,
    outcome_return: float,
    closed_date: Optional[str] = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Close a trade with outcome."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE trades SET outcome_notes = ?, outcome_return = ?, closed_date = ?
        WHERE id = ?
        """,
        (outcome_notes, outcome_return, closed_date or date.today().isoformat(), trade_id),
    )
    conn.commit()
    conn.close()


def get_open_trades(db_path: Path = DEFAULT_DB_PATH) -> list[dict]:
    """Get all open (unclosed) trades."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM trades WHERE closed_date IS NULL ORDER BY date DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_trade_history(
    ticker: Optional[str] = None, limit: int = 50, db_path: Path = DEFAULT_DB_PATH
) -> list[dict]:
    """Get trade history, optionally filtered by ticker."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    if ticker:
        cursor.execute(
            "SELECT * FROM trades WHERE ticker = ? ORDER BY date DESC LIMIT ?",
            (ticker.upper(), limit),
        )
    else:
        cursor.execute("SELECT * FROM trades ORDER BY date DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# =============================================================================
# News Operations
# =============================================================================


def insert_news(
    headline: str,
    source: str,
    url: str,
    ticker: Optional[str] = None,
    summary: Optional[str] = None,
    sentiment: Optional[str] = None,
    relevance_score: Optional[float] = None,
    news_date: Optional[str] = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Insert a news record."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO news (ticker, date, headline, summary, source, url, sentiment, relevance_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker.upper() if ticker else None,
                news_date or date.today().isoformat(),
                headline,
                summary,
                source,
                url,
                sentiment,
                relevance_score,
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Duplicate URL, skip
    conn.close()


def get_recent_news(
    ticker: Optional[str] = None, days: int = 7, db_path: Path = DEFAULT_DB_PATH
) -> list[dict]:
    """Get recent news, optionally filtered by ticker."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    today = date.today().isoformat()
    if ticker:
        cursor.execute(
            """
            SELECT * FROM news
            WHERE ticker = ? AND date >= date(?, '-' || ? || ' days')
            ORDER BY date DESC
            """,
            (ticker.upper(), today, days),
        )
    else:
        cursor.execute(
            """
            SELECT * FROM news
            WHERE date >= date(?, '-' || ? || ' days')
            ORDER BY date DESC
            """,
            (today, days),
        )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# =============================================================================
# Recommendation Operations
# =============================================================================


def insert_recommendation(
    ticker: str,
    recommendation: str,
    confidence: float,
    rationale: str,
    factors: Optional[str] = None,
    rec_date: Optional[str] = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Insert a recommendation record."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO recommendations (ticker, date, recommendation, confidence, rationale, factors)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(ticker, date) DO UPDATE SET
            recommendation = excluded.recommendation,
            confidence = excluded.confidence,
            rationale = excluded.rationale,
            factors = excluded.factors
        """,
        (
            ticker.upper(),
            rec_date or date.today().isoformat(),
            recommendation,
            confidence,
            rationale,
            factors,
        ),
    )
    conn.commit()
    conn.close()


def get_latest_recommendations(db_path: Path = DEFAULT_DB_PATH) -> list[dict]:
    """Get the most recent recommendation for each watchlist ticker."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT r.*, w.name, w.stance
        FROM recommendations r
        JOIN watchlist w ON r.ticker = w.ticker
        INNER JOIN (
            SELECT ticker, MAX(date) as max_date
            FROM recommendations
            GROUP BY ticker
        ) latest ON r.ticker = latest.ticker AND r.date = latest.max_date
        WHERE w.active = 1
        ORDER BY r.confidence DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


if __name__ == "__main__":
    # Initialize database when run directly
    init_db()
    print(f"Database initialized at {DEFAULT_DB_PATH}")
