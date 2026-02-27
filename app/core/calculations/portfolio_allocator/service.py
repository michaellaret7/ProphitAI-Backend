"""Portfolio Allocation Service.

Public entry point for portfolio allocation.
"""

from typing import Dict, List

from app.core.calculations.portfolio_allocator.models import (
    OptimizerConfig,
    Allocation,
    AllocationResult,
    PortfolioPerformance,
    StrategyLiteral,
)
from app.core.calculations.portfolio_allocator.allocator import PortfolioAllocator


def calc_num_shares(weights: Dict[str, float], portfolio_value: float) -> Dict[str, float]:
    """Calculate the number of shares for each ticker based on weights and portfolio value.

    Returns:
        Dict mapping ticker symbols to number of shares (fractional).

    Raises:
        ValueError: If portfolio_value is invalid or price data is unavailable.
    """
    from app.db.core.pull_fmp_data import FMP_API_DATA

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
        num_shares[ticker] = round(weight * portfolio_value / prices[ticker], 4)

    return num_shares


def calc_position_navs(positions: Dict[str, float]) -> Dict[str, float]:
    """Calculate position NAV (num_shares * current_price) for each position.

    Args:
        positions: Dict mapping ticker symbols to num_shares.

    Returns:
        Dict mapping ticker symbols to position_nav values.

    Note:
        Positions with None or zero num_shares are skipped.
        If price fetch fails for a ticker, it will be omitted from results.
    """
    from app.db.core.pull_fmp_data import FMP_API_DATA

    if not positions:
        return {}

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

    prices = {}
    for quote in live_prices:
        symbol = quote.get("symbol")
        price = quote.get("price")
        if symbol and price is not None and price > 0:
            prices[symbol] = price

    position_navs = {}
    for ticker, num_shares in tickers_with_shares.items():
        price = prices.get(ticker)
        if price is not None:
            position_navs[ticker] = num_shares * price

    return position_navs


def allocate(
    tickers: List[str],
    config: OptimizerConfig,
    strategy: StrategyLiteral = "max_sharpe",
    risk_aversion: float = 5.0,
    target_volatility: float = 0.12,
    target_return: float = 0.15,
) -> AllocationResult:
    """Allocate a portfolio using the specified strategy.

    Workflow: init optimizer → fetch prices → compute inputs → optimize → calc shares.
    """
    opt = PortfolioAllocator(tickers=tickers, config=config)

    prices = opt.fetch_prices()
    ordered_tickers, mu, cov_matrix = opt.compute_inputs(prices)

    w, perf = opt.optimize(
        mu, cov_matrix, ordered_tickers,
        strategy=strategy,
        risk_aversion=risk_aversion,
        target_volatility=target_volatility,
        target_return=target_return,
    )

    num_shares = calc_num_shares(w, config.initial_portfolio_value)

    allocations = [
        Allocation(ticker=ticker, weight=weight, num_shares=num_shares[ticker])
        for ticker, weight in w.items()
    ]

    performance = PortfolioPerformance(
        expected_return=float(round(perf[0], 4)),
        volatility=float(round(perf[1], 4)),
        sharpe_ratio=float(round(perf[2], 4)),
    )

    return AllocationResult(
        allocations=allocations,
        performance=performance,
        strategy=strategy,
    )


def run(
    tickers: List[str],
    equity_weight_target: float = 0.60,
    bond_weight_target: float = 0.40,
    commodity_weight_target: float = 0.0,
    crypto_weight_target: float = 0.0,
    initial_portfolio_value: float = 10_000,
    strategy: StrategyLiteral = "max_sharpe",
) -> AllocationResult:
    """Run portfolio allocation with simplified parameters.

    Asset class weights are auto-adjusted if the provided tickers
    don't include all asset classes.
    """
    config = OptimizerConfig(
        equity_weight_target=equity_weight_target,
        bond_weight_target=bond_weight_target,
        commodity_weight_target=commodity_weight_target,
        crypto_weight_target=crypto_weight_target,
        initial_portfolio_value=initial_portfolio_value,
    )

    return allocate(
        tickers=tickers,
        config=config,
        strategy=strategy,
    )


if __name__ == "__main__":
    import time

    tickers = [
        # Equities
        "AAPL", "MU", "GOOGL", "AMZN", "TSLA", "NVDA", "META",
        # Commodities
        "GLD", "SLV", "DBA",
        # Bonds
        "AGG", "BND", "TLT",
    ]

    start = time.time()
    result = run(
        tickers=tickers,
        initial_portfolio_value=100_000,
        equity_weight_target=0.55,
        bond_weight_target=0.15,
        commodity_weight_target=0.30,
        strategy="max_sharpe",
    )
    elapsed = time.time() - start

    print(f"Strategy: {result.strategy}")
    print(f"Time: {elapsed:.2f}s\n")
    print(f"Expected Return: {result.performance.expected_return:.2%}")
    print(f"Volatility: {result.performance.volatility:.2%}")
    print(f"Sharpe Ratio: {result.performance.sharpe_ratio:.4f}\n")

    print(f"{'Ticker':<8} {'Weight':>8} {'Shares':>8}")
    print("-" * 26)
    for a in sorted(result.allocations, key=lambda x: x.weight, reverse=True):
        print(f"{a.ticker:<8} {a.weight:>7.2%} {a.num_shares:>8}")
