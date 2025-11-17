from typing import Optional
from datetime import datetime
import pandas as pd
from app.core.calculations.portfolio.utils import get_portfolio_returns
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.core.config import DEFAULT_LOOKBACK_LONG
import numpy as np
from app.models.portfolio_models import PortfolioInput
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.tool_validator import ToolValidator
from app.core.agentic_framework.tool_lib.common.schemas import PORTFOLIO_DICT_SCHEMA
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response

@log_simulation_data_range()
def calculate_portfolio_returns_metrics(portfolio_dict: PortfolioInput | dict, lookback_days=DEFAULT_LOOKBACK_LONG, _simulation_date: Optional[datetime] = None) -> str:
    """Calculate and display simple portfolio metrics.

    Args:
        portfolio_dict: Portfolio holdings
        lookback_days: Historical lookback period
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
        dict: Contains annualized returns, volatility, and weekly cumulative returns
    """
    # Validate inputs
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)
    v.optional_numeric('lookback_days', lookback_days, default=DEFAULT_LOOKBACK_LONG, min_val=1, positive_only=True)

    if not v.is_valid():
        return v.error_response()

    # Get validated/normalized values
    portfolio_dict = v.get('portfolio_dict')
    lookback_days = v.get('lookback_days')

    try:

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

        # Log actual data range
        if isinstance(portfolio_total_returns, pd.Series) and len(portfolio_total_returns) > 0:
            if hasattr(portfolio_total_returns, 'index') and isinstance(portfolio_total_returns.index, pd.DatetimeIndex):
                start_date = portfolio_total_returns.index.min().date()
                end_date = portfolio_total_returns.index.max().date()
                count = len(portfolio_total_returns)
                print(f"  📅 ACTUAL DATA USED:")
                # Check if data exceeds simulation cutoff
                if _simulation_date:
                    cutoff_ok = portfolio_total_returns.index.max() <= _simulation_date
                    cutoff_status = "✅" if cutoff_ok else "⚠️ EXCEEDS CUTOFF"
                    print(f"    • portfolio_returns: {start_date} → {end_date} ({count} points) {cutoff_status}")
                else:
                    print(f"    • portfolio_returns: {start_date} → {end_date} ({count} points)")

        # Calculate metrics
        ann_price_return = ReturnsCalculator.annualized_return(portfolio_price_returns, 252)
        ann_total_return = ReturnsCalculator.annualized_return(portfolio_total_returns, 252)
        ann_volatility = float(portfolio_total_returns.std() * np.sqrt(252))

        # Calculate weekly cumulative returns and convert to rounded dict
        weekly_cumulative = (1 + portfolio_total_returns).resample('W').prod() - 1
        weekly_returns = {ts.strftime('%Y-%m-%d'): round(val, 4) for ts, val in weekly_cumulative.items()}

        # Calculate cumulative return over period
        total_cumulative = float((1 + portfolio_total_returns).prod() - 1)

        return success_response({
            "ann_price_return": round(ann_price_return, 4),
            "ann_total_return": round(ann_total_return, 4),
            "ann_volatility": round(ann_volatility, 4),
            "weekly_returns": weekly_returns,
            "cumulative_return": round(total_cumulative, 4)
        })
    except Exception as e:
        return error_response(e)


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
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA
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