"""
run_weekly_snapshots.py
-----------------------
Single entry point for all point-in-time snapshot collections.
Run this once per week (e.g. every Monday morning) to build the
revision time series that powers estimate momentum analysis.

What it runs:
    1. load_estimates.py     — analyst EPS/revenue consensus snapshots
    2. load_price_targets.py — analyst price target consensus snapshots

What it does NOT run (separate cadence):
    - load_prices.py         — run daily
    - load_fundamentals.py   — run after each earnings season (quarterly)
    - load_earnings.py       — run after each earnings season (quarterly)
    - load_news.py           — run daily or on-demand
    - load_transcripts.py    — run after each earnings season (quarterly)

Run from the backend/ directory:
    python pipelines/run_weekly_snapshots.py

Optional flags:
    --date    Override snapshot date YYYY-MM-DD (default: today)
              Use only when replaying a specific date
    --tickers Override the default ticker list
    --dry-run Print what would run without executing

To schedule weekly (add to crontab later):
    # Every Monday at 8:00 AM
    0 8 * * 1 cd /path/to/project/backend && python pipelines/run_weekly_snapshots.py
"""

import sys
import os
import argparse
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import run functions directly — avoids subprocess overhead and shares DB connection context
from pipelines.load_estimates      import run as run_estimates, _safe_date, TICKERS as DEFAULT_TICKERS
from pipelines.load_price_targets  import run as run_price_targets


def run_weekly(tickers: list, snapshot_date: date, dry_run: bool = False):
    print("=" * 60)
    print(f"Weekly Snapshot Run")
    print(f"Snapshot date : {snapshot_date}")
    print(f"Tickers       : {len(tickers)}")
    print(f"Dry run       : {dry_run}")
    print("=" * 60)

    if dry_run:
        print("\n[DRY RUN] Would execute:")
        print("  1. load_estimates    — analyst EPS/revenue snapshots")
        print("  2. load_price_targets — analyst price target snapshots")
        print("\nNo data written.")
        return

    # --- Step 1: Analyst estimate snapshots ---
    print("\n[1/2] Running load_estimates ...")
    try:
        run_estimates(tickers, snapshot_date=snapshot_date)
    except Exception as e:
        print(f"  ERROR in load_estimates: {e}")
        print("  Continuing to next step ...")

    # --- Step 2: Price target snapshots ---
    print("\n[2/2] Running load_price_targets ...")
    try:
        run_price_targets(tickers, snapshot_date=snapshot_date)
    except Exception as e:
        print(f"  ERROR in load_price_targets: {e}")
        print("  Continuing ...")

    print("\n" + "=" * 60)
    print(f"Weekly snapshot complete for {snapshot_date}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run all weekly point-in-time snapshot pipelines"
    )
    parser.add_argument("--date",    default=None,
                        help="Override snapshot date YYYY-MM-DD (default: today)")
    parser.add_argument("--tickers", nargs="*", default=DEFAULT_TICKERS,
                        help="Override ticker list")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print plan without writing any data")
    args = parser.parse_args()

    snapshot_date = _safe_date(args.date) if args.date else date.today()
    if not snapshot_date:
        print(f"Invalid --date value: {args.date}")
        sys.exit(1)

    run_weekly(
        tickers=args.tickers,
        snapshot_date=snapshot_date,
        dry_run=args.dry_run,
    )
