"""
load_fundamentals.py
--------------------
Pull quarterly income statement, balance sheet, cash flow, key metrics,
and ratios from FMP. Inserts into quarterly_fundamentals and
valuation_metrics tables.

Run from the backend/ directory:
    python pipelines/load_fundamentals.py
"""

import sys
import os
import argparse
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_connection
from data_sources.fmp_client import (
    get_income_statement,
    get_balance_sheet,
    get_cash_flow,
    get_key_metrics,
    get_ratios,
)

TICKERS = [
    "NVDA", "AMD", "AVGO", "MU", "TSM", "ASML", "AMAT",
    "LRCX", "KLAC", "SNPS", "CDNS", "ANET", "VRT", "MRVL",
    "MSFT", "GOOGL", "AMZN", "META", "ORCL",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_date(val):
    """Convert FMP date string 'YYYY-MM-DD' → Python date, or None."""
    if not val:
        return None
    try:
        return date.fromisoformat(str(val)[:10])
    except ValueError:
        return None


def _index_by_date(records: list, date_key: str = "date") -> dict:
    """Index a list of FMP records by their date string for easy merging."""
    return {r.get(date_key): r for r in records if r.get(date_key)}


# ---------------------------------------------------------------------------
# quarterly_fundamentals insert
# ---------------------------------------------------------------------------

def insert_quarterly_fundamentals(conn, ticker: str, limit: int = 20):
    """
    Merge income statement + balance sheet + cash flow for a ticker
    and upsert into quarterly_fundamentals.
    """
    income    = get_income_statement(ticker, period="quarter", limit=limit)
    balance   = _index_by_date(get_balance_sheet(ticker,  period="quarter", limit=limit))
    cashflow  = _index_by_date(get_cash_flow(ticker,      period="quarter", limit=limit))

    if not income:
        print(f"  [fundamentals] {ticker}: no income statement data")
        return 0

    sql = """
        INSERT INTO quarterly_fundamentals
            (ticker, fiscal_date, period, revenue, gross_profit, operating_income,
             net_income, eps, free_cash_flow, capital_expenditure, cash, total_debt)
        VALUES
            (%(ticker)s, %(fiscal_date)s, %(period)s, %(revenue)s, %(gross_profit)s,
             %(operating_income)s, %(net_income)s, %(eps)s, %(free_cash_flow)s,
             %(capital_expenditure)s, %(cash)s, %(total_debt)s)
        ON CONFLICT (ticker, fiscal_date, period) DO UPDATE SET
            revenue             = EXCLUDED.revenue,
            gross_profit        = EXCLUDED.gross_profit,
            operating_income    = EXCLUDED.operating_income,
            net_income          = EXCLUDED.net_income,
            eps                 = EXCLUDED.eps,
            free_cash_flow      = EXCLUDED.free_cash_flow,
            capital_expenditure = EXCLUDED.capital_expenditure,
            cash                = EXCLUDED.cash,
            total_debt          = EXCLUDED.total_debt
    """

    rows = []
    for rec in income:
        d    = rec.get("date", "")
        bal  = balance.get(d, {})
        cf   = cashflow.get(d, {})

        rows.append({
            "ticker":             ticker,
            "fiscal_date":        _safe_date(d),
            "period":             rec.get("period", ""),
            "revenue":            rec.get("revenue"),
            "gross_profit":       rec.get("grossProfit"),
            "operating_income":   rec.get("operatingIncome"),
            "net_income":         rec.get("netIncome"),
            "eps":                rec.get("eps"),
            "free_cash_flow":     cf.get("freeCashFlow"),
            "capital_expenditure":cf.get("capitalExpenditure"),
            "cash":               bal.get("cashAndCashEquivalents"),
            "total_debt":         bal.get("totalDebt"),
        })

    # Filter out rows without a valid fiscal_date
    rows = [r for r in rows if r["fiscal_date"]]

    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()
    return len(rows)


# ---------------------------------------------------------------------------
# valuation_metrics insert
# ---------------------------------------------------------------------------

def insert_valuation_metrics(conn, ticker: str, limit: int = 20):
    """
    Merge key_metrics + ratios for a ticker and upsert into valuation_metrics.
    Uses the FMP date as the snapshot date.
    """
    metrics = get_key_metrics(ticker, period="quarter", limit=limit)
    ratios  = _index_by_date(get_ratios(ticker, period="quarter", limit=limit))

    if not metrics:
        print(f"  [valuation] {ticker}: no key metrics data")
        return 0

    sql = """
        INSERT INTO valuation_metrics
            (ticker, date, pe_ratio, price_to_sales, ev_to_sales, ev_to_ebitda,
             price_to_free_cash_flow, roe, roic, debt_to_equity)
        VALUES
            (%(ticker)s, %(date)s, %(pe_ratio)s, %(price_to_sales)s, %(ev_to_sales)s,
             %(ev_to_ebitda)s, %(price_to_free_cash_flow)s, %(roe)s, %(roic)s,
             %(debt_to_equity)s)
        ON CONFLICT (ticker, date) DO UPDATE SET
            pe_ratio                = EXCLUDED.pe_ratio,
            price_to_sales          = EXCLUDED.price_to_sales,
            ev_to_sales             = EXCLUDED.ev_to_sales,
            ev_to_ebitda            = EXCLUDED.ev_to_ebitda,
            price_to_free_cash_flow = EXCLUDED.price_to_free_cash_flow,
            roe                     = EXCLUDED.roe,
            roic                    = EXCLUDED.roic,
            debt_to_equity          = EXCLUDED.debt_to_equity
    """

    rows = []
    for rec in metrics:
        d   = rec.get("date", "")
        rat = ratios.get(d, {})

        rows.append({
            "ticker":                 ticker,
            "date":                   _safe_date(d),
            # P/E from ratios (more reliable), fallback to key metrics
            "pe_ratio":               rat.get("priceEarningsRatio") or rec.get("peRatio"),
            "price_to_sales":         rat.get("priceToSalesRatio"),
            "ev_to_sales":            rec.get("evToSales"),
            "ev_to_ebitda":           rec.get("enterpriseValueOverEBITDA"),
            "price_to_free_cash_flow":rec.get("pfcfRatio"),
            "roe":                    rat.get("returnOnEquity"),
            "roic":                   rec.get("roic"),
            "debt_to_equity":         rat.get("debtEquityRatio"),
        })

    rows = [r for r in rows if r["date"]]

    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()
    return len(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(tickers: list, limit: int = 20):
    conn = get_connection()
    try:
        for ticker in tickers:
            n_fund = insert_quarterly_fundamentals(conn, ticker, limit=limit)
            n_val  = insert_valuation_metrics(conn, ticker, limit=limit)
            print(f"  → {ticker}: {n_fund} fundamental rows, {n_val} valuation rows")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load fundamentals and valuation metrics")
    parser.add_argument("--limit",   type=int, default=20,
                        help="Number of quarters to fetch per ticker (default: 20)")
    parser.add_argument("--tickers", nargs="*", default=TICKERS)
    args = parser.parse_args()

    print(f"Loading fundamentals for {len(args.tickers)} tickers ...")
    run(args.tickers, limit=args.limit)
    print("Done.")
