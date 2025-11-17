import pandas as pd
from datetime import datetime
from typing import Optional
from app.core.calculations.portfolio.correlation import CorrelationAnalysis
from app.core.calculations.portfolio.utils import prepare_portfolio_data
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.core.config import DEFAULT_LOOKBACK_SHORT
from app.models.portfolio_models import PortfolioInput
from app.core.calculations.core.helpers import build_returns_df_from_price_map
from app.utils.tool_validator import ToolValidator
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.core.agentic_framework.tool_lib.common.schemas import PORTFOLIO_DICT_SCHEMA
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response

@log_simulation_data_range()
def run_pairwise_correlation_analysis(
    portfolio_dict: PortfolioInput | dict,
    *,
    _simulation_date: Optional[datetime] = None
) -> str:
    """
    Run pairwise correlation analysis on portfolio returns data and return results in YAML format.

    Args:
        portfolio_dict: Portfolio dictionary with allocations
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents.
                         If provided, uses this as cutoff date instead of current time.

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
            include_dividends=False,
            _simulation_date=_simulation_date
        )

        if not price_data:
            return error_response("No price data available for portfolio tickers")

        # Calculate returns without dropping rows globally; let correlation handle pairwise NaNs
        returns_df = build_returns_df_from_price_map(price_data, drop_rows='none', include_dividends=False)

        # Log actual data range (summary)
        if isinstance(returns_df, pd.DataFrame) and not returns_df.empty:
            if hasattr(returns_df, 'index') and isinstance(returns_df.index, pd.DatetimeIndex):
                start_date = returns_df.index.min().date()
                end_date = returns_df.index.max().date()
                count = len(returns_df)
                print(f"  📅 ACTUAL DATA USED:")
                # Check if data exceeds simulation cutoff
                if _simulation_date:
                    cutoff_ok = returns_df.index.max() <= _simulation_date
                    cutoff_status = "✅" if cutoff_ok else "⚠️ EXCEEDS CUTOFF"
                    print(f"    • correlation_data: {start_date} → {end_date} ({count} points) {cutoff_status}")
                else:
                    print(f"    • correlation_data: {start_date} → {end_date} ({count} points)")

        if returns_df.empty:
            return error_response("No valid returns data available")

        # Use the pairwise correlation function from calculations folder
        pairwise_df = CorrelationAnalysis.pairwise_correlation_analysis(returns_df)

        # Convert to dictionary format for YAML
        if pairwise_df.empty:
            return error_response("Failed to calculate pairwise correlations")

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
        return success_response(output)

    except Exception as e:
        return error_response(f"Failed to run pairwise correlation analysis: {str(e)}")


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
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA,
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
