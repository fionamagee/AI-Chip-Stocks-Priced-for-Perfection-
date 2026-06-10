"""
yfinance_client.py
------------------
Fetch daily OHLCV price history using yfinance.

All functions return a pandas DataFrame with columns:
    ticker, date, open, high, low, close, adjusted_close, volume
"""

import yfinance as yf
import pandas as pd


def fetch_price_history(ticker: str, period: str = "5y") -> pd.DataFrame:
    """
    Download daily price history for a single ticker.

    Args:
        ticker: Stock symbol, e.g. "NVDA"
        period: yfinance period string — "1y", "2y", "5y", "max", etc.
                Use "max" for a full backfill on first run.

    Returns:
        DataFrame with columns:
            ticker, date, open, high, low, close, adjusted_close, volume
        Returns an empty DataFrame if the download fails.
    """
    try:
        raw = yf.download(
            ticker,
            period=period,
            auto_adjust=False,   # keep both Close and Adj Close
            progress=False,
            threads=False,
        )
    except Exception as e:
        print(f"[yfinance] Error downloading {ticker}: {e}")
        return pd.DataFrame()

    if raw.empty:
        print(f"[yfinance] No data returned for {ticker}")
        return pd.DataFrame()

    # yfinance returns a MultiIndex when auto_adjust=False
    # Flatten column names if needed
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    df = pd.DataFrame({
        "ticker":         ticker,
        "date":           raw.index.date,
        "open":           raw["Open"],
        "high":           raw["High"],
        "low":            raw["Low"],
        "close":          raw["Close"],
        "adjusted_close": raw["Adj Close"],
        "volume":         raw["Volume"].astype("Int64"),
    })

    df = df.dropna(subset=["close"])
    df = df.reset_index(drop=True)

    print(f"[yfinance] {ticker}: {len(df)} rows fetched")
    return df


def fetch_price_history_range(
    ticker: str,
    start: str,
    end: str
) -> pd.DataFrame:
    """
    Download daily price history between explicit start/end dates.

    Args:
        ticker: Stock symbol
        start:  Start date string "YYYY-MM-DD"
        end:    End date string "YYYY-MM-DD"

    Returns:
        Same column structure as fetch_price_history()
    """
    try:
        raw = yf.download(
            ticker,
            start=start,
            end=end,
            auto_adjust=False,
            progress=False,
            threads=False,
        )
    except Exception as e:
        print(f"[yfinance] Error downloading {ticker} ({start} → {end}): {e}")
        return pd.DataFrame()

    if raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    df = pd.DataFrame({
        "ticker":         ticker,
        "date":           raw.index.date,
        "open":           raw["Open"],
        "high":           raw["High"],
        "low":            raw["Low"],
        "close":          raw["Close"],
        "adjusted_close": raw["Adj Close"],
        "volume":         raw["Volume"].astype("Int64"),
    })

    df = df.dropna(subset=["close"])
    df = df.reset_index(drop=True)
    return df
