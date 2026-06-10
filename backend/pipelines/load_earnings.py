"""
load_earnings.py
----------------
Pull historical earnings surprise data from FMP and insert into
earnings_events (used for PEAD / earnings drift analysis).

Run from the backend/ directory:
    python pipelines/load_earnings.py
"""

import sys
import os
import argparse
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_connection
from data_sources.fmp_client import get_earnings

TICKERS = [
    "NVDA", "AMD", "AVGO", "MU", "TSM", "ASML", "AMAT",
    "LRCX", "KLAC", "SNPS", "CDNS", "ANET", "VRT", "MRVL",
    "MSFT", "GOOGL", "AMZN", "META", "ORCL",
]


def _safe_date(val):
    if not val:
        return None
    try:
        return date.fromisoformat(str(val)[:10])
    except ValueError:
        return None


def insert_earnings(conn, ticker: str, limit: int = 20):
    """Fetch and upsert earnings surprises for a single ticker."""
    records = get_earnings(ticker, limit=limit)

    if not records:
        print(f"  [earnings] {ticker}: no data")
        return 0

    sql = """
        INSERT INTO earnings_events
            (ticker, earnings_date, eps_actual, eps_estimated,
             revenue_actual, revenue_estimated, surprise_percentage)
        VALUES
            (%(ticker)s, %(earnings_date)s, %(eps_actual)s, %(eps_estimated)s,
             %(revenue_actual)s, %(revenue_estimated)s, %(surprise_percentage)s)
        ON CONFLICT (ticker, earnings_date) DO UPDATE SET
            eps_actual          = EXCLUDED.eps_actual,
            eps_estimated       = EXCLUDED.eps_estimated,
            revenue_actual      = EXCLUDED.revenue_actual,
            revenue_estimated   = EXCLUDED.revenue_estimated,
            surprise_percentage = EXCLUDED.surprise_percentage
    """

    rows = []
    for rec in records:
        earnings_date = _safe_date(rec.get("date"))
        if not earnings_date:
            continue

        eps_actual    = rec.get("actualEarningResult")
        eps_estimated = rec.get("estimatedEarning")

        # Calculate surprise % if not provided directly
        surprise = rec.get("surprisePercent")
        if surprise is None and eps_estimated and eps_estimated != 0:
            try:
                surprise = ((float(eps_actual) - float(eps_estimated))
                            / abs(float(eps_estimated))) * 100
            except (TypeError, ValueError):
                surprise = None

        rows.append({
            "ticker":             ticker,
            "earnings_date":      earnings_date,
            "eps_actual":         eps_actual,
            "eps_estimated":      eps_estimated,
            # FMP earnings-surprises endpoint does not include revenue
            # These will be NULL unless you cross-reference income statement
            "revenue_actual":     rec.get("revenueActual"),
            "revenue_estimated":  rec.get("revenueEstimated"),
            "surprise_percentage":surprise,
        })

    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()
    return len(rows)


def run(tickers: list, limit: int = 20):
    conn = get_connection()
    try:
        for ticker in tickers:
            count = insert_earnings(conn, ticker, limit=limit)
            print(f"  → {ticker}: {count} earnings rows inserted/updated")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load earnings surprise data")
    parser.add_argument("--limit",   type=int, default=20)
    parser.add_argument("--tickers", nargs="*", default=TICKERS)
    args = parser.parse_args()

    print(f"Loading earnings for {len(args.tickers)} tickers ...")
    run(args.tickers, limit=args.limit)
    print("Done.")
