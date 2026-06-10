"""
load_prices.py
--------------
Pull daily price history via yfinance and insert into daily_prices.

Run from the backend/ directory:
    python pipelines/load_prices.py

Flags:
    --period  yfinance period string (default: "5y"). Use "max" for full backfill.
    --tickers space-separated override list (defaults to TICKERS below)
"""

import sys
import os
import argparse

# Allow imports from the backend/ directory regardless of where this is run from
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from database import get_connection
from data_sources.yfinance_client import fetch_price_history

# ---------------------------------------------------------------------------
# Ticker universe
# ---------------------------------------------------------------------------

TICKERS = [
    "NVDA", "AMD", "AVGO", "MU", "TSM", "ASML", "AMAT",
    "LRCX", "KLAC", "SNPS", "CDNS", "ANET", "VRT", "MRVL",
    "MSFT", "GOOGL", "AMZN", "META", "ORCL",
]


# ---------------------------------------------------------------------------
# DB insert
# ---------------------------------------------------------------------------

def insert_prices(conn, df):
    """
    Upsert rows from df into daily_prices.
    ON CONFLICT (ticker, date) → update OHLCV columns.
    """
    if df.empty:
        return 0

    sql = """
        INSERT INTO daily_prices
            (ticker, date, open, high, low, close, adjusted_close, volume)
        VALUES
            (%(ticker)s, %(date)s, %(open)s, %(high)s, %(low)s,
             %(close)s, %(adjusted_close)s, %(volume)s)
        ON CONFLICT (ticker, date) DO UPDATE SET
            open           = EXCLUDED.open,
            high           = EXCLUDED.high,
            low            = EXCLUDED.low,
            close          = EXCLUDED.close,
            adjusted_close = EXCLUDED.adjusted_close,
            volume         = EXCLUDED.volume
    """

    rows = df.to_dict(orient="records")
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()
    return len(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(tickers: list, period: str = "5y"):
    conn = get_connection()
    try:
        for ticker in tickers:
            df = fetch_price_history(ticker, period=period)
            count = insert_prices(conn, df)
            print(f"  → {ticker}: {count} rows inserted/updated")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load daily prices into PostgreSQL")
    parser.add_argument("--period",  default="5y",
                        help="yfinance period string (default: 5y)")
    parser.add_argument("--tickers", nargs="*", default=TICKERS,
                        help="Override ticker list")
    args = parser.parse_args()

    print(f"Loading prices for {len(args.tickers)} tickers (period={args.period}) ...")
    run(args.tickers, period=args.period)
    print("Done.")
