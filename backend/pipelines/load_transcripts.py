"""
load_transcripts.py
-------------------
Pipeline for loading earnings call transcripts into earnings_transcripts.

STATUS: Placeholder — table and schema are ready, source not yet connected.

─── TRANSCRIPT SOURCE OPTIONS (connect one when ready) ────────────────────────

1. SEEKING ALPHA PREMIUM ($20/mo) — Recommended
   - Best archive depth and coverage for the AI chip ticker universe
   - Transcripts available via their website; no official public API
   - Practical approach: manual download or community-maintained scrapers
   - Store raw HTML or plain text; strip to plain text before inserting

2. FMP ULTIMATE ($149/mo)
   - Endpoint: GET /earning_call_transcript?symbol=NVDA&quarter=3&year=2024
   - Returns structured JSON with transcript text
   - Uncomment and use fmp_client.get_transcript() once you upgrade

3. EDGAR 8-K FILINGS (free)
   - Some companies file earnings scripts as 8-K exhibits
   - Coverage is inconsistent — not all companies file transcripts
   - Use as a free supplement, not a primary source

4. MANUAL IMPORT
   - Drop a .txt file into a watched directory
   - Use the insert_transcript() function below directly

─── HOW TO USE WHEN CONNECTED ─────────────────────────────────────────────────

Once you have a transcript source:
    1. Implement fetch_transcript() for your source
    2. Call insert_transcript(conn, row) to store it
    3. Run: python pipelines/load_transcripts.py

The raw_text field is intentionally stored in full so you can reprocess
with new LLM prompts or models at any future point without re-fetching.

Run from the backend/ directory:
    python pipelines/load_transcripts.py
"""

import sys
import os
import argparse
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_connection


# ---------------------------------------------------------------------------
# Core insert — call this from whatever source implementation you build
# ---------------------------------------------------------------------------

def insert_transcript(conn, row: dict) -> int:
    """
    Insert or skip a transcript row.

    row must contain:
        ticker       str        e.g. "NVDA"
        fiscal_date  date       fiscal quarter end date
        period       str        "Q1", "Q2", "Q3", "Q4", "FY"
        call_date    date|None  actual call date if known
        raw_text     str|None   full transcript text
        source       str        "seeking_alpha", "fmp", "manual", etc.

    ON CONFLICT (ticker, fiscal_date, period) DO NOTHING:
        If a transcript already exists for this period, it is not overwritten.
        To replace a transcript, DELETE the existing row first.
    """
    if not row.get("raw_text"):
        print(f"  [transcripts] {row.get('ticker')}: raw_text is empty, skipping")
        return 0

    word_count = len(row["raw_text"].split()) if row.get("raw_text") else None

    sql = """
        INSERT INTO earnings_transcripts
            (ticker, fiscal_date, period, call_date, raw_text, word_count, source)
        VALUES
            (%(ticker)s, %(fiscal_date)s, %(period)s, %(call_date)s,
             %(raw_text)s, %(word_count)s, %(source)s)
        ON CONFLICT (ticker, fiscal_date, period)
        DO NOTHING
    """

    with conn.cursor() as cur:
        cur.execute(sql, {**row, "word_count": word_count})
    conn.commit()
    return 1


# ---------------------------------------------------------------------------
# FMP transcript fetcher (uncomment when on FMP Ultimate)
# ---------------------------------------------------------------------------

# def fetch_transcript_fmp(ticker: str, quarter: int, year: int) -> str | None:
#     """
#     Fetch a single transcript from FMP Ultimate.
#
#     FMP endpoint: /earning_call_transcript?symbol=NVDA&quarter=3&year=2024
#     Returns the transcript text string, or None if unavailable.
#
#     Requires FMP Ultimate plan ($149/mo).
#     """
#     from data_sources.fmp_client import _get
#     records = _get("earning_call_transcript", {
#         "symbol":  ticker,
#         "quarter": quarter,
#         "year":    year,
#     })
#     if not records:
#         return None
#     return records[0].get("content")


# ---------------------------------------------------------------------------
# Manual import helper
# ---------------------------------------------------------------------------

def import_from_file(filepath: str, ticker: str, fiscal_date: str,
                     period: str, source: str = "manual") -> int:
    """
    Import a transcript from a local .txt file.

    Usage:
        python -c "
        from pipelines.load_transcripts import import_from_file
        import_from_file('~/Downloads/nvda_q1_2025.txt', 'NVDA', '2025-04-30', 'Q1')
        "
    """
    from datetime import date as dt
    filepath = os.path.expanduser(filepath)
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return 0

    with open(filepath, "r", encoding="utf-8") as f:
        raw_text = f.read()

    conn = get_connection()
    try:
        count = insert_transcript(conn, {
            "ticker":      ticker,
            "fiscal_date": dt.fromisoformat(fiscal_date),
            "period":      period,
            "call_date":   None,
            "raw_text":    raw_text,
            "source":      source,
        })
        print(f"  → {ticker} {period} {fiscal_date}: {'inserted' if count else 'already exists'}")
        return count
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Main (placeholder — implement fetch logic above before activating)
# ---------------------------------------------------------------------------

def run(tickers: list, limit: int = 8):
    """
    Main pipeline run. Currently a no-op placeholder.

    To activate: implement a fetch function above and call insert_transcript()
    for each result, then remove the early return below.
    """
    print("load_transcripts.py: No transcript source connected yet.")
    print("See the source options at the top of this file.")
    print("Tables are ready — connect a source and re-run.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load earnings transcripts")
    parser.add_argument("--tickers", nargs="*", default=[])
    args = parser.parse_args()
    run(args.tickers)
