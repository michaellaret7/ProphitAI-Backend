"""Portfolio risk analysis tool.

Provides a tool for analyzing multi-asset portfolio risk metrics
using the Portfolio class and RiskMetrics model.
"""

from typing import Annotated

from prophitai_atlas.tools.decorator import agent_tool, Param
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_tools.portfolio.utils import build_portfolio_obj


# ================================
# --> Tools
# ================================

@agent_tool(name="portfolio_risk", category="portfolio")
def portfolio_risk(
    tickers: list[str],
    weights: list[float],
    years_back: Annotated[int, Param(min_val=1, max_val=5)] = 1,
) -> str:
    """Compute comprehensive risk metrics for a multi-asset portfolio.

Returns volatility, drawdown, Value-at-Risk, tail risk, and market-relative
risk measures (vs SPY).

**WHEN TO USE:**
- Assessing overall portfolio volatility and downside risk
- Measuring Value-at-Risk and Expected Shortfall at 95%/99% confidence
- Evaluating tail risk via skewness and kurtosis
- Comparing portfolio systematic risk vs SPY (beta, tracking error, capture ratios)

**IMPORTANT:**
- Weights are decimal percentages (0.30 = 30%). Negative = short position.
- Weights do not need to sum to 1.0 (e.g. 70% invested + 30% cash = weights summing to 0.70)
- All market-relative metrics (beta, tracking_error, capture ratios) are vs SPY
- max_drawdown_duration is in trading days

    Args:
        tickers: List of ticker symbols in the portfolio (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        weights: Decimal portfolio weights per ticker, same order as tickers.
            0.30 = 30% allocation. Negative = short. (e.g., [0.40, 0.35, 0.25])
        years_back: Number of years of historical data to analyze

    Returns:
        YAML-formatted risk metrics grouped by tier:
        - Tier 1 (Essential): annualized_volatility, max_drawdown, var_95/99, cvar_95/99
        - Tier 2 (Downside-Focused): downside_deviation, ulcer_index, max_drawdown_duration
        - Tier 3 (Tail Risk): skewness, kurtosis
        - Tier 4 (Market-Relative): beta, up/down_beta, tracking_error, upside/downside_capture, idiosyncratic_vol

    Interpretation Guide (all market-relative metrics benchmarked vs SPY):
        annualized_volatility: Annualized std dev of returns. 10-15% typical for diversified equity. >25% high risk.
        max_drawdown: Worst peak-to-trough decline as decimal. -0.20 = 20% drawdown. >-30% is severe.
        var_95: Daily loss not exceeded 95% of the time. -0.02 = 2% worst-case daily loss (1-in-20 days).
        var_99: Daily loss not exceeded 99% of the time. More extreme than VaR95.
        cvar_95: Expected loss given that VaR95 is breached. Always worse than VaR95. Key tail risk measure.
        cvar_99: Expected loss given that VaR99 is breached. Worst-case average loss scenario.
        downside_deviation: Volatility of negative returns only. Lower = less downside risk. Compare to annualized_volatility.
        ulcer_index: Measures depth and duration of drawdowns. <5% comfortable, 5-10% moderate, >10% painful.
        max_drawdown_duration: Longest drawdown in trading days. >252 = over 1 year underwater.
        skewness: Return asymmetry. <0 = left-skewed (more crash risk). >0 = right-skewed (upside bias).
        kurtosis: Excess kurtosis. >0 = fat tails (more extreme events than normal). >3 = very heavy tails.
        beta: Systematic risk vs SPY. 1.0 = market risk. <0.8 defensive. >1.2 aggressive.
        up_beta: Sensitivity when SPY is up. Higher = captures more upside.
        down_beta: Sensitivity when SPY is down. Lower = more defensive in selloffs.
        tracking_error: Annualized volatility vs SPY returns. <5% index-like. >10% highly active.
        upside_capture: % of SPY gains captured. >100% = outperforms in rallies.
        downside_capture: % of SPY losses captured. <100% = less downside than market.
        idiosyncratic_vol: Non-market volatility (OLS residual). High = stock-specific risk dominates.

    Examples:
        portfolio_risk(tickers=["AAPL", "MSFT", "GOOGL"], weights=[0.40, 0.35, 0.25])
        >>> {"success": True, "data": {"tickers": [...], "weights": [...], "years_back": 1, "risk_metrics": {...}}}

        portfolio_risk(tickers=["AAPL", "TSLA"], weights=[0.60, -0.20], years_back=3)
        >>> {"success": True, "data": {"tickers": [...], "weights": [...], "years_back": 3, "risk_metrics": {...}}}

    Raises:
        ValueError: If tickers and weights have different lengths or no price data found
    """
    try:
        if not tickers or not weights:
            return error_response("tickers and weights must each contain at least one element")

        if len(tickers) != len(weights):
            return error_response(
                f"tickers ({len(tickers)}) and weights ({len(weights)}) must have the same length"
            )

        portfolio = build_portfolio_obj(tickers, weights, years_back)
        risk: dict = portfolio.risk_metrics.model_dump()

        return success_response({
            "risk_metrics": risk,
        })

    except Exception as e:
        return error_response(f"Failed to compute portfolio risk: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(portfolio_risk(
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
        weights=[0.30, 0.25, 0.20, 0.15, 0.10],
        years_back=1,
    ))
