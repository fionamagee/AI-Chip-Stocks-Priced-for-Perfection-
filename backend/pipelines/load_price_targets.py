"""
load_price_targets.py
---------------------
Snapshot analyst consensus price targets for each ticker and insert
into price_target_snapshots.

Like load_estimates.py, every run stores today as the snapshot_date.
Running weekly builds a price target revision time series.

FMP endpoints used:
    /price-target-consensus  → targetHigh, targetLow, targetConsensus, targetMedian
    (FMP Premium required)

Run from the backend/ directory:
    python pipelines/load_price_targets.py
"""

import sys
import os
import argparse
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_connection
from data_sources.fmp_client import get_price_target_consensus

TICKERS = [
    "NVDA", "AMD", "AVGO", "MU", "TSM", "ASML", "AMAT",
    "LRCX", "KLAC", "SNPS", "CDNS", "ANET", "VRT", "MRVL",
    "MSFT", "GOOGL", "AMZN", "META", "ORCL",
]


def insert_price_targets(conn, ticker: str, snapshot_date: date) -> int:
    """
    Fetch consensus price target from FMP and insert a snapshot row.

    ON CONFLICT (ticker, snapshot_date) DO NOTHING:
        Running twice on the same day is safe.
    """
    records = get_price_target_consensus(ticker)

    if not records:
        print(f"  [price_targets] {ticker}: no data (FMP Premium required)")
        return 0

    rec = records[0]  # consensus endpoint returns a single-item list

    # FMP field names vary slightly by endpoint version — handle both
    avg_target  = rec.get("targetConsensus") or rec.get("priceTargetAverage")
    high_target = rec.get("targetHigh")       or rec.get("priceTargetHigh")
    low_target  = rec.get("targetLow")        or rec.get("priceTargetLow")
    # analyst count not always returned by this endpoint
    num_analysts = rec.get("numberOfAnalysts") or rec.get("numberOfAnalystOpinions")

    sql = """
        INSERT INTO price_target_snapshots
            (ticker, snapshot_date, price_target_avg, price_target_high,
             price_target_low, number_analysts, source)
        VALUES
            (%(ticker)s, %(snapshot_date)s, %(price_target_avg)s, %(price_target_high)s,
             %(price_target_low)s, %(number_analysts)s, %(source)s)
        ON CONFLICT (ticker, snapshot_date)
        DO NOTHING
    """

    row = {
        "ticker":           ticker,
        "snapshot_date":    snapshot_date,
        "price_target_avg": avg_target,
        "price_target_high":high_target,
        "price_target_low": low_target,
        "number_analysts":  num_analysts,
        "source":           "fmp",
    }

    with conn.cursor() as cur:
        cur.execute(sql, row)
    conn.commit()
    return 1


def run(tickers: list, snapshot_date: date):
    print(f"Snapshot date: {snapshot_date}")
    conn = get_connection()
    total = 0
    try:
        for ticker in tickers:
            count = insert_price_targets(conn, ticker, snapshot_date)
            print(f"  → {ticker}: {count} price target row inserted")
            total += count
    finally:
        conn.close()
    print(f"Total rows inserted: {total}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Snapshot analyst price targets (run weekly)"
    )
    parser.add_argument("--tickers", nargs="*", default=TICKERS)
    parser.add_argument("--date",    default=None,
                        help="Override snapshot date YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    try:
        snapshot_date = date.fromisoformat(args.date) if args.date else date.today()
    except ValueError:
        print(f"Invalid --date value: {args.date}")
        sys.exit(1)

    print(f"Loading price target snapshots for {len(args.tickers)} tickers ...")
    run(args.tickers, snapshot_date=snapshot_date)
    print("Done.")
