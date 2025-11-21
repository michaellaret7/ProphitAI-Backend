"""Analyst price target tools.

This module provides tools for fetching analyst price target data including
consensus targets, ranges, and historical price target trends.
"""

from typing import Optional
from datetime import datetime
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.tool_validator import ToolValidator
from app.db.core.pull_fmp_data import FMP_API_DATA

@log_simulation_data_range()
def get_price_target_data(ticker: str, data_type: str = 'consensus', _simulation_date: Optional[datetime] = None) -> str:
    """Get analyst price target data for a ticker.

    Args:
        ticker: Stock ticker symbol
        data_type: Type of price target data to retrieve:
                  - 'consensus': Current consensus price target with high/low/median
                  - 'summary': Historical price target trends over time periods
                  - 'both': Both consensus and summary data
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
        YAML formatted string with price target data including:

        **Consensus Data:**
        - targetHigh: Highest analyst price target
        - targetLow: Lowest analyst price target
        - targetConsensus: Average consensus price target
        - targetMedian: Median price target

        **Summary Data:**
        - lastMonthCount: Number of price targets in last month
        - lastMonthAvgPriceTarget: Average target from last month
        - lastQuarterCount: Number of price targets in last quarter
        - lastQuarterAvgPriceTarget: Average target from last quarter
        - lastYearCount: Number of price targets in last year
        - lastYearAvgPriceTarget: Average target from last year
        - allTimeCount: Total number of price targets ever
        - allTimeAvgPriceTarget: All-time average price target
        - publishers: List of analyst firms providing targets
    """
    # Validate inputs using ToolValidator
    v = ToolValidator()
    v.require_ticker('ticker', ticker)
    v.require_enum('data_type', data_type, ['consensus', 'summary', 'both'])

    if not v.is_valid():
        return v.error_response()

    # Get validated values
    ticker = v.get('ticker')
    data_type = v.get('data_type')

    try:
        fmp = FMP_API_DATA()
        result = {}

        # Fetch consensus data
        if data_type in ['consensus', 'both']:
            consensus_data = fmp.get_price_target_consensus(ticker)
            if consensus_data:
                # Handle both list and dict responses
                if isinstance(consensus_data, list):
                    consensus_data = consensus_data[0] if consensus_data else {}
                result['consensus'] = consensus_data

        # Fetch summary data
        if data_type in ['summary', 'both']:
            summary_data = fmp.get_price_target_summary(ticker)
            if summary_data:
                # Handle both list and dict responses
                if isinstance(summary_data, list):
                    summary_data = summary_data[0] if summary_data else {}

                # Remove publishers field to reduce token usage
                if 'publishers' in summary_data:
                    del summary_data['publishers']

                result['summary'] = summary_data

        # If only one type requested, flatten the result
        if data_type == 'consensus':
            result = result.get('consensus', {})
        elif data_type == 'summary':
            result = result.get('summary', {})

        if not result:
            return error_response(f"No price target data found for {ticker}")

        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to retrieve price target data: {str(e)}")

if __name__ == "__main__":
    print(get_price_target_data(ticker='AAPL', data_type='both'))

# Tool Schema Constants
GET_PRICE_TARGET_DATA_DESCRIPTION = (
    "Get analyst price target data for a ticker including consensus targets, ranges, and historical trends.\n\n"
    "This tool provides comprehensive price target information from Wall Street analysts, helping you "
    "understand market expectations for future stock price performance.\n\n"
    "**Data Types:**\n"
    "  - **consensus**: Current analyst consensus with high/low/median targets\n"
    "  - **summary**: Historical price target trends (last month/quarter/year/all-time)\n"
    "  - **both**: Combined consensus and summary data\n\n"
    "**Consensus Data Includes:**\n"
    "  - targetHigh: Highest analyst price target (most bullish)\n"
    "  - targetLow: Lowest analyst price target (most bearish)\n"
    "  - targetConsensus: Average consensus price target\n"
    "  - targetMedian: Median price target (less affected by outliers)\n\n"
    "**Summary Data Includes:**\n"
    "  - Price target counts and averages over different time periods\n"
    "  - Analyst coverage breadth (number of analysts)\n"
    "  - Top analyst firms providing coverage\n"
    "  - Historical trend analysis\n\n"
    "**Use Cases:**\n"
    "  - Valuation check: Compare current price to consensus target\n"
    "  - Upside potential: Calculate % upside to target consensus\n"
    "  - Analyst sentiment: Wide range (high-low) indicates disagreement\n"
    "  - Coverage trends: Increasing analyst count = rising interest\n"
    "  - Target revisions: Compare recent vs historical targets\n\n"
    "**Key Insights:**\n"
    "  - **Upside >20%**: Current price well below consensus (potential buy signal)\n"
    "  - **Downside >10%**: Current price above consensus (caution)\n"
    "  - **Narrow range**: Strong analyst consensus on valuation\n"
    "  - **Wide range**: High uncertainty or divergent views\n"
    "  - **Rising targets**: Improving analyst sentiment\n"
    "  - **Falling targets**: Deteriorating outlook\n\n"
    "**Examples:**\n"
    "  get_price_target_data(ticker='AAPL', data_type='consensus')\n"
    "  get_price_target_data(ticker='TSLA', data_type='summary')\n"
    "  get_price_target_data(ticker='NVDA', data_type='both')"
)

GET_PRICE_TARGET_DATA_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "The ticker symbol to get price target data for. For example, 'AAPL', 'MSFT', 'GOOGL', etc.",
        },
        "data_type": {
            "type": "string",
            "description": (
                "Type of price target data to retrieve:\n"
                "  - 'consensus': Current consensus with high/low/median targets\n"
                "  - 'summary': Historical price target trends over time\n"
                "  - 'both': Complete dataset with consensus and summary\n"
                "Default is 'consensus'."
            ),
            "enum": ["consensus", "summary", "both"],
            "default": "consensus"
        },
    },
    "required": ["ticker"],
}

GET_PRICE_TARGET_DATA_TOOL = {
    "name": "get_price_target_data",
    "description": GET_PRICE_TARGET_DATA_DESCRIPTION,
    "parameters": GET_PRICE_TARGET_DATA_PARAMETERS,
    "function": get_price_target_data,
}
