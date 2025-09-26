import yaml
import pandas as pd
import numpy as np
from app.utils.gpt_parser import canonical_portfolio
from app.core.calculations.portfolio.utils import get_portfolio_returns, get_benchmark_returns
from app.core.calculations.risk.calculator import RiskCalculator
from app.models.portfolio_models import PortfolioInput

def calculate_portfolio_beta_vs_index(
    portfolio_dict: PortfolioInput | dict, 
    lookback_days: int = 252,
    index_ticker: str = "SPY",
) -> str:
    """
    Calculate CAPM beta for a long/short portfolio vs index.
    
    Args:
        portfolio_dict: Dict of {ticker: {"allocation": float, "position": "long/short"}}
        lookback_days: Number of days of historical data to use
    
    Returns:
        Portfolio beta vs index
    """
    try:
        if not isinstance(portfolio_dict, dict):
            return yaml.dump({"beta": None, "error": "No portfolio_dict provided, try again with a valid portfolio_dict"}, default_flow_style=False)
        
        portfolio_dict = canonical_portfolio(portfolio_dict)
        
        # Use utility functions to get portfolio returns
        portfolio_returns, _ = get_portfolio_returns(
            portfolio=portfolio_dict,
            lookback_days=lookback_days + 50,  # Buffer for returns calc
            use_total_returns=False,  # Use price returns for beta calculation
            dropna=True
        )
        
        if portfolio_returns is None or portfolio_returns.empty:
            print(f"DEBUG: Portfolio returns is None or empty. Portfolio: {list(portfolio_dict.keys())}")
            return yaml.dump({"beta": None, "error": "No portfolio returns data"}, default_flow_style=False)
        
        # Get index returns using utility function
        index_returns = get_benchmark_returns(
            benchmark=index_ticker,
            lookback_days=lookback_days + 50,  # Buffer for returns calc
            use_total_returns=False  # Use price returns for beta calculation
        )
        
        if index_returns is None or index_returns.empty:
            print(f"DEBUG: Index returns is None or empty for {index_ticker}")
            return yaml.dump({"beta": None, "error": f"No index returns data for {index_ticker}"}, default_flow_style=False)
        
        # Calculate and return beta
        beta = RiskCalculator.beta(portfolio_returns, index_returns)
        
        # Check if beta is NaN or invalid
        if pd.isna(beta) or np.isnan(beta):
            print(f"DEBUG: Beta calculation resulted in NaN. Portfolio returns length: {len(portfolio_returns)}, Index returns length: {len(index_returns)}")
            return yaml.dump({"beta": None, "error": "Beta calculation resulted in NaN"}, default_flow_style=False)
        
        return yaml.dump({"beta": round(float(beta), 3)}, default_flow_style=False)
        
    except Exception as e:
        print(f"DEBUG: Exception in beta calculation: {str(e)}")
        return yaml.dump({"beta": None, "error": str(e)}, default_flow_style=False)

CALCULATE_PORTFOLIO_BETA_VS_INDEX_DESCRIPTION = (
    "Calculate CAPM beta for a long/short portfolio versus SPY benchmark using 252 trading days of historical data. "
    "Beta measures the portfolio's systematic risk relative to the market. A beta of 1.0 means the portfolio moves with the market, >1.0 means more volatile than market, <1.0 means less volatile. "
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
