"""
finnhub_client.py
-----------------
Data-pipeline wrapper for Finnhub news endpoints.

NOTE: This file is for the data pipeline only.
      The existing Flask route at backend/routes/news.py and
      backend/services/finnhub_service.py are NOT touched — they
      continue to work exactly as before.

This module adds:
  - fetch_company_news()  → company-specific news with date range (for pipeline)
  - fetch_market_news_raw() → raw general market news (for pipeline)
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
BASE_URL        = "https://finnhub.io/api/v1"


def _get(endpoint: str, params: dict = None) -> list:
    """Internal GET helper. Returns list or empty list on error."""
    if not FINNHUB_API_KEY:
        raise EnvironmentError("FINNHUB_API_KEY is not set in your .env file.")

    url = f"{BASE_URL}/{endpoint}"
    all_params = {"token": FINNHUB_API_KEY}
    if params:
        all_params.update(params)

    try:
        resp = requests.get(url, params=all_params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []
    except requests.exceptions.RequestException as e:
        print(f"[Finnhub] Request failed for {endpoint}: {e}")
        return []


def fetch_company_news(ticker: str, from_date: str, to_date: str) -> list:
    """
    Fetch company-specific news articles for a ticker within a date range.

    Args:
        ticker:    Stock symbol, e.g. "NVDA"
        from_date: Start date "YYYY-MM-DD"
        to_date:   End date   "YYYY-MM-DD"

    Returns:
        List of article dicts with keys:
            category, datetime, headline, id, image, related,
            source, summary, url
    """
    articles = _get("company-news", {
        "symbol": ticker,
        "from":   from_date,
        "to":     to_date,
    })
    print(f"[Finnhub] {ticker} ({from_date} → {to_date}): {len(articles)} articles")
    return articles


def fetch_market_news_raw(category: str = "general") -> list:
    """
    Fetch general market news (not company-specific).

    Args:
        category: "general", "forex", "crypto", or "merger"

    Returns:
        List of article dicts.
    """
    articles = _get("news", {"category": category})
    print(f"[Finnhub] market news ({category}): {len(articles)} articles")
    return articles
