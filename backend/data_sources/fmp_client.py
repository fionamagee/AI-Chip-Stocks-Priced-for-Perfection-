"""
fmp_client.py
-------------
Reusable helper functions for the Financial Modeling Prep (FMP) API.

Base URL: https://financialmodelingprep.com/stable/

Each function takes a ticker (and optional kwargs) and returns the
raw JSON list from FMP, or an empty list on error.

FMP API key is read from the FMP_API_KEY environment variable.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

BASE_URL = "https://financialmodelingprep.com/stable"
API_KEY  = os.getenv("FMP_API_KEY")


def _get(endpoint: str, params: dict = None) -> list:
    """
    Internal helper — GET BASE_URL/endpoint with apikey injected.

    Returns:
        Parsed JSON (list or dict). Returns [] on any error.
    """
    if not API_KEY:
        raise EnvironmentError("FMP_API_KEY is not set in your .env file.")

    url = f"{BASE_URL}/{endpoint}"
    all_params = {"apikey": API_KEY}
    if params:
        all_params.update(params)

    try:
        resp = requests.get(url, params=all_params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # FMP returns errors as {"Error Message": "..."} dicts
        if isinstance(data, dict) and "Error Message" in data:
            print(f"[FMP] API error for {endpoint}: {data['Error Message']}")
            return []
        return data if isinstance(data, list) else [data]
    except requests.exceptions.RequestException as e:
        print(f"[FMP] Request failed for {endpoint}: {e}")
        return []


# ------------------------------------------------------------------
# Income statement
# ------------------------------------------------------------------

def get_income_statement(ticker: str, period: str = "quarter", limit: int = 20) -> list:
    """
    Quarterly or annual income statement.

    Args:
        ticker: e.g. "NVDA"
        period: "quarter" or "annual"
        limit:  number of periods to return

    Returns:
        List of dicts, most recent first.
    """
    return _get("income-statement", {
        "symbol": ticker,
        "period": period,
        "limit":  limit,
    })


# ------------------------------------------------------------------
# Balance sheet
# ------------------------------------------------------------------

def get_balance_sheet(ticker: str, period: str = "quarter", limit: int = 20) -> list:
    """Quarterly or annual balance sheet statement."""
    return _get("balance-sheet-statement", {
        "symbol": ticker,
        "period": period,
        "limit":  limit,
    })


# ------------------------------------------------------------------
# Cash flow statement
# ------------------------------------------------------------------

def get_cash_flow(ticker: str, period: str = "quarter", limit: int = 20) -> list:
    """Quarterly or annual cash flow statement."""
    return _get("cash-flow-statement", {
        "symbol": ticker,
        "period": period,
        "limit":  limit,
    })


# ------------------------------------------------------------------
# Key metrics  (ROIC, EV/EBITDA, etc.)
# ------------------------------------------------------------------

def get_key_metrics(ticker: str, period: str = "quarter", limit: int = 20) -> list:
    """
    Key financial metrics including ROIC, EV/EBITDA, P/FCF, debt/equity.
    These are the valuation inputs for the valuation_metrics table.
    """
    return _get("key-metrics", {
        "symbol": ticker,
        "period": period,
        "limit":  limit,
    })


# ------------------------------------------------------------------
# Ratios  (P/E, P/S, ROE, etc.)
# ------------------------------------------------------------------

def get_ratios(ticker: str, period: str = "quarter", limit: int = 20) -> list:
    """
    Financial ratios: P/E, P/S, ROE, current ratio, etc.
    Combined with key_metrics to populate valuation_metrics.
    """
    return _get("ratios", {
        "symbol": ticker,
        "period": period,
        "limit":  limit,
    })


# ------------------------------------------------------------------
# Analyst estimates
# ------------------------------------------------------------------

def get_analyst_estimates(ticker: str, period: str = "quarter", limit: int = 20) -> list:
    """
    Consensus analyst EPS and revenue estimates.

    Returns forward-looking estimates per fiscal period.
    """
    return _get("analyst-estimates", {
        "symbol": ticker,
        "period": period,
        "limit":  limit,
    })


# ------------------------------------------------------------------
# Price target summary  (consensus avg / high / low)
# ------------------------------------------------------------------

def get_price_target_summary(ticker: str) -> list:
    """
    Analyst consensus price target summary for a ticker.

    FMP endpoint: /price-target-summary?symbol=TICKER
    Returns a list with one dict containing:
        lastMonth, lastMonthAvgPriceTarget,
        lastQuarter, lastQuarterAvgPriceTarget,
        lastYear, lastYearAvgPriceTarget,
        allTime, allTimeAvgPriceTarget,
        publishers (list of sources)

    Note: FMP Premium required. Returns [] on 402 / free plan.
    """
    return _get("price-target-summary", {"symbol": ticker})


def get_price_target_consensus(ticker: str) -> list:
    """
    Analyst price target consensus (avg, high, low, count).

    FMP endpoint: /price-target-consensus?symbol=TICKER
    Returns targetHigh, targetLow, targetConsensus, targetMedian.

    Note: FMP Premium required.
    """
    return _get("price-target-consensus", {"symbol": ticker})


# ------------------------------------------------------------------
# Earnings surprises
# ------------------------------------------------------------------

def get_earnings(ticker: str, limit: int = 20) -> list:
    """
    Historical earnings actuals vs. estimates (surprise data).

    Used to populate earnings_events for PEAD analysis.
    """
    return _get("earnings-surprises", {
        "symbol": ticker,
        "limit":  limit,
    })
