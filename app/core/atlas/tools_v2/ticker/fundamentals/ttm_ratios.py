"""TTM financial ratios tools.

Provides tools for fetching trailing twelve months (TTM) financial
ratios for companies, enabling current-state fundamental analysis.
"""

from app.core.atlas.tools_v2.decorator import agent_tool
from app.core.atlas.tools_v2.responses import success_response, error_response
from app.db.core.pull_fmp_data import FMP_API_DATA


# ================================
# --> Tools
# ================================

@agent_tool(name="get_ratios_ttm")
def get_ratios_ttm(
    ticker: str,
) -> str:
    """
    Get trailing twelve months (TTM) financial ratios for a ticker.

    TTM ratios provide a current snapshot of a company's financial health using
    the most recent 12 months of data, smoothing out seasonal variations.

    **Ratio Categories:**
    - Profitability: ROE, ROA, gross margin, operating margin, net profit margin
    - Liquidity: Current ratio, quick ratio, cash ratio
    - Leverage: Debt-to-equity, debt-to-assets, interest coverage
    - Efficiency: Asset turnover, inventory turnover, receivables turnover
    - Valuation: P/E, P/B, P/S, EV/EBITDA, dividend yield

    **Use Cases:**
    - Quick financial health assessment
    - Peer comparison across key metrics
    - Screening for value or quality characteristics
    - Identifying red flags (low coverage, high leverage)

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'KO')

    Returns:
        TTM financial ratios including profitability, liquidity, leverage,
        efficiency, and valuation metrics

    Examples:
        get_ratios_ttm(ticker='AAPL')
        >>> {"success": True, "data": [{"peRatioTTM": 28.5, "returnOnEquityTTM": 1.47, ...}]}

    Raises:
        Exception: If ticker is invalid or no data found
    """
    fmp = FMP_API_DATA()
    data = fmp.get_ratios_ttm(ticker.upper())

    if data is None or len(data) == 0:
        return error_response(f"No TTM ratios found for {ticker}")

    if isinstance(data, list) and len(data) > 0:
        data[0] = {k: round(v, 4) if isinstance(v, (int, float)) else v for k, v in data[0].items()}

    return success_response(data)


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(get_ratios_ttm.tool)
