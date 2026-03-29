"""Portfolio industry classification tool.

Provides a tool for analyzing portfolio exposure breakdown by sector,
industry, and sub-industry — including concentration and group-level VaR.
"""

from typing import Annotated

from prophitai_calculations.models.group_metrics import GroupMetrics
from prophitai_atlas.tools.decorator import agent_tool, Param
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_tools.portfolio.utils import build_portfolio_obj


# ================================
# --> Helper funcs
# ================================

def _format_group_metrics(metrics: dict[str, GroupMetrics]) -> dict[str, dict]:
    """Convert GroupMetrics dict to a serializable dict sorted by concentration descending.

    Args:
        metrics: Dict of group name → GroupMetrics.

    Returns:
        Dict of group name → {concentration, var_99, tickers}, sorted by concentration.
    """
    sorted_groups = sorted(metrics.items(), key=lambda x: abs(x[1].concentration), reverse=True)
    return {
        name: gm.model_dump()
        for name, gm in sorted_groups
    }


# ================================
# --> Tools
# ================================

@agent_tool(name="portfolio_classification", category="portfolio")
def portfolio_classification(
    tickers: list[str],
    weights: list[float],
    years_back: Annotated[int, Param(min_val=1, max_val=5)] = 1,
) -> str:
    """Analyze portfolio exposure breakdown by sector, industry, and sub-industry.

Returns concentration (weight allocation), group-level 99% VaR, and constituent
tickers for each classification group, plus portfolio-level exposure metrics.

**WHEN TO USE:**
- Understanding sector/industry diversification of a portfolio
- Identifying concentration risk in specific sectors or industries
- Checking long/short/net/gross exposure metrics
- Reviewing which tickers belong to which classification groups

**IMPORTANT:**
- Weights are decimal percentages (0.30 = 30%). Negative = short position.
- Concentration is the sum of weights in that group (can be negative for short-heavy groups).
- VaR 99% is the daily 1% worst-case loss contribution from that group at portfolio weights.
- Groups are sorted by absolute concentration (largest exposure first).

    Args:
        tickers: List of ticker symbols in the portfolio (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        weights: Decimal portfolio weights per ticker, same order as tickers.
            0.30 = 30% allocation. Negative = short. (e.g., [0.40, 0.35, 0.25])
        years_back: Number of years of historical data for VaR calculation (default 1)

    Returns:
        YAML-formatted classification breakdown:
        - exposures: net_exposure, gross_exposure, long_exposure, short_exposure
        - sector: {group_name: {concentration, var_99, tickers}}
        - industry: {group_name: {concentration, var_99, tickers}}
        - sub_industry: {group_name: {concentration, var_99, tickers}}

    Interpretation Guide:
        net_exposure: Sum of all weights. 1.0 = fully invested long. 0.0 = market-neutral.
        gross_exposure: Sum of absolute weights. Measures total capital deployed. 130/30 = 1.6.
        long_exposure: Sum of positive weights.
        short_exposure: Sum of absolute negative weights.
        concentration: Weight allocated to that group. 0.40 = 40% of portfolio.
        var_99: Daily 99% VaR for that group's contribution to portfolio risk.
            -0.02 means a 1% chance of losing 2%+ from that group on any given day.

    Examples:
        portfolio_classification(
            tickers=["AAPL", "MSFT", "JPM", "XOM", "PG"],
            weights=[0.25, 0.25, 0.20, 0.15, 0.15]
        )

        portfolio_classification(
            tickers=["AAPL", "TSLA", "JPM", "XOM"],
            weights=[0.40, -0.15, 0.35, 0.40],
            years_back=2
        )

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

        return success_response({
            "exposures": {
                "net_exposure": round(portfolio.net_exposure, 4),
                "gross_exposure": round(portfolio.gross_exposure, 4),
                "long_exposure": round(portfolio.long_exposure, 4),
                "short_exposure": round(portfolio.short_exposure, 4),
            },
            "sector": _format_group_metrics(portfolio.sector_metrics),
            "industry": _format_group_metrics(portfolio.industry_metrics),
            "sub_industry": _format_group_metrics(portfolio.sub_industry_metrics),
        })

    except Exception as e:
        return error_response(f"Failed to compute portfolio classification: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(portfolio_classification(
        tickers=["AAPL", "MSFT", "JPM", "XOM", "PG"],
        weights=[0.25, 0.25, 0.20, 0.15, 0.15],
        years_back=1,
    ))
