from app.utils.gpt_parser import canonical_portfolio
from app.core.calculations.portfolio.utils import get_portfolio_returns, get_benchmark_returns
from app.core.calculations.risk.calculator import RiskCalculator
from app.models.portfolio_models import PortfolioInput

def calculate_portfolio_beta_vs_index(
    portfolio_dict: PortfolioInput | dict, 
    lookback_days: int = 252,
    index_ticker: str = "SPY",
) -> float:
    """
    Calculate CAPM beta for a long/short portfolio vs index.
    
    Args:
        portfolio_dict: Dict of {ticker: {"allocation": float, "position": "long/short"}}
        lookback_days: Number of days of historical data to use
    
    Returns:
        Portfolio beta vs index
    """
    portfolio_dict = canonical_portfolio(portfolio_dict)
    
    # Use utility functions to get portfolio returns
    portfolio_returns, _ = get_portfolio_returns(
        portfolio=portfolio_dict,
        lookback_days=lookback_days + 50,  # Buffer for returns calc
        use_total_returns=False,  # Use price returns for beta calculation
        dropna=True
    )
    
    if portfolio_returns is None or portfolio_returns.empty:
        return float('nan')
    
    # Get index returns using utility function
    index_returns = get_benchmark_returns(
        benchmark=index_ticker,
        lookback_days=lookback_days + 50,  # Buffer for returns calc
        use_total_returns=False  # Use price returns for beta calculation
    )
    
    if index_returns is None or index_returns.empty:
        return float('nan')
    
    # Calculate and return beta
    return RiskCalculator.beta(portfolio_returns, index_returns)

CALCULATE_PORTFOLIO_BETA_VS_INDEX_DESCRIPTION = (
    "Calculate CAPM beta for a long/short portfolio versus a specified market index using 252 trading days of historical data. "
    "Beta measures the portfolio's systematic risk relative to the index. A beta of 1.0 means the portfolio moves with the market, >1.0 means more volatile than market, <1.0 means less volatile. "
    "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings and specify 'index_ticker'. "
    "Example: calculate_portfolio_beta_vs_index(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'MSFT': {'allocation': 0.5, 'position': 'long'}}, index_ticker='SPY')"
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
                "You MUST include this parameter with all portfolio tickers."
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
                    },
                    index_ticker="SPY"
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
        "index_ticker": {
            "type": "string",
            "description": "Market index ticker to calculate beta against. Common indices: 'SPY' (S&P 500), 'QQQ' (NASDAQ 100), 'IWM' (Russell 2000), 'DIA' (Dow Jones), 'VTI' (Total Market).",
        },
    },
    "required": ["portfolio_dict", "index_ticker"],
    "additionalProperties": False
}

CALCULATE_PORTFOLIO_BETA_VS_INDEX_TOOL = {
    "name": "calculate_portfolio_beta_vs_index",
    "description": CALCULATE_PORTFOLIO_BETA_VS_INDEX_DESCRIPTION,
    "parameters": CALCULATE_PORTFOLIO_BETA_VS_INDEX_PARAMETERS,
    "function": calculate_portfolio_beta_vs_index,
}
