from typing import Optional
from datetime import datetime
from app.core.calculations.portfolio.utils import prepare_portfolio_data
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.core.config import DEFAULT_LOOKBACK_1Y
from app.models.portfolio_models import PortfolioInput
import pandas as pd
from app.utils.gpt_parser import canonical_portfolio
from app.core.calculations.core.helpers import build_returns_df_from_price_map
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.core.agentic_framework.tool_lib.common.schemas import PORTFOLIO_DICT_SCHEMA
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response

@log_simulation_data_range()
def calculate_covariance_matrix(portfolio_dict: PortfolioInput | dict = None, _simulation_date: Optional[datetime] = None, **kwargs) -> str:
    """
    Calculate covariance matrix for portfolio tickers using historical returns data.

    Parameters:
    - portfolio_dict: Portfolio configuration mapping ticker -> {allocation, position}

    Returns:
    - Dictionary with tickers list and covariance matrix as nested dictionary
    """
    try:
        if not portfolio_dict:
            return error_response("Portfolio dictionary is required")

        try:
            portfolio_dict = canonical_portfolio(portfolio_dict)
        except Exception as e:
            return error_response(e)

        # Get tickers and prepare portfolio data
        tickers = list(portfolio_dict.keys())

        # Get portfolio data using utility
        weights_dict, price_data, _ = prepare_portfolio_data(
            portfolio=portfolio_dict,
            lookback_days=DEFAULT_LOOKBACK_1Y,
            include_dividends=False,
            _simulation_date=_simulation_date
        )

        if not price_data:
            return error_response("No price data available for portfolio tickers")

        # Calculate returns and drop rows with any NaNs for stable covariance
        returns_df = build_returns_df_from_price_map(price_data, drop_rows='any', include_dividends=False)

        if returns_df.empty:
            return error_response("No valid returns data available")

        # Calculate covariance matrix using RiskCalculator
        cov_matrix = RiskCalculator.covariance_matrix(returns_df, annualize=False)

        if cov_matrix.empty:
            return error_response("Failed to calculate covariance matrix")

        # Convert to dictionary format
        tickers_list = list(cov_matrix.columns)
        cov_dict = {}

        for ticker in tickers_list:
            cov_dict[ticker] = {}
            for other_ticker in tickers_list:
                cov_dict[ticker][other_ticker] = round(float(cov_matrix.loc[ticker, other_ticker]), 6)

        result = {
            "tickers": tickers_list,
            "covariance_matrix": cov_dict
        }

        return success_response(result)

    except Exception as e:
        return error_response(f"Failed to calculate covariance matrix: {str(e)}")


# Tool Schema Constants
CALCULATE_COVARIANCE_MATRIX_DESCRIPTION = (
    "Calculate covariance matrix measuring how portfolio tickers move together in absolute terms using the last year (252 trading days) of daily returns data. "
    "Unlike correlation, covariance is not normalized and reflects both the strength and direction of relationships, rounded to 6 decimal places. "
    "Returns dictionary format with tickers list and covariance matrix as nested dictionary. "
    "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings. "
    "Example: calculate_covariance_matrix(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'TSLA': {'allocation': 0.5, 'position': 'short'}})"
)

CALCULATE_COVARIANCE_MATRIX_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA,
    },
    "required": ["portfolio_dict"],
    "additionalProperties": False
}

CALCULATE_COVARIANCE_MATRIX_TOOL = {
    "name": "portfolio_covariance_matrix",
    "description": CALCULATE_COVARIANCE_MATRIX_DESCRIPTION,
    "parameters": CALCULATE_COVARIANCE_MATRIX_PARAMETERS,
    "function": calculate_covariance_matrix,
}
