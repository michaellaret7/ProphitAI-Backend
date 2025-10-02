import yaml
from typing import Optional
from datetime import datetime
from app.core.calculations.portfolio.utils import prepare_portfolio_data
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.portfolio.correlation import CorrelationAnalysis
from app.models.portfolio_models import PortfolioInput
import pandas as pd
from app.utils.gpt_parser import canonical_portfolio
from app.core.calculations.core.helpers import build_returns_df_from_price_map
from app.utils.decorators.tool_validation import log_simulation_data_range, validate_required_args, validate_portfolio_dict

@validate_required_args('portfolio_dict')
@validate_portfolio_dict()
@log_simulation_data_range()
def correlation_matrix(portfolio_dict: PortfolioInput | dict, _simulation_date: Optional[datetime] = None) -> str:
    """
    Calculate pairwise correlations and return as records for easy LLM consumption.

    Args:
        portfolio_dict: Portfolio holdings
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Output shape:
    {
      "correlations": [
        {"ticker1": "T1", "ticker2": "T2", "correlation": 0.123}
      ]
    }
    """
    try:
        if not portfolio_dict:
            return yaml.dump({"success": True, "data": {"correlations": []}}, default_flow_style=False)

        try:
            portfolio_dict = canonical_portfolio(portfolio_dict)
        except ValueError:
            return yaml.dump({"success": True, "data": {"correlations": []}}, default_flow_style=False)

        # Use utility to get portfolio data
        weights, price_data, dividend_data = prepare_portfolio_data(
            portfolio=portfolio_dict,
            lookback_days=252,
            include_dividends=False,
            _simulation_date=_simulation_date
        )

        if not price_data:
            return yaml.dump({"success": True, "data": {"correlations": []}}, default_flow_style=False)

        # Calculate returns without dropping rows globally; let correlation handle pairwise NaNs
        returns_df = build_returns_df_from_price_map(price_data, drop_rows='none', include_dividends=False)

        if returns_df.empty:
            return yaml.dump({"success": True, "data": {"correlations": []}}, default_flow_style=False)

        # Compute correlation matrix and round
        corr_df = CorrelationAnalysis.correlation_matrix(returns_df)
        if corr_df is None or corr_df.empty:
            return yaml.dump({"success": True, "data": {"correlations": []}}, default_flow_style=False)
        corr_df = corr_df.round(3)

        # Use the correlation matrix's own column order to avoid key-order drift
        ordered_tickers = [t for t in corr_df.columns if t in corr_df.index]

        # Build records for unique pairs (upper triangle, excluding diagonal)
        records = []
        for i, t1 in enumerate(ordered_tickers):
            for j in range(i + 1, len(ordered_tickers)):
                t2 = ordered_tickers[j]
                value = corr_df.loc[t1, t2]
                try:
                    value = float(value)
                except Exception:
                    pass
                records.append({
                    "pair": f"{t1} | {t2}",
                    "corr": value
                })

        return yaml.dump({"success": True, "data": {"correlations": records}}, default_flow_style=False)
    except Exception as e:
        return yaml.dump({"success": False, "error": str(e)}, default_flow_style=False)


# Tool Schema Constants
CORRELATION_MATRIX_DESCRIPTION = (
    "Calculate pairwise correlations using 252 trading days of price returns. "
    "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter and it must contain ALL portfolio holdings with their allocations and positions. "
    "Output shape: {'correlations': [{'pair': 'AAPL | MSFT', 'corr': 0.712}, ...]} (values rounded to 3 decimals). "
    "Example: correlation_matrix(portfolio_dict={'AAPL': {'allocation': 0.125, 'position': 'long'}, 'MSFT': {'allocation': 0.125, 'position': 'long'}})"
)

CORRELATION_MATRIX_PARAMETERS = {
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
                correlation_matrix(
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
        },
    },
    "required": ["portfolio_dict"],
    "additionalProperties": False
}

CORRELATION_MATRIX_TOOL = {
    "name": "calculate_portfolio_correlation_matrix",
    "description": CORRELATION_MATRIX_DESCRIPTION,
    "parameters": CORRELATION_MATRIX_PARAMETERS,
    "function": correlation_matrix,
}