"""
load_news.py
------------
Pull company news from Finnhub for each ticker and insert into
news_articles. Uses the /company-news endpoint (requires date range).

NOTE: The existing Flask route (backend/routes/news.py) and its service
      (backend/services/finnhub_service.py) are completely separate and
      are NOT affected by running this pipeline.

Run from the backend/ directory:
    python pipelines/load_news.py

Flags:
    --days   How many days back to fetch (default: 30)
    --tickers  Override ticker list
"""

import sys
import os
import argparse
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_connection
from data_sources.finnhub_client import fetch_company_news

TICKERS = [
    "NVDA", "AMD", "AVGO", "MU", "TSM", "ASML", "AMAT",
    "LRCX", "KLAC", "SNPS", "CDNS", "ANET", "VRT", "MRVL",
    "MSFT", "GOOGL", "AMZN", "META", "ORCL",
]


def insert_news(conn, ticker: str, articles: list):
    """
    Upsert news articles for a ticker into news_articles.
    Deduplicates on url — same article won't be inserted twice even
    if it appears under multiple tickers.
    """
    if not articles:
        return 0

    sql = """
        INSERT INTO news_articles
            (ticker, headline, summary, source, url, image,
             published_at, related_tickers)
        VALUES
            (%(ticker)s, %(headline)s, %(summary)s, %(source)s, %(url)s,
             %(image)s, to_timestamp(%(datetime)s), %(related)s)
        ON CONFLICT (url) DO NOTHING
    """

    rows = []
    for a in articles:
        url = a.get("url", "").strip()
        if not url:
            continue  # skip articles without a URL

        rows.append({
            "ticker":   ticker,
            "headline": a.get("headline"),
            "summary":  a.get("summary"),
            "source":   a.get("source"),
            "url":      url,
            "image":    a.get("image"),
            # Finnhub returns Unix timestamp as integer
            "datetime": a.get("datetime"),
            # 'related' is a space-separated string of tickers in Finnhub
            "related":  a.get("related"),
        })

    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()
    return len(rows)


def run(tickers: list, days: int = 30):
    to_date   = date.today().isoformat()
    from_date = (date.today() - timedelta(days=days)).isoformat()

    print(f"Fetching news from {from_date} to {to_date} ...")

    conn = get_connection()
    try:
        for ticker in tickers:
            articles = fetch_company_news(ticker, from_date, to_date)
            count    = insert_news(conn, ticker, articles)
            print(f"  → {ticker}: {count} articles inserted (of {len(articles)} fetched)")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load company news from Finnhub")
    parser.add_argument("--days",    type=int, default=30,
                        help="Number of days back to fetch (default: 30)")
    parser.add_argument("--tickers", nargs="*", default=TICKERS)
    args = parser.parse_args()

    run(args.tickers, days=args.days)
    print("Done.")
