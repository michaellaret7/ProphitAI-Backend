"""Portfolio allocation optimization tool.

Provides a tool for constructing optimized multi-asset portfolios with
asset class bucketing, hybrid constraints, and multiple optimization strategies.
"""

from typing import Annotated, Literal

from pypfopt.exceptions import OptimizationError

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response


# ================================
# --> Helper funcs
# ================================


def _format_allocation_result(result) -> dict:
    """Convert AllocationResult into a clean dict for agent consumption."""
    allocations = sorted(result.allocations, key=lambda a: a.weight, reverse=True)

    return {
        "strategy": result.strategy,
        "performance": {
            "expected_return": result.performance.expected_return,
            "volatility": result.performance.volatility,
            "sharpe_ratio": result.performance.sharpe_ratio,
        },
        "allocations": [
            {
                "ticker": a.ticker,
                "weight": round(a.weight, 4),
                "weight_pct": f"{a.weight:.2%}",
                "num_shares": a.num_shares,
            }
            for a in allocations
        ],
        "total_positions": len(allocations),
    }


# ================================
# --> Tools
# ================================

@agent_tool(name="portfolio_allocator")
def portfolio_allocator(
    tickers: list[str],
    strategy: Literal[
        "max_sharpe", "min_vol", "max_utility", "efficient_risk", "efficient_return"
    ] = "max_sharpe",
    initial_portfolio_value: Annotated[float, Param(min_val=1000, max_val=100_000_000)] = 10_000,
    equity_weight_target: Annotated[float, Param(min_val=0.0, max_val=1.0)] = 0.60,
    bond_weight_target: Annotated[float, Param(min_val=0.0, max_val=1.0)] = 0.40,
    commodity_weight_target: Annotated[float, Param(min_val=0.0, max_val=1.0)] = 0.0,
    crypto_weight_target: Annotated[float, Param(min_val=0.0, max_val=1.0)] = 0.0,
    risk_aversion: Annotated[float, Param(min_val=0.5, max_val=20.0)] = 5.0,
    target_volatility: Annotated[float, Param(min_val=0.01, max_val=0.50)] = 0.12,
    target_return: Annotated[float, Param(min_val=0.01, max_val=0.50)] = 0.15,
) -> str:
    """Optimize a multi-asset portfolio and return ticker weights, expected performance, and share counts.

Uses mean-variance optimization with asset class bucketing (equity, bond, commodity, crypto),
hybrid hard/soft constraints, and L2 regularization for diversification. Tickers are auto-classified
into asset classes, and bucket targets are auto-adjusted when not all asset classes are present.

**WHEN TO USE:**
- Constructing a new portfolio from a list of tickers
- Rebalancing an existing portfolio with updated allocation targets
- Comparing different optimization strategies (max Sharpe vs min volatility, etc.)
- Generating share counts for a given portfolio value

**IMPORTANT:**
- Asset class targets should sum to 1.0 (auto-adjusted if missing asset classes)
- Tickers are auto-classified: ETFs with fixed_income industry -> bonds,
  commodity industry -> commodities, cryptocurrency industry -> crypto, else equity
- Every ticker gets at least 1% weight (hard floor), max 15% (hard ceiling)
- Strategy-specific params only apply to their strategy:
  risk_aversion -> max_utility only, target_volatility -> efficient_risk only,
  target_return -> efficient_return only

    Args:
        tickers: List of ticker symbols to include in the portfolio
            (e.g., ['AAPL', 'MSFT', 'GOOGL', 'GLD', 'AGG'])
        strategy: Optimization strategy to use.
            max_sharpe = maximize risk-adjusted return (default, best general purpose).
            min_vol = minimize portfolio volatility (conservative).
            max_utility = maximize return - 0.5 * risk_aversion * variance (risk-preference).
            efficient_risk = maximize return for a target volatility level.
            efficient_return = minimize volatility for a target return level.
        initial_portfolio_value: Dollar amount to invest. Used to calculate share counts.
        equity_weight_target: Target allocation to equities (0.0 to 1.0)
        bond_weight_target: Target allocation to bonds/fixed income (0.0 to 1.0)
        commodity_weight_target: Target allocation to commodities (0.0 to 1.0)
        crypto_weight_target: Target allocation to crypto (0.0 to 1.0)
        risk_aversion: Risk aversion coefficient for max_utility strategy.
            Higher = more conservative. 1-3 aggressive, 5 moderate, 10+ conservative.
        target_volatility: Target annualized volatility for efficient_risk strategy.
            0.10 = 10% vol. Typical equity portfolio 0.12-0.20.
        target_return: Target annualized return for efficient_return strategy.
            0.10 = 10% return. Must be achievable given the asset universe.

    Returns:
        YAML-formatted result with:
        - strategy: which optimization strategy was used
        - performance: expected_return, volatility, sharpe_ratio
        - allocations: list of {ticker, weight, weight_pct, num_shares} sorted by weight desc
        - total_positions: number of positions in the portfolio

    Interpretation Guide:
        expected_return: Forward-looking annualized return estimate based on historical data.
        volatility: Annualized portfolio standard deviation. Lower = less risk.
        sharpe_ratio: (return - risk_free) / volatility. >1.0 is good, >2.0 is excellent.
        weight: Decimal allocation (0.08 = 8% of portfolio).
        num_shares: Fractional share count at current market prices.

    Examples:
        portfolio_allocator(tickers=["AAPL", "MSFT", "GOOGL", "GLD", "AGG"])
        >>> allocates using max_sharpe with default 60/40 equity/bond targets

        portfolio_allocator(
            tickers=["AAPL", "NVDA", "TSLA", "GLD", "SLV", "AGG", "TLT"],
            strategy="min_vol",
            initial_portfolio_value=100000,
            equity_weight_target=0.50,
            bond_weight_target=0.20,
            commodity_weight_target=0.30,
        )
        >>> minimum volatility portfolio with custom asset class targets

    Raises:
        ValueError: If tickers are invalid, prices unavailable, or optimization fails
    """
    try:
        if not tickers or len(tickers) < 2:
            return error_response("At least 2 tickers are required for portfolio optimization")

        tickers = [t.upper().strip() for t in tickers]

        from app.core.calc_v2.portfolio_allocator.models import OptimizerConfig
        from app.core.calc_v2.portfolio_allocator.service import allocate

        config = OptimizerConfig(
            equity_weight_target=equity_weight_target,
            bond_weight_target=bond_weight_target,
            commodity_weight_target=commodity_weight_target,
            crypto_weight_target=crypto_weight_target,
            initial_portfolio_value=initial_portfolio_value,
        )

        result = allocate(
            tickers=tickers,
            config=config,
            strategy=strategy,
            risk_aversion=risk_aversion,
            target_volatility=target_volatility,
            target_return=target_return,
        )

        return success_response({
            "initial_portfolio_value": initial_portfolio_value,
            **_format_allocation_result(result),
        })

    except OptimizationError:
        strategy_hints = {
            "max_sharpe": "Try adding more tickers or relaxing asset class targets.",
            "min_vol": "Try adding more tickers or relaxing asset class targets.",
            "max_utility": "Try increasing risk_aversion or adding more tickers.",
            "efficient_risk": "Try increasing target_volatility or using max_sharpe instead.",
            "efficient_return": "Try lowering target_return or using min_vol instead.",
        }
        hint = strategy_hints.get(strategy, "Try a different strategy or adjust constraints.")
        return error_response(
            f"'{strategy}' optimization infeasible: the solver could not find a valid "
            f"portfolio with the current tickers and constraints. {hint}"
        )
    except Exception as e:
        return error_response(f"Portfolio allocation failed: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(portfolio_allocator(
        tickers=["AAPL", "MU", "GOOGL", "AMZN", "TSLA", "NVDA", "META",
                 "GLD", "SLV", "DBA", "AGG", "BND", "TLT"],
        strategy="max_sharpe",
        initial_portfolio_value=100_000,
        equity_weight_target=0.55,
        bond_weight_target=0.15,
        commodity_weight_target=0.30,
    ))
