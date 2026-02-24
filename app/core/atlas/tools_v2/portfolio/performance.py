"""Portfolio performance analysis tool.

Provides a tool for analyzing multi-asset portfolio performance metrics
using the Portfolio class and PerformanceMetrics model from calc_v2.
"""

from typing import Annotated

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.core.atlas.tools_v2.portfolio.utils import build_portfolio_obj


# ================================
# --> Tools
# ================================

@agent_tool(name="portfolio_performance")
def portfolio_performance(
    tickers: list[str],
    weights: list[float],
    years_back: Annotated[int, Param(min_val=1, max_val=5)] = 1,
) -> str:
    """Compute comprehensive performance metrics for a multi-asset portfolio.

Returns absolute returns, risk-adjusted ratios, return distribution quality,
market-relative performance (vs SPY), and trailing momentum across multiple
horizons.

**WHEN TO USE:**
- Evaluating overall portfolio return quality and risk-adjusted performance
- Comparing portfolio performance against SPY benchmark
- Assessing return distribution (win rate, profit factor, tail ratio)
- Checking trailing momentum across 1m to 5yr horizons

**IMPORTANT:**
- Weights are decimal percentages (0.30 = 30%). Negative = short position.
- Weights do not need to sum to 1.0 (e.g. 70% invested + 30% cash = weights summing to 0.70)
- All benchmark-relative metrics (alpha, information_ratio, treynor_ratio) are vs SPY
- Momentum periods that exceed the data window will be None

    Args:
        tickers: List of ticker symbols in the portfolio (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        weights: Decimal portfolio weights per ticker, same order as tickers.
            0.30 = 30% allocation. Negative = short. (e.g., [0.40, 0.35, 0.25] or [0.60, -0.20, 0.20])
        years_back: Number of years of historical data to analyze

    Returns:
        YAML-formatted performance metrics grouped by tier:
        - Tier 1 (Core Returns): annualized_return, cumulative_total_return
        - Tier 2a (Risk-Adjusted): sharpe, sortino, calmar, omega
        - Tier 2b (Distribution Quality): win_rate, profit_factor, gain_loss_ratio, tail_ratio
        - Tier 3 (Market-Relative): alpha, information_ratio, treynor_ratio
        - Tier 4 (Momentum): 1m, 3m, 6m, 1yr, 3yr, 5yr trailing momentum

    Interpretation Guide (all market-relative metrics benchmarked vs SPY):
        annualized_return: CAGR over the period. 8-12% is market-average for equities.
        cumulative_total_return: Total gain/loss as decimal. 0.25 = 25% total return.
        sharpe_ratio: Return per unit of total risk (rf=4.5%). <0.5 poor, 0.5-1.0 decent, 1.0-2.0 good, >2.0 excellent.
        sortino_ratio: Return per unit of downside risk. Same scale as Sharpe but usually higher.
        calmar_ratio: Annualized return / max drawdown. <0.5 poor, 0.5-1.0 fair, >2.0 excellent.
        omega_ratio: Probability-weighted gains / losses. >1.0 means gains outweigh losses overall.
        win_rate: % of positive return days. Typical equity portfolio ~52-54%.
        profit_factor: Gross profits / gross losses. >1.0 profitable, >1.5 strong, >2.0 excellent.
        gain_loss_ratio: Avg winning day / |avg losing day|. >1.0 = winners larger than losers.
        tail_ratio: 95th pctile / |5th pctile|. >1.0 = right tail fatter (upside skew).
        alpha: Annualized excess return vs SPY. >0 outperforming, <0 underperforming.
        information_ratio: Alpha / tracking error. >0.5 good, >1.0 excellent active management.
        treynor_ratio: Return per unit of systematic risk (beta). Higher = better compensated for market risk.
        momentum_Xm/Xyr: Cumulative return over trailing period. Positive = uptrend.

    Examples:
        portfolio_performance(tickers=["AAPL", "MSFT", "GOOGL"], weights=[0.40, 0.35, 0.25])
        >>> {"success": True, "data": {"tickers": [...], "weights": [...], "years_back": 1, "performance_metrics": {...}}}

        portfolio_performance(tickers=["AAPL", "TSLA"], weights=[0.60, -0.20], years_back=3)
        >>> {"success": True, "data": {"tickers": [...], "weights": [...], "years_back": 3, "performance_metrics": {...}}}

    Raises:
        ValueError: If tickers and weights have different lengths or no price data found
    """
    try:
        if len(tickers) != len(weights):
            return error_response(
                f"tickers ({len(tickers)}) and weights ({len(weights)}) must have the same length"
            )

        portfolio = build_portfolio_obj(tickers, weights, years_back)
        perf: dict = portfolio.performance_metrics.model_dump()

        # Reason: strip momentum periods that equal or exceed the data window
        perf.pop("momentum_5yr", None)
        if years_back <= 3:
            perf.pop("momentum_3yr", None)
        if years_back == 1:
            perf.pop("momentum_1yr", None)

        return success_response({
            "tickers": portfolio.tickers,
            "weights": [round(w, 4) for w in portfolio.weights.tolist()],
            "years_back": years_back,
            "performance_metrics": perf,
        })

    except Exception as e:
        return error_response(f"Failed to compute portfolio performance: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(portfolio_performance(
        tickers=["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
        weights=[0.30, 0.25, 0.20, 0.15, 0.10],
        years_back=1,
    ))
