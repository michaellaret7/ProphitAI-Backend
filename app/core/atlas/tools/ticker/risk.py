"""Ticker risk analysis tool.

Provides a tool for analyzing single-ticker risk metrics using the Ticker
class and RiskMetrics model.
"""

from typing import Annotated

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.core.atlas.tools.ticker.utils import build_ticker_obj


# ================================
# --> Tools
# ================================

@agent_tool(name="ticker_risk")
def ticker_risk(
    ticker: str,
    years_back: Annotated[int, Param(min_val=1, max_val=5)] = 1,
) -> str:
    """
    Compute comprehensive risk metrics for a single ticker.

    Returns volatility, drawdown, Value at Risk, Expected Shortfall, tail risk
    statistics, and market-relative risk measures (beta, capture ratios, tracking
    error) benchmarked against SPY.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'KO')
        years_back: Number of years of historical data to analyze

    Returns:
        YAML-formatted risk metrics grouped by tier:
        - Tier 1 (Essential): volatility, max drawdown, VaR, CVaR
        - Tier 2 (Downside): downside deviation, ulcer index, drawdown duration
        - Tier 3 (Tail Risk): skewness, kurtosis
        - Tier 4 (Market-Relative): beta, up/down beta, tracking error, capture ratios

    Interpretation Guide (all benchmarked vs SPY, typical SPY vol ~15-18%):
        annualized_volatility: <15% low, 15-25% moderate, 25-40% high, >40% very high.
        max_drawdown: Negative decimal. -0.10 mild, -0.20 notable, -0.30+ severe.
        var_95/var_99: Worst expected daily loss (negative decimal) at 95%/99% confidence.
        cvar_95/cvar_99: Avg loss in worst 5%/1% of days. Always worse than VaR. <-0.05 is heavy tail risk.
        downside_deviation: Vol from negative returns only. Close to annualized_vol = mostly downside risk.
        ulcer_index: Drawdown pain. <0.05 calm, 0.05-0.15 moderate, >0.15 painful.
        max_drawdown_duration: Trading days in longest drawdown. >252 = over a year without recovery.
        skewness: <-1 crash-prone, -0.5 to 0 typical, >0 positive skew.
        kurtosis: Excess kurtosis. 0-3 typical, >6 frequent extreme moves.
        beta: <0.8 defensive, 1.0 market-like, >1.5 aggressive.
        up_beta/down_beta: Ideal is high up_beta + low down_beta.
        tracking_error: <10% tracks market closely, 10-20% moderate, >25% very different profile.
        upside/downside_capture: Expressed as %. >100 upside = outperforms in rallies, <100 downside = protects in selloffs.
        idiosyncratic_vol: Stock-specific risk. <10% market-driven, 10-20% moderate, >25% high (event-driven).

    Examples:
        ticker_risk(ticker="AAPL", years_back=1)
        >>> {"success": True, "data": {"ticker": "AAPL", "years_back": 1, "risk_metrics": {...}}}

    Raises:
        ValueError: If ticker has no available price data
    """
    try:
        ticker = ticker.upper().strip()
        ticker_obj = build_ticker_obj(ticker, years_back)
        risk: dict = ticker_obj.risk_metrics.model_dump()

        return success_response({
            "ticker": ticker,
            "years_back": years_back,
            "risk_metrics": risk,
        })

    except Exception as e:
        return error_response(f"Failed to compute risk metrics for {ticker}: {str(e)}")

