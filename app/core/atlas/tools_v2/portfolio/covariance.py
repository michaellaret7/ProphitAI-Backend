"""Portfolio covariance analysis tool.

Provides a tool for decomposing portfolio risk by asset, surfacing which
holdings are the largest contributors to overall portfolio variance.
"""

import math
from typing import Annotated

from app.core.atlas.tools_v2.decorator import agent_tool, Param
from app.core.atlas.tools_v2.responses import success_response, error_response
from app.core.atlas.tools_v2.portfolio.utils import build_portfolio_obj
from app.core.calc_v2.config import TRADING_DAYS


# ================================
# --> Tools
# ================================

@agent_tool(name="portfolio_covariance")
def portfolio_covariance(
    tickers: list[str],
    weights: list[float],
    years_back: Annotated[int, Param(min_val=1, max_val=5)] = 1,
) -> str:
    """Decompose portfolio risk into per-asset contributions using the covariance matrix.

Returns portfolio variance, annualized volatility, and each asset's marginal,
component, and percentage contribution to total portfolio risk.

**WHEN TO USE:**
- Understanding which holdings drive the most portfolio risk
- Identifying risk concentration (one asset dominating pct_contribution)
- Comparing marginal risk contributions to decide where to trim/add
- Validating that diversification is actually reducing risk

**IMPORTANT:**
- Weights are decimal percentages (0.30 = 30%). Negative = short position.
- Weights do not need to sum to 1.0
- pct_contribution values sum to ~1.0 (100% of portfolio risk)
- marginal_contribution = how much portfolio variance changes per unit weight increase
- component_contribution = weight * marginal_contribution (each asset's absolute risk share)

    Args:
        tickers: List of ticker symbols in the portfolio (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        weights: Decimal portfolio weights per ticker, same order as tickers.
            0.30 = 30% allocation. Negative = short. (e.g., [0.40, 0.35, 0.25])
        years_back: Number of years of historical data to analyze

    Returns:
        YAML-formatted covariance decomposition:
        - portfolio_variance_daily: Daily portfolio variance
        - portfolio_volatility_annualized: Annualized portfolio standard deviation
        - asset_risk_contributions: Per-asset breakdown with weight, marginal_contribution,
          component_contribution, and pct_contribution

    Interpretation Guide:
        portfolio_variance_daily: Daily variance of portfolio returns. Raw building block.
        portfolio_volatility_annualized: sqrt(variance * 252). Typical equity portfolio 15-30%.
        marginal_contribution: Partial derivative of portfolio variance w.r.t. asset weight.
            Higher = adding more of this asset increases risk faster.
        component_contribution: Asset's absolute share of portfolio variance (weight * marginal).
            Sum of all component_contributions = portfolio_variance_daily.
        pct_contribution: component_contribution / portfolio_variance_daily.
            Shows what % of total risk each asset drives. Sum = ~1.0.
            If one asset has pct_contribution > 0.50, portfolio is risk-concentrated.

    Examples:
        portfolio_covariance(tickers=["AAPL", "MSFT", "GOOGL"], weights=[0.40, 0.35, 0.25])
        portfolio_covariance(tickers=["AAPL", "JNJ", "XOM", "TLT"], weights=[0.25, 0.25, 0.25, 0.25], years_back=3)

    Raises:
        ValueError: If tickers and weights have different lengths or no price data found
    """
    try:
        if len(tickers) != len(weights):
            return error_response(
                f"tickers ({len(tickers)}) and weights ({len(weights)}) must have the same length"
            )

        portfolio = build_portfolio_obj(tickers, weights, years_back)
        cov_metrics = portfolio.covariance_metrics.model_dump()

        variance_daily = cov_metrics["portfolio_variance_daily"]
        vol_annualized = round(math.sqrt(variance_daily * TRADING_DAYS), 4)

        return success_response({
            "tickers": portfolio.tickers,
            "years_back": years_back,
            "portfolio_variance_daily": variance_daily,
            "portfolio_volatility_annualized": vol_annualized,
            "asset_risk_contributions": cov_metrics["asset_risk_contributions"],
        })

    except Exception as e:
        return error_response(f"Failed to compute portfolio covariance: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(portfolio_covariance(
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
        weights=[0.30, 0.25, 0.20, 0.15, 0.10],
        years_back=1,
    ))
