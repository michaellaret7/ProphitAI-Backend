import yaml
from app.core.calculations.portfolio.utils import prepare_portfolio_data
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.models.portfolio_models import PortfolioInput
import pandas as pd
from app.utils.gpt_parser import canonical_portfolio

def calculate_covariance_matrix(portfolio_dict: PortfolioInput | dict = None) -> str:
    """
    Calculate covariance matrix for portfolio tickers using historical returns data.
    
    Parameters:
    - portfolio_dict: Portfolio configuration mapping ticker -> {allocation, position}
    
    Returns:
    - Dictionary with tickers list and covariance matrix as nested dictionary
    """
    if not portfolio_dict:
        return yaml.dump({"tickers": [], "covariance_matrix": {}}, default_flow_style=False)
    
    try:
        portfolio_dict = canonical_portfolio(portfolio_dict)
    except Exception as e:
        return yaml.dump({"error": str(e)}, default_flow_style=False)

    # Get tickers and prepare portfolio data
    tickers = list(portfolio_dict.keys())
    
    try:
        # Get portfolio data using utility
        weights_dict, price_data, _ = prepare_portfolio_data(
            portfolio=portfolio_dict,
            lookback_days=252,
            include_dividends=False
        )
        
        if not price_data:
            return yaml.dump({"error": "No price data available for portfolio tickers"}, default_flow_style=False)
        
        # Calculate returns for each ticker
        returns_df = pd.DataFrame({
            ticker: ReturnsCalculator.daily_price_returns(prices)
            for ticker, prices in price_data.items()
            if prices is not None and not prices.empty
        }).dropna()
        
        if returns_df.empty:
            return yaml.dump({"error": "No valid returns data available"}, default_flow_style=False)
        
        # Calculate covariance matrix using RiskCalculator
        cov_matrix = RiskCalculator.covariance_matrix(returns_df, annualize=False)
        
        if cov_matrix.empty:
            return yaml.dump({"error": "Failed to calculate covariance matrix"}, default_flow_style=False)
        
        # Convert to dictionary format
        tickers_list = list(cov_matrix.columns)
        cov_dict = {}
        
        for ticker in tickers_list:
            cov_dict[ticker] = {}
            for other_ticker in tickers_list:
                cov_dict[ticker][other_ticker] = round(float(cov_matrix.loc[ticker, other_ticker]), 6)
        
        return yaml.dump({
            "tickers": tickers_list,
            "covariance_matrix": cov_dict
        }, default_flow_style=False)
        
    except Exception as e:
        return yaml.dump({"error": f"Failed to calculate covariance matrix: {str(e)}"}, default_flow_style=False)


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
                calculate_covariance_matrix(
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

CALCULATE_COVARIANCE_MATRIX_TOOL = {
    "name": "portfolio_covariance_matrix",
    "description": CALCULATE_COVARIANCE_MATRIX_DESCRIPTION,
    "parameters": CALCULATE_COVARIANCE_MATRIX_PARAMETERS,
    "function": calculate_covariance_matrix,
}
