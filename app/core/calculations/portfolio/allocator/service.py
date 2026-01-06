"""
Portfolio Allocation Service

Public entry point for portfolio allocation with the same interface as the original run() function.
"""

import json
from typing import List, Literal

from app.core.calculations.portfolio.allocator.models import (
    OptimizerConfig,
    Allocation,
    AllocationResult,
    PortfolioPerformance,
)
from app.core.calculations.portfolio.allocator.allocator import PortfolioAllocator
from app.core.calculations.portfolio.utils import calc_num_shares


def allocate(
    tickers: List[str],
    config: OptimizerConfig,
    strategy: Literal["max_sharpe", "min_vol", "max_utility", "efficient_risk", "efficient_return"] = "max_sharpe",
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

    Returns:
        AllocationResult with allocations, performance, and strategy
    """
    opt = PortfolioAllocator(tickers=tickers, config=config)

    prices = opt.fetch_prices()
    ordered_tickers, mu, S = opt.compute_inputs(prices)

    if strategy == "max_sharpe":
        w, perf = opt.optimize_max_sharpe(mu, S, ordered_tickers)
    elif strategy == "min_vol":
        w, perf = opt.optimize_min_vol(mu, S, ordered_tickers)
    elif strategy == "max_utility":
        w, perf = opt.optimize_max_utility(mu, S, ordered_tickers, risk_aversion=risk_aversion)
    elif strategy == "efficient_risk":
        w, perf = opt.optimize_efficient_risk(mu, S, ordered_tickers, target_volatility=target_volatility)
    elif strategy == "efficient_return":
        w, perf = opt.optimize_efficient_return(mu, S, ordered_tickers, target_return=target_return)
    else:
        raise ValueError(f"Unknown optimization strategy: {strategy}")

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
    initial_portfolio_value: float = 10_000,
    strategy: Literal["max_sharpe", "min_vol", "max_utility", "efficient_risk", "efficient_return"] = "max_sharpe",
) -> AllocationResult:
    """
    Run portfolio allocation with simplified parameters.

    This is the main public entry point that matches the original allocate.py interface.

    Args:
        tickers: List of ticker symbols
        equity_weight_target: Target equity allocation (default: 60%)
        bond_weight_target: Target bond allocation (default: 40%)
        initial_portfolio_value: Portfolio value for share calculation
        strategy: Optimization strategy to use

    Returns:
        AllocationResult with allocations, performance, and strategy
    """
    if not tickers:
        raise ValueError("tickers list is empty.")

    config = OptimizerConfig(
        # Bucket targets with bands
        equity_weight_target=equity_weight_target,
        bond_weight_target=bond_weight_target,
        bucket_band=0.05,  # ±5% flexibility around targets

        # Initial portfolio value
        initial_portfolio_value=initial_portfolio_value,

        # Position constraints (hybrid hard/soft)
        min_weight=0.01,  # HARD 1% floor
        soft_max_weight=0.08,  # Soft 8% threshold (penalty kicks in above this)
        hard_max_weight=0.15,  # HARD 15% ceiling

        # Regularization penalties
        l2_gamma=0.1,  # Diversification pressure
        concentration_gamma=0.5,  # Soft max penalty

        # Other params
        risk_free_rate=0.02,
        lookback_days=504,
        frequency="daily",
        trading_days=252,
    )

    return allocate(
        tickers=tickers,
        config=config,
        strategy=strategy,
        risk_aversion=5.0,
        target_volatility=0.12,
    )


if __name__ == "__main__":
    final_output = run(
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "F", "AAL", "IBM", "AGG", "BND"],
        initial_portfolio_value=100_000,
        equity_weight_target=0.7,
        bond_weight_target=0.3,
        strategy="min_vol"
    )

    print(final_output.model_dump_json(indent=4))
    # from app.db.core.db_config import MarketSession
    # from app.db.core.models.market_data_models import Ticker
    # from app.utils.serialize_output import serialize_sqlalchemy_obj
    # m_session = MarketSession()

    # results = m_session.query(Ticker.industry, Ticker.sub_industry).filter(Ticker.sector == "etf").distinct().all()
    
    # industries = sorted(set(r.industry for r in results if r.industry))
    # sub_industries = sorted(set(r.sub_industry for r in results if r.sub_industry))
    
    # print("Industries:", industries)
    # print("Sub-industries:", sub_industries)
    # m_session.close()