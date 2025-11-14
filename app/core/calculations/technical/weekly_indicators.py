from __future__ import annotations

from typing import Dict, Optional, Union

import pandas as pd

from app.repositories.price_data import get_price_data_daily
from app.core.calculations.technical.indicators import TechnicalIndicators
import tiktoken


def count_dataframe_tokens(df: pd.DataFrame, encoding_name: str = "cl100k_base") -> int:
    """Count the number of tokens in a dataframe when converted to string.

    Args:
        df: DataFrame to count tokens for
        encoding_name: Tiktoken encoding to use (default: cl100k_base for GPT-4)

    Returns:
        Total token count for the dataframe
    """
    if df.empty:
        return 0

    encoding = tiktoken.get_encoding(encoding_name)
    df_string = df.to_string()
    token_count = len(encoding.encode(df_string))
    return token_count


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
    include_token_counts: bool = False,
) -> Union[Dict[str, Union[pd.Series, pd.DataFrame]], tuple[Dict[str, Union[pd.Series, pd.DataFrame]], Dict[str, int]]]:
    """Compute key portfolio-relevant weekly indicators for a ticker.

    Args:
        ticker: Stock ticker symbol
        start_date: Start date for data
        end_date: End date for data
        include_adx: Whether to include ADX indicator
        include_token_counts: Whether to return token counts for each indicator

    Returns:
        If include_token_counts is False: dict of indicator name -> Series/DataFrame
        If include_token_counts is True: tuple of (indicators dict, token_counts dict)
    """
    weekly = fetch_weekly_ohlcv(ticker, start_date, end_date, week_ending="W-FRI")
    if weekly.empty:
        return ({}, {}) if include_token_counts else {}

    tech = TechnicalIndicators(weekly)

    results: Dict[str, Union[pd.Series, pd.DataFrame]] = {}

    # Moving averages with close price for comparison
    ma_df = tech.moving_averages([10, 26, 52], ma_type="sma")
    ma_df.insert(0, "close", weekly["close"])
    results["moving_averages_sma_10_26_52"] = ma_df

    # ROC with close price for context
    roc_df = tech.roc(period=12).to_frame(name="roc_12")
    roc_df.insert(0, "close", weekly["close"])
    results["roc_12"] = roc_df

    # MACD with close price for divergence analysis
    macd_df = tech.macd()
    macd_df.insert(0, "close", weekly["close"])
    results["macd_12_26_9"] = macd_df

    # ATR with close price to understand volatility relative to price
    atr_df = tech.atr(period=14).to_frame(name="atr_14")
    atr_df.insert(0, "close", weekly["close"])
    results["atr_14"] = atr_df

    # Donchian channels with close to see position within channel
    donchian_df = tech.donchian_channels(period=20)
    donchian_df.insert(0, "close", weekly["close"])
    results["donchian_20"] = donchian_df

    # Keltner channels with close to see position within channel
    keltner_df = tech.keltner_channels(period=20, multiplier=2.0)
    keltner_df.insert(0, "close", weekly["close"])
    results["keltner_20"] = keltner_df

    if include_adx:
        # ADX with close for trend context
        adx_df = tech.adx(period=14)
        adx_df.insert(0, "close", weekly["close"])
        results["adx_14"] = adx_df

    if include_token_counts:
        token_counts: Dict[str, int] = {}
        for name, df in results.items():
            token_counts[name] = count_dataframe_tokens(df)
        return results, token_counts

    return results


def print_weekly_indicators(
    indicators: Dict[str, Union[pd.Series, pd.DataFrame]],
    tail: int = 10,
    token_counts: Optional[Dict[str, int]] = None,
) -> None:
    """Pretty-print the last N rows of each indicator with optional token counts.

    Args:
        indicators: Dictionary of indicator name -> Series/DataFrame
        tail: Number of rows to display from the end
        token_counts: Optional dictionary of indicator name -> token count
    """
    if not indicators:
        print("No data/indicators to display.")
        return

    total_tokens = 0
    for name, obj in indicators.items():
        token_info = ""
        if token_counts and name in token_counts:
            tokens = token_counts[name]
            total_tokens += tokens
            token_info = f" [Tokens: {tokens:,}]"

        print(f"\n{name} (last {tail}){token_info}:")
        try:
            print(obj.tail(tail))
        except Exception:
            # Fallback in case non-standard object slips in
            print(obj)

    if token_counts:
        print(f"\n{'='*60}")
        print(f"Total tokens across all indicators: {total_tokens:,}")
        print(f"{'='*60}")


if __name__ == "__main__":
    # Example usage:
    # Compute and print indicators for AAL over the last 5 years (weekly)
    ticker_symbol = "AAL"

    # Example 1: Without token counts
    print("=" * 80)
    print(f"Weekly Technical Indicators for {ticker_symbol}")
    print("=" * 80)
    out = compute_weekly_indicators_for_ticker(ticker_symbol)
    print_weekly_indicators(out, tail=10)

    # Example 2: With token counts
    print("\n\n" + "=" * 80)
    print(f"Weekly Technical Indicators for {ticker_symbol} (with token counts)")
    print("=" * 80)
    indicators, tokens = compute_weekly_indicators_for_ticker(ticker_symbol, include_token_counts=True)
    print_weekly_indicators(indicators, tail=10, token_counts=tokens)


