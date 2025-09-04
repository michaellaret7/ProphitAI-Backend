from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from backend.src.calculations_v2.core import DataService
from backend.src.calculations_v2.performance import PerformanceCalculator
from backend.src.calculations_v2.returns import (
    PortfolioReturnsCalculator,
    ReturnsCalculator,
)


def main() -> None:
    """
    Demonstrates building and evaluating a long-short equity portfolio
    using the calculations_v2 toolkit.
    """
    portfolio_weights = {
        "NVDA": 0.35,
        "SPY": 0.30,  # Long
        "QQQ": 0.25,  # Long
        "TLT": 0.25,  # Short
        "IEF": 0.40,  # Short
        "HYG": 0.30,  # Short
        "XLF": -0.20,  # Short
    }
    weights_series = pd.Series(portfolio_weights)

    print("=" * 60)
    print("Long-Short Portfolio Performance Evaluation")
    print("=" * 60)
    print(f"Gross Exposure: {weights_series.abs().sum():.2%}")
    print(f"Net Exposure: {weights_series.sum():.2%}")
    print("-" * 60)

    # 2. Fetch Historical Price Data
    ds = DataService()
    tickers = list(portfolio_weights.keys())
    benchmark_ticker = "SPY"
    end = datetime.now()
    start = end - timedelta(days=365 * 3)  # 3 years of data

    print(f"Fetching data for tickers: {tickers + [benchmark_ticker]}")
    print(f"Time period: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
    price_data = ds.get_bulk_close_series(tickers + [benchmark_ticker], start, end)

    # 3. Calculate Daily Returns for Each Asset
    ticker_returns = {
        ticker: ReturnsCalculator.daily_price_returns(prices)
        for ticker, prices in price_data.items()
        if prices is not None and not prices.empty
    }

    # 4. Calculate the Portfolio's Daily Return Series
    print("\nCalculating portfolio daily returns...")
    portfolio_daily_returns = PortfolioReturnsCalculator.weighted_daily_returns(
        ticker_returns=ticker_returns, weights=portfolio_weights, dropna=True
    )

    if portfolio_daily_returns.empty:
        print("\nCould not calculate portfolio returns. Exiting.")
        return

    # 5. Compute and Display Performance Metrics
    print("\n--- Portfolio Performance Metrics ---")

    # --- Absolute Performance Metrics ---
    sharpe = PerformanceCalculator.sharpe_ratio(portfolio_daily_returns)
    sortino = PerformanceCalculator.sortino_ratio(portfolio_daily_returns)
    cagr = PerformanceCalculator.cagr_from_returns(portfolio_daily_returns)

    equity_curve = (1 + portfolio_daily_returns).cumprod()
    mdd = (equity_curve / equity_curve.cummax() - 1.0).min()
    calmar = PerformanceCalculator.calmar_ratio(cagr, mdd)

    print(f"\n[Risk-Adjusted Returns]")
    print(f"  CAGR: {cagr:.2%}")
    print(f"  Sharpe Ratio: {sharpe:.2f}")
    print(f"  Sortino Ratio: {sortino:.2f}")
    print(f"  Calmar Ratio: {calmar:.2f}")

    print(f"\n[Risk & Drawdown]")
    print(f"  Annualized Volatility: {portfolio_daily_returns.std() * (252**0.5):.2%}")
    print(f"  Max Drawdown: {mdd:.2%}")

    # --- Benchmark-Relative Metrics ---
    spy_returns = ticker_returns.get(benchmark_ticker)
    if spy_returns is not None and not spy_returns.empty:
        print("\n--- Benchmark-Relative Metrics (vs. SPY) ---")
        alpha = PerformanceCalculator.alpha_jensen(portfolio_daily_returns, spy_returns)
        info_ratio = PerformanceCalculator.information_ratio(
            portfolio_daily_returns, spy_returns
        )
        up_capture, down_capture = PerformanceCalculator.capture_ratios(
            portfolio_daily_returns, spy_returns
        )
        tracking_error = PerformanceCalculator.tracking_error(
            portfolio_daily_returns, spy_returns
        )

        print(f"  Alpha (Jensen): {alpha:.4f}")
        print(f"  Information Ratio: {info_ratio:.2f}")
        print(f"  Tracking Error: {tracking_error:.2%}")
        print(f"  Up/Down Capture Ratio: {up_capture:.2f} / {down_capture:.2f}")
    else:
        print("\nCould not fetch benchmark data to calculate relative metrics.")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
    from backend.src.db.core.market_data_models import *
    from backend.src.db.core.db_config import *
