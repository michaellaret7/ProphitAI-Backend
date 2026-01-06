"""Portfolio calculation utilities to reduce code duplication."""

from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple, Optional
import pandas as pd

from app.core.calculations.core.data_service import DataService
from app.core.calculations.returns.calculator import ReturnsCalculator, PortfolioReturnsCalculator
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.simulation_utils import get_end_date, filter_series_by_date


def prepare_portfolio_data(
    portfolio: Dict,
    lookback_days: int = 252,
    include_dividends: bool = True,
    include_benchmark: Optional[str] = None,
    _simulation_date: Optional[datetime] = None
) -> Tuple[Dict[str, float], Dict[str, pd.Series], Dict[str, pd.Series], pd.Series]:
    """
    Common utility to prepare portfolio data for calculations.

    Args:
        portfolio: Dict with structure {"TICKER": {"position": "long/short", "allocation": 0.xx}}
        lookback_days: Number of days to look back for historical data
        include_dividends: Whether to fetch dividend data
        include_benchmark: Optional benchmark ticker to include (e.g., "SPY")
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
        Tuple of:
        - weights: Dict[str, float] with signed weights (negative for shorts)
        - price_data: Dict[str, pd.Series] of price series
        - dividend_data: Dict[str, pd.Series] of dividend series (or None if not requested)
        - portfolio_returns: pd.Series of weighted portfolio returns
    """
    # 1. Date range
    end = get_end_date(_simulation_date)
    start = end - timedelta(days=lookback_days)
    
    # 2. Get tickers
    tickers = list(portfolio.keys())
    if include_benchmark and include_benchmark not in tickers:
        tickers.append(include_benchmark)
    
    # 3. Fetch price data
    ds = DataService()
    price_data = ds.get_bulk_close_series(tickers, start, end)

    # Filter price data by simulation date if provided
    if _simulation_date is not None:
        for ticker in price_data:
            price_data[ticker] = filter_series_by_date(price_data[ticker], _simulation_date)

    # 4. Get dividend data if requested
    dividend_data = {}
    if include_dividends:
        for ticker in tickers:
            try:
                div_data = ds.get_dividends(ticker, start, end)
                dividend_data[ticker] = filter_series_by_date(div_data.series, _simulation_date)
            except (ValueError, KeyError, AttributeError):
                # Reason: Dividend data may not exist for all tickers (e.g., bonds, ETFs)
                dividend_data[ticker] = None
    
    # 5. Convert portfolio to weights (negative for shorts)
    weights = {}
    for ticker, details in portfolio.items():
        if details["position"].lower() == "short":
            weights[ticker] = -abs(details["allocation"])
        else:
            weights[ticker] = abs(details["allocation"])
    
    return weights, price_data, dividend_data


def get_portfolio_returns(
    portfolio: Dict,
    lookback_days: int = 252,
    use_total_returns: bool = True,
    dropna: bool = True,
    renormalize_each_day: bool = False,
    normalization: str = "gross",
    _simulation_date: Optional[datetime] = None
) -> Tuple[pd.Series, Dict[str, float]]:
    """
    Calculate portfolio returns from portfolio dict.

    Args:
        portfolio: Dict with structure {"TICKER": {"position": "long/short", "allocation": 0.xx}}
        lookback_days: Number of days to look back
        use_total_returns: Whether to include dividends in returns
        dropna: Whether to drop days with missing data
        renormalize_each_day: Whether to renormalize weights daily
        normalization: "gross" or "net" exposure normalization
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
        Tuple of:
        - portfolio_returns: pd.Series of weighted portfolio returns
        - weights: Dict of signed weights used
    """
    # Get all the data
    weights, price_data, dividend_data = prepare_portfolio_data(
        portfolio,
        lookback_days,
        include_dividends=use_total_returns,
        _simulation_date=_simulation_date
    )
    
    # Calculate individual ticker returns
    ticker_returns = {}
    for ticker in weights:
        if ticker in price_data and not price_data[ticker].empty:
            if use_total_returns:
                divs = dividend_data.get(ticker)
                ticker_returns[ticker] = ReturnsCalculator.total_returns(price_data[ticker], divs)
            else:
                ticker_returns[ticker] = ReturnsCalculator.daily_price_returns(price_data[ticker])
    
    # Calculate weighted portfolio returns
    portfolio_returns = PortfolioReturnsCalculator.weighted_daily_returns(
        ticker_returns=ticker_returns,
        weights=weights,
        dropna=dropna,
        renormalize_each_day=renormalize_each_day,
        normalization=normalization
    )
    
    return portfolio_returns, weights


def get_benchmark_returns(
    benchmark: str = "SPY",
    start: datetime = None,
    end: datetime = None,
    lookback_days: int = None,
    use_total_returns: bool = True,
    _simulation_date: Optional[datetime] = None
) -> pd.Series:
    """
    Get benchmark returns for comparison.

    Args:
        benchmark: Benchmark ticker
        start/end: Date range (if not provided, uses lookback_days)
        lookback_days: Alternative to start/end
        use_total_returns: Whether to include dividends
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
        pd.Series of benchmark returns
    """
    if not end:
        end = get_end_date(_simulation_date)

    if not start:
        if lookback_days:
            start = end - timedelta(days=lookback_days)
        else:
            raise ValueError("Must provide either start date or lookback_days")

    ds = DataService()
    bench_prices = ds.get_bulk_close_series([benchmark], start, end).get(benchmark)

    # Filter by simulation date if provided
    bench_prices = filter_series_by_date(bench_prices, _simulation_date)

    if bench_prices is None or bench_prices.empty:
        raise ValueError(f"No price data for benchmark {benchmark}")

    if use_total_returns:
        try:
            div_data = ds.get_dividends(benchmark, start, end)
            bench_divs = div_data.series
            bench_divs = filter_series_by_date(bench_divs, _simulation_date)
        except (ValueError, KeyError, AttributeError):
            # Reason: Some benchmarks may not have dividend data available
            bench_divs = None
        return ReturnsCalculator.total_returns(bench_prices, bench_divs)
    else:
        return ReturnsCalculator.daily_price_returns(bench_prices)

def format_correlation_matrix(correlation_matrix: pd.DataFrame) -> dict:
    tickers = list(correlation_matrix.columns)
    values = correlation_matrix.values
    pairs: dict[str, float] = {}
    n = len(tickers)
    for i in range(n):
        for j in range(i + 1, n):
            val = float(values[i, j])
            if val > 0.5:
                key = f"{tickers[i]}|{tickers[j]}"
                pairs[key] = round(val, 3)
    return pairs


def calc_num_shares(weights: Dict[str, float], portfolio_value: float) -> Dict[str, int]:
    """
    Calculate the number of shares for each ticker based on weights and portfolio value.

    Args:
        weights: Dict mapping ticker symbols to weight fractions (must sum to ~1.0)
        portfolio_value: Total portfolio value in dollars

    Returns:
        Dict mapping ticker symbols to number of shares (integer, rounded down)

    Raises:
        ValueError: If portfolio_value is invalid or price data is unavailable
    """
    if portfolio_value is None or portfolio_value <= 0:
        raise ValueError(f"portfolio_value must be positive, got: {portfolio_value}")

    if not weights:
        return {}

    fmp_data = FMP_API_DATA()
    live_prices = fmp_data.get_batch_quote(list(weights.keys()))

    if not live_prices:
        raise ValueError("Failed to fetch live prices from FMP API")

    prices = {}
    for quote in live_prices:
        symbol = quote.get("symbol")
        price = quote.get("price")
        if symbol and price is not None and price > 0:
            prices[symbol] = price

    missing = set(weights.keys()) - set(prices.keys())
    if missing:
        raise ValueError(f"Missing price data for tickers: {sorted(missing)}")

    num_shares = {}
    for ticker, weight in weights.items():
        # Calculate and round down to whole shares
        num_shares[ticker] = int(weight * portfolio_value / prices[ticker])

    return num_shares


def calc_position_navs(positions: Dict[str, int]) -> Dict[str, float]:
    """
    Calculate position NAV (num_shares * current_price) for each position.

    Args:
        positions: Dict mapping ticker symbols to num_shares (integer)

    Returns:
        Dict mapping ticker symbols to position_nav values

    Note:
        Positions with None or zero num_shares are skipped.
        If price fetch fails for a ticker, it will be omitted from results.
    """
    if not positions:
        return {}

    # Filter positions that have valid num_shares
    tickers_with_shares = {
        ticker: num_shares
        for ticker, num_shares in positions.items()
        if num_shares is not None and num_shares > 0
    }

    if not tickers_with_shares:
        return {}

    fmp_data = FMP_API_DATA()
    live_prices = fmp_data.get_batch_quote(list(tickers_with_shares.keys()))

    if not live_prices:
        return {}

    # Build price map from API response
    prices = {}
    for quote in live_prices:
        symbol = quote.get("symbol")
        price = quote.get("price")
        if symbol and price is not None and price > 0:
            prices[symbol] = price

    # Calculate position NAV for each ticker
    position_navs = {}
    for ticker, num_shares in tickers_with_shares.items():
        price = prices.get(ticker)
        if price is not None:
            position_navs[ticker] = num_shares * price

    return position_navs
