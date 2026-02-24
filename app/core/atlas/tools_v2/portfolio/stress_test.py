"""Portfolio stress testing tool.

Provides a tool for running ETF beta-shock stress tests on a multi-asset
portfolio using the Portfolio class and StressTestResult model from calc_v2.
"""

from typing import Annotated

from app.core.atlas.tools_v2.decorator import agent_tool, Param, Schema
from app.core.atlas.tools_v2.responses import success_response, error_response
from app.core.atlas.tools_v2.portfolio.utils import build_portfolio_obj


# ================================
# --> Helper funcs
# ================================

SHOCKS_SCHEMA = {
    "type": "object",
    "description": (
        "ETF shock magnitudes as {ETF_ticker: shock_size}. "
        "Each value is a decimal return shock applied to that ETF factor. "
        'Example: {"SPY": -0.05, "TLT": 0.10, "GLD": -0.04} means '
        "SPY drops 5%, TLT rises 10%, GLD drops 4%."
    ),
    "additionalProperties": {"type": "number"},
}


# ================================
# --> Tools
# ================================

@agent_tool(name="portfolio_stress_test")
def portfolio_stress_test(
    tickers: list[str],
    weights: list[float],
    shocks: Annotated[dict, Schema(SHOCKS_SCHEMA)],
    years_back: Annotated[int, Param(min_val=1, max_val=5)] = 2,
) -> str:
    """Run an ETF beta-shock stress test on a multi-asset portfolio.

Estimates portfolio-level impact by regressing each holding (and the portfolio)
against ETF factor returns via OLS, then applying user-supplied shock magnitudes.

**WHEN TO USE:**
- Estimating portfolio P&L under a hypothetical market scenario (e.g. equity crash + rates spike)
- Identifying which holdings are most vulnerable (top detractors) or most protective (top hedges)
- Decomposing stress impact by ETF factor (equity, rates, commodities, EM)
- Measuring residual (idiosyncratic) risk not captured by the factor model

**IMPORTANT:**
- Weights are decimal percentages (0.30 = 30%). Negative = short position.
- Shocks are decimal returns: -0.05 = 5% drop, 0.10 = 10% rally.
- Common ETF factors: SPY (equity), TLT (long-term treasuries), GLD (gold), EEM (emerging markets),
  HYG (high yield credit), UUP (US dollar), XLE (energy), XLF (financials)
- Two expected-return estimates are provided:
    - expected_return (top-down): portfolio-level OLS betas x shocks — consistent with residual_std
    - expected_return_bottom_up: sum of per-ticker OLS PnLs — useful for attribution
- All results are on a daily horizon

    Args:
        tickers: List of ticker symbols in the portfolio (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        weights: Decimal portfolio weights per ticker, same order as tickers.
            0.30 = 30% allocation. Negative = short. (e.g., [0.40, 0.35, 0.25])
        shocks: ETF shock magnitudes as {ETF_ticker: shock_size}.
            Each value is a decimal return shock. Example: {"SPY": -0.05, "TLT": 0.10}
        years_back: Number of years of historical data for OLS regressions (default 2)

    Returns:
        YAML-formatted stress test results:
        - Portfolio-level: expected_return, expected_return_bottom_up, stressed_var_95,
          r_squared, residual_std, idiosyncratic_vol_annual, total_stressed_vol
        - Per-ticker: expected_return, weighted_pnl, pct_of_portfolio_impact
        - Per-ETF: shock, portfolio_sensitivity, contribution, pct_of_total
        - Diagnostics: factor_vif (Variance Inflation Factor per ETF factor)
        - Summary: top_hedges

    Interpretation Guide:
        expected_return: Estimated daily portfolio return under the stress scenario (top-down OLS).
        expected_return_bottom_up: Same estimate built from per-ticker attribution — use for drill-down.
        stressed_var_95: 95% VaR under stress = expected_return - 1.65 x residual_std. Worst daily loss at 95% confidence.
        r_squared: How much of portfolio variance the ETF factors explain. >0.80 = good model fit.
        residual_std: Daily std of OLS residuals = unexplained (idiosyncratic) risk.
        idiosyncratic_vol_annual: Annualized idiosyncratic volatility.
        total_stressed_vol: Annualized total portfolio vol under stress (systematic + idiosyncratic).
        ticker weighted_pnl: weight x expected_return for that ticker. Negative = drag on portfolio.
        pct_of_portfolio_impact: What fraction of total portfolio stress this ticker contributes.
        etf contribution: portfolio_sensitivity x shock. Shows how much each ETF shock drives the total.
        factor_vif: Variance Inflation Factor per ETF factor. Detects multicollinearity.
            VIF < 5 = acceptable. VIF 5-10 = moderate collinearity, betas may be unstable.
            VIF > 10 = severe collinearity, betas between collinear factors are unreliable.
            If VIF is high, consider dropping one of the correlated factors (e.g. use QQQ OR SPY, not both).
        top_hedges: Holdings with best weighted PnL under stress — natural offsets.

    Examples:
        portfolio_stress_test(
            tickers=["AAPL", "MSFT", "GOOGL"],
            weights=[0.40, 0.35, 0.25],
            shocks={"SPY": -0.05, "TLT": 0.10}
        )

        portfolio_stress_test(
            tickers=["AAPL", "TSLA", "JPM", "XOM"],
            weights=[0.30, -0.15, 0.25, 0.30],
            shocks={"SPY": -0.05, "TLT": 0.10, "GLD": -0.04, "EEM": 0.15},
            years_back=3
        )

    Raises:
        ValueError: If tickers and weights have different lengths, no price data found,
            or ETF factor data unavailable
    """
    try:
        if len(tickers) != len(weights):
            return error_response(
                f"tickers ({len(tickers)}) and weights ({len(weights)}) must have the same length"
            )

        if not shocks:
            return error_response("shocks must contain at least one ETF → shock mapping")

        portfolio = build_portfolio_obj(tickers, weights, years_back, shocks=shocks)

        if portfolio.stress_test is None:
            return error_response("Stress test computation failed — check ETF factor data availability")

        result = portfolio.stress_test.model_dump()
        
        result["ticker_results"] = [
            tr.model_dump(exclude={"factor_betas", "factor_beta_std_errors"})
            for tr in portfolio.stress_test.ticker_results
        ]
        result.pop("top_detractors", None)

        return success_response({
            "tickers": portfolio.tickers,
            "weights": [round(w, 4) for w in portfolio.weights.tolist()],
            "years_back": years_back,
            "shocks": shocks,
            "stress_test": result,
        })

    except Exception as e:
        return error_response(f"Failed to run portfolio stress test: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(portfolio_stress_test(
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
        weights=[0.30, 0.25, 0.20, 0.15, 0.10],
        shocks={"QQQ": -0.05, "TLT": 0.10, "GLD": -0.04},
        years_back=2,
    ))
