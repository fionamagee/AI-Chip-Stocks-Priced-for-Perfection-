"""
load_estimates.py
-----------------
Pull consensus analyst EPS and revenue estimates from FMP and insert
a point-in-time snapshot into analyst_estimates.

KEY BEHAVIOUR:
    Every run stores today's snapshot_date as a new row.
    Prior snapshots are NEVER overwritten or deleted.
    Running this weekly builds an estimate revision time series —
    the most analytically important data that cannot be reconstructed
    retroactively. Start running this immediately and keep it running.

Unique constraint: (ticker, fiscal_date, period, snapshot_date)
→ Running twice on the same day is safe (second run does nothing).
→ Running on a different day always adds a new snapshot.

Run from the backend/ directory:
    python pipelines/load_estimates.py

Optional flags:
    --limit   Number of fiscal periods to fetch per ticker (default: 20)
    --tickers Override the default ticker list
    --date    Override snapshot date for backfilling, e.g. 2025-01-15
              (only use this when replaying historical data you have available)
"""

import sys
import os
import argparse
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_connection
from data_sources.fmp_client import get_analyst_estimates

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


def insert_estimates(conn, ticker: str, snapshot_date: date, limit: int = 20) -> int:
    """
    Fetch current consensus estimates from FMP and insert a snapshot row
    for each fiscal period.

    ON CONFLICT (ticker, fiscal_date, period, snapshot_date) DO NOTHING:
        - Running on the same day twice is safe — no duplicate inserted.
        - Running on a new day always adds a fresh snapshot.
        - Prior snapshots on earlier dates are never touched.
    """
    records = get_analyst_estimates(ticker, period="quarter", limit=limit)

    if not records:
        print(f"  [estimates] {ticker}: no data returned (FMP 402 = plan upgrade needed)")
        return 0

    sql = """
        INSERT INTO analyst_estimates
            (ticker, fiscal_date, period, snapshot_date,
             estimated_revenue_avg, estimated_eps_avg, number_analysts)
        VALUES
            (%(ticker)s, %(fiscal_date)s, %(period)s, %(snapshot_date)s,
             %(estimated_revenue_avg)s, %(estimated_eps_avg)s, %(number_analysts)s)
        ON CONFLICT (ticker, fiscal_date, period, snapshot_date)
        DO NOTHING
    """

    rows = []
    for rec in records:
        fiscal_date = _safe_date(rec.get("date"))
        if not fiscal_date:
            continue
        rows.append({
            "ticker":                 ticker,
            "fiscal_date":            fiscal_date,
            "period":                 rec.get("period", ""),
            "snapshot_date":          snapshot_date,
            "estimated_revenue_avg":  rec.get("estimatedRevenueAvg"),
            "estimated_eps_avg":      rec.get("estimatedEpsAvg"),
            "number_analysts":        rec.get("numberAnalystEstimatedRevenue"),
        })

    if not rows:
        return 0

    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()
    return len(rows)


def run(tickers: list, snapshot_date: date, limit: int = 20):
    print(f"Snapshot date: {snapshot_date}")
    conn = get_connection()
    total = 0
    try:
        for ticker in tickers:
            count = insert_estimates(conn, ticker, snapshot_date, limit=limit)
            print(f"  → {ticker}: {count} snapshot rows inserted")
            total += count
    finally:
        conn.close()
    print(f"Total rows inserted: {total}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Snapshot analyst estimates (run weekly to build revision time series)"
    )
    parser.add_argument("--limit",   type=int, default=20,
                        help="Fiscal periods per ticker (default: 20)")
    parser.add_argument("--tickers", nargs="*", default=TICKERS,
                        help="Override ticker list")
    parser.add_argument("--date",    default=None,
                        help="Override snapshot date YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    snapshot_date = _safe_date(args.date) if args.date else date.today()
    if not snapshot_date:
        print(f"Invalid --date value: {args.date}")
        sys.exit(1)

    print(f"Loading analyst estimate snapshots for {len(args.tickers)} tickers ...")
    run(args.tickers, snapshot_date=snapshot_date, limit=args.limit)
    print("Done.")
