"""Shared utilities for tools_v2 ticker tools."""

from typing import cast

import pandas as pd

from app.core.calc_v2.ticker import Ticker
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.utils.time_utils import get_utc_date_str, get_utc_days_ago

SPY = "SPY"


def build_ticker_obj(
    ticker: str,
    years_back: int,
    fundamentals: bool = False,
) -> Ticker:
    """Fetch OHLCV data and construct a Ticker object with benchmark.

    Args:  
        ticker: Uppercase ticker symbol.
        years_back: Number of years of historical data.
        fundamentals: If True, also fetch fundamentals for factor calculations.
    """
    end_date = get_utc_date_str()
    start_date = get_utc_days_ago(years_back * 365).strftime("%Y-%m-%d")

    tickers_to_fetch = [ticker]
    if ticker != SPY:
        tickers_to_fetch.append(SPY)

    data = fetch_bulk_ohlcv_data_for_tickers(tickers_to_fetch, start_date, end_date)

    if ticker not in data or data[ticker].empty:
        raise ValueError(f"No price data found for {ticker}")

    benchmark_prices = cast(pd.Series, data[SPY]["adj_close"]) if ticker != SPY else None

    fund_result = None
    if fundamentals:
        from app.repositories.fundamentals.fetchers import get_bulk_fundamentals
        fund_result = get_bulk_fundamentals([ticker]).get(ticker)

    return Ticker(
        ticker,
        data[ticker],
        benchmark_prices=benchmark_prices,
        fundamentals=fund_result,
    )
