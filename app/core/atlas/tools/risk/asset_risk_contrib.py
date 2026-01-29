from datetime import datetime
from typing import Optional
from app.core.calculations.portfolio.utils import prepare_portfolio_data
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.core.config import DEFAULT_LOOKBACK_1Y
from app.models.portfolio_models import PortfolioInput
import pandas as pd
import numpy as np
from app.core.calculations.core.helpers import build_returns_df_from_price_map
from app.utils.tool_validator import ToolValidator
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.core.atlas.tools.tool_schemas import PORTFOLIO_DICT_SCHEMA
from app.core.atlas.tools.responses import success_response, error_response

@log_simulation_data_range()
def risk_contribution(
    portfolio_dict: PortfolioInput | dict = None,
    metric: str = 'vol',
    *,
    _simulation_date: Optional[datetime] = None
) -> str:
    """
    Calculate Total Risk and risk contributions by asset.

    Parameters:
    - portfolio_dict: Portfolio configuration mapping ticker -> {allocation, position}
    - metric: Risk metric to decompose {'vol', 'var'}
    - _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
    - TR: Total Risk (portfolio level)
    - MCTR: Marginal Contribution to Total Risk (per asset)
    - CTR_pct: Component Total Risk as percentage (per asset)
    """
    # Validate inputs
    v = ToolValidator()
    v.require_portfolio('portfolio_dict', portfolio_dict, normalize=True)
    v.require_enum('metric', metric, ['vol', 'var'])

    if not v.is_valid():
        return v.error_response()

    # Get validated/normalized values (portfolio already normalized by validator)
    portfolio_dict = v.get('portfolio_dict')
    metric = v.get('metric')

    try:

        # Get tickers and weights from portfolio
        tickers = list(portfolio_dict.keys())
        weights_series = pd.Series({
            ticker: portfolio_dict[ticker]['allocation'] * (1 if portfolio_dict[ticker]['position'] == 'long' else -1)
            for ticker in tickers
        })

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
            return error_response("No price data available for portfolio tickers")

        # Calculate covariance matrix using v2
        cov_matrix = RiskCalculator.covariance_matrix(returns_df, annualize=False)

        # Align weights to covariance columns
        aligned_weights = weights_series.reindex(cov_matrix.columns).fillna(0.0)
        w = aligned_weights.to_numpy(dtype=float)
        Sigma = cov_matrix.to_numpy(dtype=float)

        if metric == 'vol':
            # Volatility-based risk contribution
            portfolio_variance = float(w @ Sigma @ w)
            total_risk = float(np.sqrt(max(portfolio_variance, 0.0)))  # Portfolio volatility
            if total_risk == 0.0:
                marginal_contrib = np.zeros_like(w)
                component_contrib = np.zeros_like(w)
                ctr_pct = np.zeros_like(w)
            else:
                marginal_contrib = (Sigma @ w) / total_risk
                component_contrib = w * marginal_contrib
                ctr_pct = (component_contrib / total_risk) * 100.0

        elif metric == 'var':
            # VaR-based risk contribution using v2 marginal_var
            mv_series, cv_series = RiskCalculator.marginal_var(aligned_weights, cov_matrix, confidence=0.99, as_percent_of_portfolio_var=False)
            total_risk = float(cv_series.sum())
            marginal_contrib = mv_series.reindex(cov_matrix.columns).to_numpy(dtype=float)
            component_contrib = cv_series.reindex(cov_matrix.columns).to_numpy(dtype=float)
            if total_risk != 0.0:
                ctr_pct = (component_contrib / total_risk) * 100.0
            else:
                ctr_pct = np.zeros_like(component_contrib)

        else:
            return error_response(f"Invalid metric '{metric}'. Use 'vol' or 'var'")

        # Build result dictionary
        result = {
            'metric': metric,
            'TR': round(float(total_risk), 6),
            'MCTR': {ticker: round(float(marginal_contrib[i]), 6) for i, ticker in enumerate(cov_matrix.columns)},
            'CTR_pct': {ticker: round(float(ctr_pct[i]), 2) for i, ticker in enumerate(cov_matrix.columns)}
        }

        return success_response(result)

    except Exception as e:
        return error_response(f"Failed to calculate risk_contribution: {str(e)}")


# Tool Schema Constants
RISK_CONTRIBUTION_DESCRIPTION = (
    "Calculate total risk and risk contributions by asset using either volatility ('vol') or Value at Risk ('var') decomposition. "
    "Returns total risk (TR), marginal contribution to total risk (MCTR) per asset, and component total risk as percentage (CTR_pct) per asset. "
    "CRITICAL: You MUST ALWAYS include the portfolio_dict parameter with ALL holdings and specify 'metric' as 'vol' or 'var'. "
    "Example: risk_contribution(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'TSLA': {'allocation': 0.5, 'position': 'short'}}, metric='vol')"
)

RISK_CONTRIBUTION_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA,
        "metric": {
            "type": "string",
            "description": "Risk metric to decompose. 'vol' calculates volatility-based risk contributions, 'var' calculates Value at Risk-based contributions.",
            "enum": ["vol", "var"],
            "default": "vol"
        },
    },
    "required": ["portfolio_dict", "metric"],
    "additionalProperties": False
}

RISK_CONTRIBUTION_TOOL = {
    "name": "portfolio_risk_contribution_by_asset",
    "description": RISK_CONTRIBUTION_DESCRIPTION,
    "parameters": RISK_CONTRIBUTION_PARAMETERS,
    "function": risk_contribution,
}
