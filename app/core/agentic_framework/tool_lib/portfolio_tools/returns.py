import yaml
from typing import Optional
from datetime import datetime
from app.core.calculations.portfolio.utils import get_portfolio_returns
from app.core.calculations.returns.calculator import ReturnsCalculator
import numpy as np
from app.models.portfolio_models import PortfolioInput
from app.utils.gpt_parser import canonical_portfolio
from app.utils.decorators.tool_validation import log_simulation_data_range, validate_portfolio_dict, validate_required_args

@validate_required_args('portfolio_dict')
@validate_portfolio_dict()
@log_simulation_data_range()
def calculate_portfolio_returns_metrics(portfolio_dict: PortfolioInput | dict, lookback_days=252, _simulation_date: Optional[datetime] = None) -> str:
    """Calculate and display simple portfolio metrics.

    Args:
        portfolio_dict: Portfolio holdings
        lookback_days: Historical lookback period
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
        dict: Contains annualized returns, volatility, and weekly cumulative returns
    """
    try:
        portfolio_dict = canonical_portfolio(portfolio_dict)

        # Get price-only returns
        portfolio_price_returns, _ = get_portfolio_returns(
            portfolio=portfolio_dict,
            lookback_days=lookback_days,
            use_total_returns=False,
            dropna=True,
            _simulation_date=_simulation_date
        )

        # Get total returns
        portfolio_total_returns, _ = get_portfolio_returns(
            portfolio=portfolio_dict,
            lookback_days=lookback_days,
            use_total_returns=True,
            dropna=True,
            _simulation_date=_simulation_date
        )


        # Calculate metrics
        ann_price_return = ReturnsCalculator.annualized_return(portfolio_price_returns, 252)
        ann_total_return = ReturnsCalculator.annualized_return(portfolio_total_returns, 252)
        ann_volatility = float(portfolio_total_returns.std() * np.sqrt(252))

        # Calculate weekly cumulative returns and convert to rounded dict
        weekly_cumulative = (1 + portfolio_total_returns).resample('W').prod() - 1
        weekly_returns = {ts.strftime('%Y-%m-%d'): round(val, 4) for ts, val in weekly_cumulative.items()}

        # Calculate cumulative return over period
        total_cumulative = float((1 + portfolio_total_returns).prod() - 1)

        return yaml.dump({"success": True, "data": {
            "ann_price_return": round(ann_price_return, 4),
            "ann_total_return": round(ann_total_return, 4),
            "ann_volatility": round(ann_volatility, 4),
            "weekly_returns": weekly_returns,
            "cumulative_return": round(total_cumulative, 4)
        }}, default_flow_style=False)
    except Exception as e:
        return yaml.dump({"success": False, "error": str(e)}, default_flow_style=False)


# Tool Schema Constants
CALCULATE_PORTFOLIO_RETURNS_METRICS_DESCRIPTION = (
    "Calculate and display simple portfolio return metrics including annualized returns, volatility, and weekly cumulative returns. "
    "Returns both price-only and total returns (with dividends) for comparison. "
    "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings. "
    "Example: calculate_portfolio_returns_metrics(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'KO': {'allocation': 0.5, 'position': 'long'}})"
)

CALCULATE_PORTFOLIO_RETURNS_METRICS_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": {
            "type": "object",
            "description": (
                "**MANDATORY - DO NOT OMIT THIS PARAMETER.** "
                "Complete portfolio with ALL holdings. "
                "Keys = ticker symbols (e.g., 'AAPL'). "
                "Values = objects with 'allocation' (decimal 0-1) and 'position' ('long'/'short'). "
                "You MUST include this parameter with all portfolio tickers. "
                "Uses 1-year lookback (252 days) by default."
                "\n\n"
                """Example of CORRECT function call:
                calculate_portfolio_returns_metrics(
                    portfolio_dict={
                        "AAPL": {"allocation": 0.125, "position": "long"},
                        "MSFT": {"allocation": 0.125, "position": "long"},
                        "AMZN": {"allocation": 0.125, "position": "long"},
                        "TSLA": {"allocation": 0.125, "position": "long"},
                        "META": {"allocation": 0.125, "position": "long"},
                        "SPY": {"allocation": 0.125, "position": "long"},
                        "QQQ": {"allocation": 0.125, "position": "long"},
                        "IWM": {"allocation": 0.125, "position": "long"}
                    }
                )"""
            ),
            "patternProperties": {
                "^[A-Z]{1,5}$": {
                    "type": "object",
                    "properties": {
                        "allocation": {
                            "type": "number",
                            "description": "Weight as decimal (e.g., 0.125 for 12.5%)",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "position": {
                            "type": "string",
                            "description": "Must be 'long' or 'short'",
                            "enum": ["long", "short"]
                        }
                    },
                    "required": ["allocation", "position"],
                    "additionalProperties": False
                }
            },
            "minProperties": 1,
            "additionalProperties": False
        }
    },
    "required": ["portfolio_dict"],
    "additionalProperties": False
}

CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL = {
    "name": "calculate_portfolio_returns_metrics",
    "description": CALCULATE_PORTFOLIO_RETURNS_METRICS_DESCRIPTION,
    "parameters": CALCULATE_PORTFOLIO_RETURNS_METRICS_PARAMETERS,
    "function": calculate_portfolio_returns_metrics,
}

if __name__ == "__main__":
    print(calculate_portfolio_returns_metrics(portfolio_dict={'AAPL': {'allocation': 0.125, 'position': 'long'}, 'MSFT': {'allocation': 0.125, 'position': 'long'}, 'AMZN': {'allocation': 0.125, 'position': 'long'}, 'TSLA': {'allocation': 0.125, 'position': 'long'}, 'META': {'allocation': 0.125, 'position': 'long'}, 'SPY': {'allocation': 0.125, 'position': 'long'}, 'QQQ': {'allocation': 0.125, 'position': 'long'}, 'IWM': {'allocation': 0.125, 'position': 'long'}}))