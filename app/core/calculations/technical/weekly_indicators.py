from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional, Union

import pandas as pd

from app.repositories.price_data import get_price_data_daily
from app.core.calculations.technical.indicators import TechnicalIndicators


def fetch_weekly_ohlcv(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    week_ending: str = "W-FRI",
) -> pd.DataFrame:
    """Fetch daily OHLCV from DB and resample to weekly OHLCV.

    - week_ending: pandas offset alias for week end (e.g., 'W-FRI', 'W-MON').
    Returns a DataFrame indexed by week end with columns: open, high, low, close, volume.
    """
    end_dt = pd.Timestamp.now().normalize() if end_date is None else pd.to_datetime(end_date)
    start_dt = (end_dt - pd.DateOffset(years=5)) if start_date is None else pd.to_datetime(start_date)

    daily_df = get_price_data_daily(ticker, start_dt.to_pydatetime(), end_dt.to_pydatetime())
    if daily_df is None or daily_df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    daily_df = daily_df.copy()
    daily_df["date"] = pd.to_datetime(daily_df["date"])
    daily_df = daily_df.set_index("date").sort_index()

    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    weekly_df = daily_df.resample(week_ending).apply(agg)
    weekly_df = weekly_df.dropna(subset=["open", "high", "low", "close"], how="any")
    return weekly_df


def compute_weekly_indicators_for_ticker(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_adx: bool = True,
) -> Dict[str, Union[pd.Series, pd.DataFrame]]:
    """Compute key portfolio-relevant weekly indicators for a ticker.

    Returns dict of indicator name -> Series/DataFrame.
    """
    weekly = fetch_weekly_ohlcv(ticker, start_date, end_date, week_ending="W-FRI")
    if weekly.empty:
        return {}

    tech = TechnicalIndicators(weekly)

    results: Dict[str, Union[pd.Series, pd.DataFrame]] = {}
    results["weekly_close"] = weekly["close"]
    results["moving_averages_sma_10_26_52"] = tech.moving_averages([10, 26, 52], ma_type="sma")
    results["roc_12"] = tech.roc(period=12)
    results["macd_12_26_9"] = tech.macd()
    results["atr_14"] = tech.atr(period=14)
    results["donchian_20"] = tech.donchian_channels(period=20)
    results["keltner_20"] = tech.keltner_channels(period=20, multiplier=2.0)
    if include_adx:
        results["adx_14"] = tech.adx(period=14)
    return results


def print_weekly_indicators(
    indicators: Dict[str, Union[pd.Series, pd.DataFrame]],
    tail: int = 10,
) -> None:
    """Pretty-print the last N rows of each indicator."""
    if not indicators:
        print("No data/indicators to display.")
        return
    for name, obj in indicators.items():
        print(f"\n{name} (last {tail}):")
        try:
            print(obj.tail(tail))
        except Exception:
            # Fallback in case non-standard object slips in
            print(obj)


if __name__ == "__main__":
    # Example usage:
    # Compute and print indicators for SPY over the last 5 years (weekly)
    ticker_symbol = "AAL"
    out = compute_weekly_indicators_for_ticker(ticker_symbol)
    print_weekly_indicators(out, tail=52)


