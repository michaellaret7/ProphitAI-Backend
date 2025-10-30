import pandas as pd
import yaml
from app.core.calculations.portfolio.correlation import CorrelationAnalysis
from app.core.calculations.portfolio.utils import prepare_portfolio_data
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.core.config import DEFAULT_LOOKBACK_SHORT
from app.models.portfolio_models import PortfolioInput
from app.core.calculations.core.helpers import build_returns_df_from_price_map
from app.utils.tool_validator import ToolValidator

def run_pairwise_correlation_analysis(portfolio_dict: PortfolioInput | dict) -> str:
    """
    Run pairwise correlation analysis on portfolio returns data and return results in YAML format.

    Args:
        portfolio_dict: Portfolio dictionary with allocations

    Returns:
        YAML formatted string containing pairwise correlations
    """
    # Validate inputs
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)

    if not v.is_valid():
        return v.error_response()

    # Get validated/normalized values
    portfolio_dict = v.get('portfolio_dict')

    try:

        # Use utility to get portfolio data
        weights, price_data, dividend_data = prepare_portfolio_data(
            portfolio=portfolio_dict,
            lookback_days=DEFAULT_LOOKBACK_SHORT,
            include_dividends=False
        )

        if not price_data:
            return yaml.dump({"success": False, "error": "No price data available for portfolio tickers"}, default_flow_style=False)

        # Calculate returns without dropping rows globally; let correlation handle pairwise NaNs
        returns_df = build_returns_df_from_price_map(price_data, drop_rows='none', include_dividends=False)

        if returns_df.empty:
            return yaml.dump({"success": False, "error": "No valid returns data available"}, default_flow_style=False)

        # Use the pairwise correlation function from calculations folder
        pairwise_df = CorrelationAnalysis.pairwise_correlation_analysis(returns_df)

        # Convert to dictionary format for YAML
        if pairwise_df.empty:
            return yaml.dump({"success": False, "error": "Failed to calculate pairwise correlations"}, default_flow_style=False)

        # Round correlation values to 3 decimal places
        pairwise_df['correlation'] = pairwise_df['correlation'].round(3)
        pairwise_df['abs_correlation'] = pairwise_df['abs_correlation'].round(3)

        # Convert DataFrame to list of dictionaries
        correlations_list = pairwise_df.to_dict('records')

        # Create structured output
        output = {
            "summary": {
                "total_pairs": len(correlations_list),
                "avg_correlation": round(float(pairwise_df['correlation'].mean()), 3) if not pairwise_df.empty else None,
                "avg_abs_correlation": round(float(pairwise_df['abs_correlation'].mean()), 3) if not pairwise_df.empty else None,
                "max_correlation": round(float(pairwise_df['correlation'].max()), 3) if not pairwise_df.empty else None,
                "min_correlation": round(float(pairwise_df['correlation'].min()), 3) if not pairwise_df.empty else None,
            }
        }

        # Return as YAML string
        return yaml.dump({"success": True, "data": output}, default_flow_style=False, sort_keys=False)

    except Exception as e:
        return yaml.dump({"success": False, "error": f"Failed to run pairwise correlation analysis: {str(e)}"}, default_flow_style=False)


# Tool Schema Constants
PAIRWISE_CORR_ANALYSIS_DESCRIPTION = (
    "Run pairwise correlation analysis on portfolio returns data and return results in YAML format. "
    "Returns summary statistics including total pairs, average correlation, max/min correlations, and detailed pairwise correlations. "
    "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings. "
    "Example: run_pairwise_correlation_analysis(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'TSLA': {'allocation': 0.5, 'position': 'short'}})"
)

PAIRWISE_CORR_ANALYSIS_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": {
            "type": "object",
            "description": (
                "**MANDATORY - DO NOT OMIT THIS PARAMETER.** "
                "Complete portfolio with ALL holdings. "
                "Keys = ticker symbols (e.g., 'AAPL'). "
                "Values = objects with 'allocation' (decimal 0-1) and 'position' ('long'/'short'). "
                "You MUST include this parameter with all portfolio tickers."
                "\n\n"
                """Example of CORRECT function call:
                run_pairwise_correlation_analysis(
                    portfolio_dict={
                        "AAPL": {"allocation": 0.125, "position": "long"},
                        "MSFT": {"allocation": 0.125, "position": "long"},
                        "AMZN": {"allocation": 0.125, "position": "long"},
                        "TSLA": {"allocation": 0.125, "position": "short"},
                        "META": {"allocation": 0.125, "position": "short"},
                        "SPY": {"allocation": 0.125, "position": "long"},
                        "QQQ": {"allocation": 0.125, "position": "long"},
                        "IWM": {"allocation": 0.125, "position": "short"}
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
        },
    },
    "required": ["portfolio_dict"],
    "additionalProperties": False
}

PAIRWISE_CORR_ANALYSIS_TOOL = {
    "name": "portfolio_pairwise_correlation_analysis",
    "description": PAIRWISE_CORR_ANALYSIS_DESCRIPTION,
    "parameters": PAIRWISE_CORR_ANALYSIS_PARAMETERS,
    "function": run_pairwise_correlation_analysis,
}
