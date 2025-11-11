import yaml
from typing import Optional
from datetime import datetime
import pandas as pd
import numpy as np
from app.core.calculations.portfolio.utils import get_portfolio_returns, get_benchmark_returns
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.core.config import DEFAULT_LOOKBACK_MEDIUM
from app.models.portfolio_models import PortfolioInput
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.tool_validator import ToolValidator

@log_simulation_data_range()
def calculate_portfolio_beta_vs_index(
    portfolio_dict: PortfolioInput | dict,
    lookback_days: int = DEFAULT_LOOKBACK_MEDIUM,
    _simulation_date: Optional[datetime] = None
) -> str:
    """
    Calculate CAPM beta for a long/short portfolio vs SPY index.

    Args:
        portfolio_dict: Dict of {ticker: {"allocation": float, "position": "long/short"}}
        lookback_days: Number of days of historical data to use (default: 504 days / 2 years)

    Returns:
        Portfolio beta vs SPY index
    """
    # Validate inputs
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)
    v.require_numeric('lookback_days', lookback_days, min_val=1, positive_only=True)

    if not v.is_valid():
        return v.error_response()

    # Get validated/normalized values
    portfolio_dict = v.get('portfolio_dict')
    lookback_days = v.get('lookback_days')

    try:

        # Use utility functions to get portfolio returns
        portfolio_returns, _ = get_portfolio_returns(
            portfolio=portfolio_dict,
            lookback_days=lookback_days + 50,  # Buffer for returns calc
            use_total_returns=False,  # Use price returns for beta calculation
            dropna=True,
            _simulation_date=_simulation_date
        )

        if portfolio_returns is None or portfolio_returns.empty:
            print(f"DEBUG: Portfolio returns is None or empty. Portfolio: {list(portfolio_dict.keys())}")
            return yaml.dump({"success": False, "error": "No portfolio returns data"}, default_flow_style=False)

        # Get index returns using utility function (hardcoded to SPY)
        index_returns = get_benchmark_returns(
            benchmark="SPY",
            lookback_days=lookback_days + 50,  # Buffer for returns calc
            use_total_returns=False,  # Use price returns for beta calculation
            _simulation_date=_simulation_date
        )

        if index_returns is None or index_returns.empty:
            print(f"DEBUG: Index returns is None or empty for SPY")
            return yaml.dump({"success": False, "error": "No index returns data for SPY"}, default_flow_style=False)

        # Calculate and return beta
        beta = RiskCalculator.beta(portfolio_returns, index_returns)

        # Check if beta is NaN or invalid
        if pd.isna(beta) or np.isnan(beta):
            print(f"DEBUG: Beta calculation resulted in NaN. Portfolio returns length: {len(portfolio_returns)}, Index returns length: {len(index_returns)}")
            return yaml.dump({"success": False, "error": "Beta calculation resulted in NaN"}, default_flow_style=False)

        return yaml.dump({"success": True, "data": {"beta": round(float(beta), 3)}}, default_flow_style=False)

    except Exception as e:
        print(f"DEBUG: Exception in beta calculation: {str(e)}")
        return yaml.dump({"success": False, "error": str(e)}, default_flow_style=False)

CALCULATE_PORTFOLIO_BETA_VS_INDEX_DESCRIPTION = (
    "Calculate CAPM beta for a long/short portfolio versus SPY benchmark (hardcoded) using 504 trading days (2 years) of historical data. "
    "Beta measures the portfolio's systematic risk relative to SPY. A beta of 1.0 means the portfolio moves with SPY, >1.0 means more volatile than SPY, <1.0 means less volatile. "
    "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings. "
    "Example: calculate_portfolio_beta_vs_index(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'MSFT': {'allocation': 0.5, 'position': 'long'}})"
)

CALCULATE_PORTFOLIO_BETA_VS_INDEX_PARAMETERS = {
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
                "Uses SPY benchmark by default."
                "\n\n"
                """Example of CORRECT function call:
                calculate_portfolio_beta_vs_index(
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

CALCULATE_PORTFOLIO_BETA_VS_INDEX_TOOL = {
    "name": "calculate_portfolio_beta_vs_index",
    "description": CALCULATE_PORTFOLIO_BETA_VS_INDEX_DESCRIPTION,
    "parameters": CALCULATE_PORTFOLIO_BETA_VS_INDEX_PARAMETERS,
    "function": calculate_portfolio_beta_vs_index,
}
