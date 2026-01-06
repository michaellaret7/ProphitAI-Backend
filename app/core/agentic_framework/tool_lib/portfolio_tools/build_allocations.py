from typing import List, Dict
from app.core.calculations.portfolio.allocator import run, StrategyLiteral
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response


def build_allocations(
    tickers: List[str],
    equity_weight_target: float = 0.60,
    bond_weight_target: float = 0.40,
    commodity_weight_target: float = 0.0,
    strategy: StrategyLiteral = "max_sharpe",
    initial_portfolio_value: float = 100_000,
) -> Dict[str, float]:

    if not tickers:
        return error_response("Tickers list is empty")

    try:
        allocations = run(
            tickers=tickers,
            equity_weight_target=equity_weight_target,
            bond_weight_target=bond_weight_target,
            commodity_weight_target=commodity_weight_target,
            initial_portfolio_value=initial_portfolio_value,
            strategy=strategy,
        )
        return success_response(allocations)
    except Exception as e:
        return error_response(f"Error building allocations: {e}")

# Tool Schema Constants
BUILD_PORTFOLIO_DESCRIPTION = (
    "Build optimal portfolio allocations using mean-variance optimization. "
    "Given a list of tickers, this tool calculates optimal weights using the specified strategy. "
    "\n\n**Strategies:**"
    "\n  • 'max_sharpe' (default): Maximize risk-adjusted returns (Sharpe ratio)"
    "\n  • 'min_vol': Minimize portfolio volatility (most conservative)"
    "\n  • 'max_utility': Maximize expected utility with risk aversion"
    "\n  • 'efficient_risk': Target specific risk level on efficient frontier"
    "\n  • 'efficient_return': Target specific return level on efficient frontier"
    "\n\n**Parameters:**"
    "\n  • tickers: List of stock/ETF tickers to include in portfolio"
    "\n  • equity_weight_target: Target allocation to equities (default 0.60 = 60%)"
    "\n  • bond_weight_target: Target allocation to bonds (default 0.40 = 40%)"
    "\n  • commodity_weight_target: Target allocation to commodities (default 0.0 = 0%)"
    "\n  • strategy: Optimization strategy to use"
    "\n  • initial_portfolio_value: Starting portfolio value in USD (default $100,000)"
    "\n\n**Output:**"
    "\n  Returns optimized allocation weights for each ticker."
)

BUILD_PORTFOLIO_PARAMETERS = {
    "type": "object",
    "properties": {
        "tickers": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of stock/ETF tickers to include in the portfolio optimization."
        },
        "equity_weight_target": {
            "type": "number",
            "description": "Target weight for equity allocation (0.0 to 1.0). Default is 0.60 (60%).",
            "default": 0.60
        },
        "bond_weight_target": {
            "type": "number",
            "description": "Target weight for bond allocation (0.0 to 1.0). Default is 0.40 (40%).",
            "default": 0.40
        },
        "commodity_weight_target": {
            "type": "number",
            "description": "Target weight for commodity allocation (0.0 to 1.0). Default is 0.0 (0%).",
            "default": 0.0
        },
        "strategy": {
            "type": "string",
            "description": "Optimization strategy: 'max_sharpe', 'min_vol', 'max_utility', 'efficient_risk', or 'efficient_return'.",
            "enum": ["max_sharpe", "min_vol", "max_utility", "efficient_risk", "efficient_return"],
            "default": "max_sharpe"
        },
        "initial_portfolio_value": {
            "type": "number",
            "description": "Initial portfolio value in USD. Default is $100,000.",
            "default": 100000
        }
    },
    "required": ["tickers"],
    "additionalProperties": False
}

BUILD_PORTFOLIO_TOOL = {
    "name": "build_portfolio_allocations",
    "description": BUILD_PORTFOLIO_DESCRIPTION,
    "parameters": BUILD_PORTFOLIO_PARAMETERS,
    "function": build_allocations,
}


