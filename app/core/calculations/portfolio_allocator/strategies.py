"""Optimization Strategies Module.

Defines and executes portfolio optimization strategies (max_sharpe, min_vol, etc.).
"""

from typing import Callable, Dict, List, Tuple

import pandas as pd
from pypfopt import EfficientFrontier

from app.core.calculations.portfolio_allocator.models import OptimizationStrategy
from app.core.calculations.portfolio_allocator.constraints import ConstraintBuilder


# Type alias for strategy functions
StrategyFunc = Callable[
    [EfficientFrontier, float, float],  # ef, risk_free_rate, target_param
    None,  # Modifies ef in place
]


def optimize_min_vol(ef: EfficientFrontier, risk_free_rate: float, **kwargs) -> None:
    """Minimize portfolio volatility."""
    ef.min_volatility()

def optimize_max_sharpe(ef: EfficientFrontier, risk_free_rate: float, **kwargs) -> None:
    """Maximize Sharpe ratio."""
    ef.max_sharpe(risk_free_rate=risk_free_rate)

def optimize_max_utility(
    ef: EfficientFrontier,
    risk_free_rate: float,
    risk_aversion: float = 5.0,
    **kwargs,
) -> None:
    """Maximize quadratic utility with given risk aversion."""
    ef.max_quadratic_utility(risk_aversion=risk_aversion)

def optimize_efficient_risk(
    ef: EfficientFrontier,
    risk_free_rate: float,
    target_volatility: float = 0.20,
    **kwargs,
) -> None:
    """Maximize return for a given target volatility."""
    ef.efficient_risk(target_volatility=target_volatility)

def optimize_efficient_return(
    ef: EfficientFrontier,
    risk_free_rate: float,
    target_return: float = 0.15,
    **kwargs,
) -> None:
    """Minimize volatility for a given target return."""
    ef.efficient_return(target_return=target_return)

# Strategy registry mapping strategy names to their functions
STRATEGIES: Dict[str, StrategyFunc] = {
    OptimizationStrategy.MIN_VOL.value: optimize_min_vol,
    OptimizationStrategy.MAX_SHARPE.value: optimize_max_sharpe,
    OptimizationStrategy.MAX_UTILITY.value: optimize_max_utility,
    OptimizationStrategy.EFFICIENT_RISK.value: optimize_efficient_risk,
    OptimizationStrategy.EFFICIENT_RETURN.value: optimize_efficient_return,
}


def run_strategy(
    constraint_builder: ConstraintBuilder,
    mu: pd.Series,
    cov_matrix: pd.DataFrame,
    tickers: List[str],
    strategy: str,
    risk_free_rate: float,
    **strategy_params,
) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
    """Run a specific optimization strategy.

    Returns:
        Tuple of (weights_dict, performance_tuple)
        where performance_tuple is (expected_return, volatility, sharpe_ratio).

    Raises:
        ValueError: If strategy is unknown.
    """
    if strategy not in STRATEGIES:
        raise ValueError(
            f"Unknown optimization strategy: {strategy}. "
            f"Available: {list(STRATEGIES.keys())}"
        )

    # Build EfficientFrontier with constraints
    ef = constraint_builder.build_ef(mu, cov_matrix, tickers)

    # Execute strategy
    strategy_func = STRATEGIES[strategy]
    strategy_func(ef, risk_free_rate, **strategy_params)

    # Finalize and validate weights
    weights = constraint_builder.finalize_weights(ef, tickers)

    # Get performance metrics
    # Reason: Only pass risk_free_rate for max_sharpe (matches pypfopt behavior)
    if strategy == OptimizationStrategy.MAX_SHARPE.value:
        perf = ef.portfolio_performance(risk_free_rate=risk_free_rate, verbose=False)
    else:
        perf = ef.portfolio_performance(verbose=False)

    return weights, perf
