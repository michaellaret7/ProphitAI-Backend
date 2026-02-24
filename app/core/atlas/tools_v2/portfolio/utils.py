"""Shared utilities for tools_v2 portfolio tools."""

import pandas as pd

from app.core.calc_v2.portfolio import Portfolio
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.utils.time_utils import get_utc_date_str, get_utc_days_ago

SPY = "SPY"


def build_portfolio_obj(
    tickers: list[str],
    weights: list[float],
    years_back: int,
    shocks: dict[str, float] | None = None,
) -> Portfolio:
    """Fetch price data and construct a Portfolio object with SPY benchmark.

    Args:
        tickers: List of uppercase ticker symbols.
        weights: Decimal portfolio weights per ticker (e.g. 0.30 = 30%). Negative = short.
        years_back: Number of years of historical data.
        shocks: Optional ETF shock magnitudes for stress testing (e.g. {"SPY": -0.05, "TLT": 0.10}).
            When provided, ETF price data is fetched and etf_returns_map is built for the Portfolio.
    """
    tickers = [t.upper().strip() for t in tickers]

    end_date = get_utc_date_str()
    start_date = get_utc_days_ago(years_back * 365).strftime("%Y-%m-%d")

    # Reason: always fetch SPY for benchmark; include ETF tickers if stress testing
    etf_tickers = list(shocks.keys()) if shocks else []
    fetch_list = list(set(tickers + [SPY] + etf_tickers))
    data = fetch_bulk_ohlcv_data_for_tickers(fetch_list, start_date, end_date)

    missing = [t for t in tickers if t not in data or data[t].empty]
    if missing:
        raise ValueError(f"No price data found for: {missing}")

    price_df = pd.DataFrame({t: data[t]["adj_close"] for t in tickers})
    benchmark_prices = data[SPY]["adj_close"]

    # Reason: build ETF returns map for stress testing when shocks are provided
    etf_returns_map: dict[str, pd.Series] | None = None
    if shocks:
        missing_etfs = [e for e in shocks if e not in data or data[e].empty]
        if missing_etfs:
            raise ValueError(f"No price data found for ETF factors: {missing_etfs}")
        etf_returns_map = {
            etf: data[etf]["adj_close"].pct_change().dropna()
            for etf in shocks
        }

    return Portfolio(
        name="Agent Portfolio",
        tickers=tickers,
        weights=weights,
        price_df=price_df,
        benchmark_prices=benchmark_prices,
        etf_returns_map=etf_returns_map,
        shocks=shocks,
    )
