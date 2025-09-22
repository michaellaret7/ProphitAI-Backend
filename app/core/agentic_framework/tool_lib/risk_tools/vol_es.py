from app.core.calculations.portfolio.utils import get_portfolio_returns
from app.core.calculations.risk.calculator import RiskCalculator
from app.models.portfolio_models import PortfolioInput
from app.utils.gpt_parser import canonical_portfolio

import numpy as np

def vol_es(portfolio_dict: PortfolioInput | dict = None, horizon_days: int = 1, conf: float = 0.99, method: str = 'param') -> dict:
    """
    Calculate Volatility, Value at Risk (VaR), and Expected Shortfall (ES) for portfolio.
    
    Parameters:
    - portfolio_dict: Portfolio configuration mapping ticker -> {allocation, position}
    - horizon_days: Time horizon for risk calculation (default: 1 day)
    - conf: Confidence level (default: 0.99 for 99% confidence)
    - method: Calculation method {'param', 'hist', 'ewma'}
    
    Returns:
    - VaR: Value at Risk at specified confidence level
    - ES: Expected Shortfall (conditional VaR)
    - vol: Portfolio volatility (annualized)
    """
    if not portfolio_dict:
        return {"error": "Portfolio dictionary is required"}
    
    try:
        portfolio_dict = canonical_portfolio(portfolio_dict)
    except Exception as e:
        return {"error": str(e)}
    
    try:
        # Get portfolio returns using the utility
        portfolio_returns, _ = get_portfolio_returns(
            portfolio=portfolio_dict,
            lookback_days=252,
            use_total_returns=False,  # Use price returns for volatility metrics
            dropna=True
        )
        
        if portfolio_returns is None or portfolio_returns.empty:
            return {"error": "No price data available for portfolio tickers"}

        # Calculate VaR/ES and volatility using calculations_v2
        if method == 'param':
            annual_vol = RiskCalculator.annualized_volatility(portfolio_returns)
            var_1day = RiskCalculator.parametric_var(annual_vol, confidence=conf)
            es_value = RiskCalculator.parametric_cvar(annual_vol, confidence=conf)

        elif method == 'hist':
            var_1day = RiskCalculator.historical_var(portfolio_returns, confidence=conf)
            es_value = RiskCalculator.expected_shortfall(portfolio_returns, confidence=conf)
            annual_vol = RiskCalculator.annualized_volatility(portfolio_returns)
            
        elif method == 'ewma':
            return {"error": "Method 'ewma' not supported with calculations_v2. Use 'param' or 'hist'."}
        else:
            return {"error": f"Invalid method '{method}'. Use 'param' or 'hist'"}

        # Scale VaR for time horizon and annualize
        var_scaled = float(var_1day) * np.sqrt(horizon_days)
        es_scaled = float(es_value) * np.sqrt(horizon_days)
        var_annual = float(var_1day) * np.sqrt(252)

        result = {
            'method': method,
            'confidence_level': conf,
            'horizon_days': horizon_days,
            'VaR': round(float(var_scaled), 6),
            'ES': round(float(es_scaled), 6),
            'vol': round(float(annual_vol), 6),
            'var_1day': round(float(var_1day), 6),
            'var_annual': round(float(var_annual), 6)
        }

        return result
        
    except Exception as e:
        return {"error": f"Failed to calculate vol_es: {str(e)}"}


# Tool Schema Constants
VOL_ES_DESCRIPTION = (
    "Calculate portfolio volatility, Value at Risk (VaR), and Expected Shortfall (ES) using parametric or historical methods. "
    "Returns risk metrics including VaR, ES, and annualized volatility for specified time horizon and confidence level. "
    "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings and specify calculation parameters. "
    "Example: vol_es(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'TSLA': {'allocation': 0.5, 'position': 'short'}}, method='param', conf=0.99)"
)

VOL_ES_PARAMETERS = {
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
                vol_es(
                    portfolio_dict={
                        "AAPL": {"allocation": 0.125, "position": "long"},
                        "MSFT": {"allocation": 0.125, "position": "long"},
                        "AMZN": {"allocation": 0.125, "position": "long"},
                        "TSLA": {"allocation": 0.125, "position": "short"},
                        "META": {"allocation": 0.125, "position": "short"},
                        "SPY": {"allocation": 0.125, "position": "long"},
                        "QQQ": {"allocation": 0.125, "position": "long"},
                        "IWM": {"allocation": 0.125, "position": "short"}
                    },
                    method="param",
                    conf=0.99,
                    horizon_days=1
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
        "horizon_days": {
            "type": "integer",
            "description": "Time horizon for risk calculation in days (default: 1 day)",
            "default": 1,
            "minimum": 1
        },
        "conf": {
            "type": "number",
            "description": "Confidence level for VaR/ES calculation (default: 0.99 for 99% confidence)",
            "default": 0.99,
            "minimum": 0.5,
            "maximum": 0.999
        },
        "method": {
            "type": "string",
            "description": "Calculation method. 'param' uses parametric method with normal distribution, 'hist' uses historical simulation.",
            "enum": ["param", "hist"],
            "default": "param"
        },
    },
    "required": ["portfolio_dict"],
    "additionalProperties": False
}

VOL_ES_TOOL = {
    "name": "portfolio_vol_es",
    "description": VOL_ES_DESCRIPTION,
    "parameters": VOL_ES_PARAMETERS,
    "function": vol_es,
}