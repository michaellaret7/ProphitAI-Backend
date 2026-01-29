from datetime import datetime
from typing import Optional
import pandas as pd
from app.core.calculations.portfolio.utils import get_portfolio_returns
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.core.config import DEFAULT_LOOKBACK_1Y
from app.models.portfolio_models import PortfolioInput
import numpy as np
from app.utils.tool_validator import ToolValidator
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.core.atlas.tools.tool_schemas import PORTFOLIO_DICT_SCHEMA
from app.core.atlas.tools.responses import success_response, error_response

@log_simulation_data_range()
def vol_es(
    portfolio_dict: PortfolioInput | dict = None,
    horizon_days: int = 1,
    conf: float = 0.99,
    method: str = 'param',
    *,
    _simulation_date: Optional[datetime] = None
) -> str:
    """
    Calculate Volatility, Value at Risk (VaR), and Expected Shortfall (ES) for portfolio.

    Parameters:
    - portfolio_dict: Portfolio configuration mapping ticker -> {allocation, position}
    - horizon_days: Time horizon for risk calculation (default: 1 day)
    - conf: Confidence level (default: 0.99 for 99% confidence)
    - method: Calculation method {'param', 'hist', 'ewma'}
    - _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
    - VaR: Value at Risk at specified confidence level
    - ES: Expected Shortfall (conditional VaR)
    - vol: Portfolio volatility (annualized)
    """
    # Validate inputs
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)
    v.require_numeric('horizon_days', horizon_days, min_val=1)
    v.require_numeric('conf', conf, min_val=0.5, max_val=0.999)
    v.require_enum('method', method, ['param', 'hist'])

    if not v.is_valid():
        return v.error_response()

    # Get validated/normalized values
    portfolio_dict = v.get('portfolio_dict')
    horizon_days = v.get('horizon_days')
    conf = v.get('conf')
    method = v.get('method')

    try:

        # Get portfolio returns using the utility
        portfolio_returns, _ = get_portfolio_returns(
            portfolio=portfolio_dict,
            lookback_days=DEFAULT_LOOKBACK_1Y,
            use_total_returns=False,  # Use price returns for volatility metrics
            dropna=True,
            _simulation_date=_simulation_date
        )

        if portfolio_returns is None or portfolio_returns.empty:
            return error_response("No price data available for portfolio tickers, move on to the next tool")

        # Log actual data range
        if isinstance(portfolio_returns, pd.Series) and len(portfolio_returns) > 0:
            if hasattr(portfolio_returns, 'index') and isinstance(portfolio_returns.index, pd.DatetimeIndex):
                start_date = portfolio_returns.index.min().date()
                end_date = portfolio_returns.index.max().date()
                count = len(portfolio_returns)
                print(f"  📅 ACTUAL DATA USED:")
                if _simulation_date:
                    cutoff_ok = portfolio_returns.index.max() <= _simulation_date
                    cutoff_status = "✅" if cutoff_ok else "⚠️ EXCEEDS CUTOFF"
                    print(f"    • vol_es_data: {start_date} → {end_date} ({count} points) {cutoff_status}")
                else:
                    print(f"    • vol_es_data: {start_date} → {end_date} ({count} points)")

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
            return error_response("Method 'ewma' not supported with calculations_v2. Use 'param' or 'hist'.")
        else:
            return error_response(f"Invalid method '{method}'. Use 'param' or 'hist'")

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

        return success_response(result)

    except Exception as e:
        return error_response(f"Failed to calculate vol_es: {str(e)}")


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
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA,
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
