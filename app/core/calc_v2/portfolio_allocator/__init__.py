"""Portfolio Allocation Module.

Provides optimization-based portfolio allocation with support for:
- Multiple asset classes (equity, fixed income, commodities)
- Configurable constraints (min/max weights, bucket targets)
- Multiple optimization strategies (max_sharpe, min_vol, max_utility, etc.)
- Auto-detection and adjustment of asset class weights

Usage:
    from app.core.calc_v2.portfolio_allocator import run, allocate, PortfolioAllocator

    # Simple usage with defaults
    result = run(
        tickers=["AAPL", "MSFT", "GOOGL", "BND"],
        strategy="max_sharpe",
    )

    # Advanced usage with custom config
    config = OptimizerConfig(
        equity_weight_target=0.60,
        bond_weight_target=0.30,
        commodity_weight_target=0.10,
        min_weight=0.02,
    )
    result = allocate(tickers, config, strategy="min_vol")
"""

from app.core.calc_v2.portfolio_allocator.models import (
    OptimizerConfig,
    OptimizationStrategy,
    StrategyLiteral,
    Allocation,
    PortfolioPerformance,
    AllocationResult,
    ClassifiedTickers,
    validate_weights,
    WEIGHT_TOLERANCE,
)
from app.core.calc_v2.portfolio_allocator.allocator import PortfolioAllocator
from app.core.calc_v2.portfolio_allocator.service import allocate, run
from app.core.calc_v2.portfolio_allocator.classifier import (
    classify_tickers,
    build_classified_tickers,
    auto_adjust_bucket_targets,
)
from app.core.calc_v2.portfolio_allocator.strategies import STRATEGIES, run_strategy
from app.core.calc_v2.portfolio_allocator.constraints import ConstraintBuilder

__all__ = [
    # Main API
    "allocate",
    "run",
    "PortfolioAllocator",
    # Models
    "OptimizerConfig",
    "OptimizationStrategy",
    "StrategyLiteral",
    "Allocation",
    "PortfolioPerformance",
    "AllocationResult",
    "ClassifiedTickers",
    # Utilities
    "classify_tickers",
    "build_classified_tickers",
    "auto_adjust_bucket_targets",
    "validate_weights",
    "WEIGHT_TOLERANCE",
    # Strategies
    "STRATEGIES",
    "run_strategy",
    # Constraints
    "ConstraintBuilder",
]
