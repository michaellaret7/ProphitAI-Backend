"""Analyst price target tools.

Provides tools for fetching analyst price target data including
consensus targets, ranges, and historical price target trends.
"""

from typing import Literal

from app.core.atlas.tools_v2.decorator import agent_tool
from app.core.atlas.tools_v2.responses import success_response, error_response
from app.db.core.pull_fmp_data import FMP_API_DATA


# ================================
# --> Tools
# ================================

@agent_tool(name="get_price_target_data")
def get_price_target_data(
    ticker: str,
    data_type: Literal['consensus', 'summary', 'both'] = 'consensus',
) -> str:
    """
    Get analyst price target data for a ticker including consensus targets,
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
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'TSLA')
        data_type: Type of price target data to retrieve

    Returns:
        Price target data with consensus and/or summary information

    Examples:
        get_price_target_data(ticker='AAPL', data_type='consensus')
        >>> {"success": True, "data": {"targetHigh": 250, "targetLow": 180, "targetConsensus": 215, ...}}

        get_price_target_data(ticker='NVDA', data_type='both')
        >>> {"success": True, "data": {"consensus": {...}, "summary": {...}}}

    Raises:
        Exception: If ticker is invalid or no data found
    """
    ticker = ticker.upper()

    try:
        fmp = FMP_API_DATA()
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

        if not result:
            return error_response(f"No price target data found for {ticker}")

        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to retrieve price target data for {ticker}: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(get_price_target_data.tool)
