"""
Portfolio Allocation Service

Public entry point for portfolio allocation with the same interface as the original run() function.
"""

from typing import List

from app.core.calculations.portfolio.allocator.models import (
    OptimizerConfig,
    Allocation,
    AllocationResult,
    PortfolioPerformance,
    StrategyLiteral,
)
from app.core.calculations.portfolio.allocator.allocator import PortfolioAllocator
from app.core.calculations.portfolio.utils import calc_num_shares


def allocate(
    tickers: List[str],
    config: OptimizerConfig,
    strategy: StrategyLiteral = "max_sharpe",
    risk_aversion: float = 5.0,
    target_volatility: float = 0.12,
    target_return: float = 0.15,
) -> AllocationResult:
    """
    Allocate a portfolio using the specified strategy.

    This is the core allocation function that handles the full workflow:
    1. Initialize optimizer with tickers and config
    2. Fetch historical prices
    3. Compute expected returns and covariance
    4. Run optimization strategy
    5. Calculate share counts
    6. Return structured result

    Args:
        tickers: List of ticker symbols
        config: OptimizerConfig with all optimization parameters
        strategy: Optimization strategy to use
        risk_aversion: Risk aversion parameter for max_utility strategy
        target_volatility: Target volatility for efficient_risk strategy
        target_return: Target return for efficient_return strategy

    Returns:
        AllocationResult with allocations, performance, and strategy
    """
    opt = PortfolioAllocator(tickers=tickers, config=config)

    prices = opt.fetch_prices()
    ordered_tickers, mu, S = opt.compute_inputs(prices)

    w, perf = opt.optimize(
        mu, S, ordered_tickers,
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
    initial_portfolio_value: float = 10_000,
    strategy: StrategyLiteral = "max_sharpe",
) -> AllocationResult:
    """
    Run portfolio allocation with simplified parameters.

    This is the main public entry point. Asset class weights are auto-adjusted
    if the provided tickers don't include all asset classes.

    Args:
        tickers: List of ticker symbols
        equity_weight_target: Target equity allocation (default: 60%)
        bond_weight_target: Target bond allocation (default: 40%)
        commodity_weight_target: Target commodity allocation (default: 0%)
        initial_portfolio_value: Portfolio value for share calculation
        strategy: Optimization strategy to use

    Returns:
        AllocationResult with allocations, performance, and strategy

    Note:
        Weight targets must sum to 1.0. If only some asset classes are present
        in the tickers, weights are automatically redistributed proportionally.
    """
    config = OptimizerConfig(
        equity_weight_target=equity_weight_target,
        bond_weight_target=bond_weight_target,
        commodity_weight_target=commodity_weight_target,
        initial_portfolio_value=initial_portfolio_value,
    )

    return allocate(
        tickers=tickers,
        config=config,
        strategy=strategy,
    )


if __name__ == "__main__":
    # Test with equity + bonds (commodities auto-excluded since none present)
    final_output = run(
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "GLD", "SLV", "DBA", "AGG", "BND", "TLT"],
        initial_portfolio_value=100_000,
        equity_weight_target=0.7,
        bond_weight_target=0.2,
        commodity_weight_target=0.1,
        strategy="max_sharpe"
    )

    print(final_output.model_dump_json(indent=4))
