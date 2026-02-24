"""Ticker performance analysis tool.

Provides a tool for analyzing single-ticker performance metrics using the Ticker
class and PerformanceMetrics model from calc_v2.
"""

from typing import Annotated

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.core.atlas.tools_v2.ticker.risk import _build_ticker_obj


# ================================
# --> Tools
# ================================

@agent_tool(name="ticker_performance")
def ticker_performance(
    ticker: str,
    years_back: Annotated[int, Param(min_val=1, max_val=5)] = 1,
) -> str:
    """
    Compute comprehensive performance metrics for a single ticker.

    Returns absolute returns, risk-adjusted ratios, return distribution quality,
    market-relative performance, and momentum across multiple horizons.
    All market-relative metrics are benchmarked against SPY.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'KO')
        years_back: Number of years of historical data to analyze

    Returns:
        YAML-formatted performance metrics grouped by tier:
        - Tier 1 (Core Returns): annualized return, cumulative total return
        - Tier 2a (Risk-Adjusted): sharpe, sortino, calmar, omega
        - Tier 2b (Distribution Quality): win rate, profit factor, gain/loss ratio, tail ratio
        - Tier 3 (Market-Relative): alpha, information ratio, treynor ratio
        - Tier 4 (Momentum): 1m, 3m, 6m, 1yr, 3yr, 5yr momentum

    Interpretation Guide (all market-relative metrics benchmarked vs SPY):
        annualized_return: CAGR over the period. 8-12% is market-average for equities.
        cumulative_total_return: Total gain/loss as decimal. 0.25 = 25% total return.
        sharpe_ratio: Return per unit of total risk (rf=0). <0.5 poor, 0.5-1.0 decent, 1.0-2.0 good, >2.0 excellent.
        sortino_ratio: Return per unit of downside risk. Same scale as Sharpe but usually higher.
        calmar_ratio: Annualized return / max drawdown. <0.5 poor, 0.5-1.0 fair, >2.0 excellent.
        omega_ratio: Probability-weighted gains / losses. >1.0 means gains outweigh losses overall.
        win_rate: % of positive return days. Typical equity ~52-54%.
        profit_factor: Gross profits / gross losses. >1.0 profitable, >1.5 strong, >2.0 excellent.
        gain_loss_ratio: Avg winning day / |avg losing day|. >1.0 = winners larger than losers.
        tail_ratio: 95th pctile / |5th pctile|. >1.0 = right tail fatter (upside skew).
        alpha: Annualized excess return vs benchmark. >0 outperforming, <0 underperforming.
        information_ratio: Alpha / tracking error. >0.5 good, >1.0 excellent active management.
        treynor_ratio: Return per unit of systematic risk (beta). Higher = better compensated for market risk.
        momentum_Xm/Xyr: Cumulative return over trailing period. Positive = uptrend.

    Examples:
        ticker_performance(ticker="AAPL", years_back=1)
        >>> {"success": True, "data": {"ticker": "AAPL", "years_back": 1, "performance_metrics": {...}}}

    Raises:
        ValueError: If ticker has no available price data
    """
    try:
        ticker = ticker.upper().strip()
        ticker_obj = _build_ticker_obj(ticker, years_back)
        perf: dict = ticker_obj.performance_metrics.model_dump()

        perf.pop("momentum_5yr")

        if years_back <= 3:
            perf.pop("momentum_3yr")
        if years_back == 1:
            perf.pop("momentum_1yr")

        return success_response({
            "ticker": ticker,
            "years_back": years_back,
            "performance_metrics": perf,
        })

    except Exception as e:
        return error_response(f"Failed to compute performance metrics for {ticker}: {str(e)}")

