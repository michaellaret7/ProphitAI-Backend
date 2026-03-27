"""Analyst price target tools.

Provides tools for fetching analyst price target data including
consensus targets, ranges, and historical price target trends.
Supports batched multi-ticker calls.
"""

from typing import Literal

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_data.clients.fmp import FMP_API_DATA


# ================================
# --> Helper funcs
# ================================

def _fetch_price_target_for_ticker(
    fmp: FMP_API_DATA,
    ticker: str,
    data_type: str,
) -> dict:
    """Fetch and process price target data for a single ticker."""

    result = {}

    if data_type in ['consensus', 'both']:
        consensus_data = fmp.get_price_target_consensus(ticker)
        if consensus_data:
            if isinstance(consensus_data, list):
                consensus_data = consensus_data[0] if consensus_data else {}
            result['consensus'] = consensus_data

    if data_type in ['summary', 'both']:
        summary_data = fmp.get_price_target_summary(ticker)
        if summary_data:
            if isinstance(summary_data, list):
                summary_data = summary_data[0] if summary_data else {}
            if 'publishers' in summary_data:
                del summary_data['publishers']
            result['summary'] = summary_data

    # Reason: flatten result when only one type requested
    if data_type == 'consensus':
        result = result.get('consensus', {})
    elif data_type == 'summary':
        result = result.get('summary', {})

    return result


# ================================
# --> Tools
# ================================

@agent_tool(name="get_price_target_data", category="fundamentals")
def get_price_target_data(
    tickers: list[str],
    data_type: Literal['consensus', 'summary', 'both'] = 'consensus',
) -> str:
    """
    Get analyst price target data for one or more tickers including consensus targets,
    ranges, and historical trends.

    Provides comprehensive price target information from Wall Street analysts,
    helping understand market expectations for future stock price performance.

    **Data Types:**
    - consensus: Current analyst consensus with high/low/median targets
    - summary: Historical price target trends (last month/quarter/year/all-time)
    - both: Combined consensus and summary data

    **Consensus Data Includes:**
    - targetHigh: Highest analyst price target (most bullish)
    - targetLow: Lowest analyst price target (most bearish)
    - targetConsensus: Average consensus price target
    - targetMedian: Median price target (less affected by outliers)

    **Summary Data Includes:**
    - Price target counts and averages over different time periods
    - Analyst coverage breadth (number of analysts)
    - Historical trend analysis

    **Key Insights:**
    - Upside >20%: Current price well below consensus (potential buy signal)
    - Downside >10%: Current price above consensus (caution)
    - Narrow range: Strong analyst consensus on valuation
    - Wide range: High uncertainty or divergent views
    - Rising targets: Improving analyst sentiment
    - Falling targets: Deteriorating outlook

    Args:
        tickers: List of stock ticker symbols (e.g., ['AAPL', 'MSFT', 'TSLA'])
        data_type: Type of price target data to retrieve

    Returns:
        Price target data with consensus and/or summary information

    Examples:
        get_price_target_data(tickers=['AAPL', 'NVDA'], data_type='consensus')
        >>> {"success": True, "data": {"results": {"AAPL": {...}, "NVDA": {...}}, "errors": {}}}

    Raises:
        Exception: If data retrieval fails
    """
    tickers = [t.upper().strip() for t in tickers]

    results: dict = {}
    errors: dict = {}

    try:
        fmp = FMP_API_DATA()
    except Exception as e:
        return error_response(f"Failed to initialize FMP API: {str(e)}")

    for t in tickers:
        try:
            data = _fetch_price_target_for_ticker(fmp, t, data_type)
            if not data:
                errors[t] = f"No price target data found for {t}"
                continue
            results[t] = data
        except Exception as e:
            errors[t] = f"Failed to retrieve price target data for {t}: {str(e)}"

    return success_response({"results": results, "errors": errors})


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(get_price_target_data.tool)
