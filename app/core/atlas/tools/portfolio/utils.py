"""Shared utilities for tools portfolio tools."""

import pandas as pd

from app.core.calc_v2.portfolio import Portfolio
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.utils.time_utils import get_utc_date_str, get_utc_days_ago

SPY = "SPY"


# ================================
# --> Helper funcs
# ================================

def _build_ticker_factors(
    tickers: list[str],
    ohlcv_data: dict[str, pd.DataFrame],
    benchmark_prices: pd.Series,
) -> dict:
    """Compute TickerFactors for each holding using calc_all_factors directly.

    Fetches fundamentals in bulk (single DB round-trip) and computes factor
    exposures per ticker without constructing full Ticker objects.

    Args:
        tickers: Portfolio holding symbols.
        ohlcv_data: Pre-fetched OHLCV data keyed by ticker.
        benchmark_prices: SPY adj_close series for benchmark returns.

    Returns:
        dict[str, TickerFactors] mapping ticker → factor exposures.
    """
    from app.core.calc_v2.factors.calc_all import calc_all_factors
    from app.repositories.fundamentals.fetchers import get_bulk_fundamentals

    benchmark_returns = benchmark_prices.pct_change().dropna()
    fundamentals_map = get_bulk_fundamentals(tickers)

    ticker_factors = {}
    for t in tickers:
        adj_close = ohlcv_data[t]["adj_close"]
        daily_returns = adj_close.pct_change().dropna()
        fundamentals = fundamentals_map.get(t)
        ticker_factors[t] = calc_all_factors(
            adj_close=adj_close,
            daily_returns=daily_returns,
            benchmark_returns=benchmark_returns,
            fundamentals=fundamentals,
        )

    return ticker_factors


def build_portfolio_obj(
    tickers: list[str],
    weights: list[float],
    years_back: int,
    shocks: dict[str, float] | None = None,
    with_factors: bool = False,
) -> Portfolio:
    """Fetch price data and construct a Portfolio object with SPY benchmark.

    Args:
        tickers: List of uppercase ticker symbols.
        weights: Decimal portfolio weights per ticker (e.g. 0.30 = 30%). Negative = short.
        years_back: Number of years of historical data.
        shocks: Optional ETF shock magnitudes for stress testing (e.g. {"SPY": -0.05, "TLT": 0.10}).
            When provided, ETF price data is fetched and etf_returns_map is built for the Portfolio.
        with_factors: When True, compute ticker-level factor exposures and pass them to
            the Portfolio constructor, which triggers universe z-scoring and portfolio-level
            factor exposure calculation. Adds ~15-25s due to build_universe_factors().
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

    # Reason: compute ticker-level factors for portfolio factor exposure analysis
    ticker_factors = None
    if with_factors:
        ticker_factors = _build_ticker_factors(tickers, data, benchmark_prices)

    return Portfolio(
        name="Agent Portfolio",
        tickers=tickers,
        weights=weights,
        price_df=price_df,
        benchmark_prices=benchmark_prices,
        ticker_factors=ticker_factors,
        etf_returns_map=etf_returns_map,
        shocks=shocks,
    )
