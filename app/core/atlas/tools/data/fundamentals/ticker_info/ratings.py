"""Analyst ratings and stock grades tools.

This module provides tools for fetching analyst ratings, upgrades/downgrades,
and fundamental quality scores for stocks.
"""

from typing import Optional
from datetime import datetime, timedelta
from app.core.atlas.tools.responses import success_response, error_response
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.tool_validator import ToolValidator
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.time_utils import get_current_utc_time
import pandas as pd
from app.utils.token_count import get_token_count

@log_simulation_data_range()
def get_stock_ratings(
    tickers: list[str],
    data_type: str = 'summary',
    days_back: int = 180,
    row_limit: int = 15,
    _simulation_date: Optional[datetime] = None
) -> str:
    """Get analyst ratings and stock grades for one or more tickers.

    Args:
        tickers: List of stock ticker symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        data_type: Type of rating data to retrieve:
                  - 'summary': Aggregate rating counts (buy/hold/sell distribution)
                  - 'individual': Individual analyst actions (upgrades/downgrades/maintains)
                  - 'scores': Fundamental quality scores and overall rating
                  - 'all': All three data types combined
        days_back: Number of days to look back for individual ratings (default 180)
        row_limit: Maximum number of individual rating records to return per ticker (default 15)
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
        YAML formatted string with rating data including:

        **Summary Data:**
        - analystRatingsStrongBuy: Number of Strong Buy ratings
        - analystRatingsBuy: Number of Buy ratings
        - analystRatingsHold: Number of Hold ratings
        - analystRatingsSell: Number of Sell ratings
        - analystRatingsStrongSell: Number of Strong Sell ratings

        **Individual Data:**
        - symbol: Stock ticker
        - date: Date of rating action
        - gradingCompany: Analyst firm name
        - previousGrade: Previous rating
        - newGrade: New rating
        - action: upgrade/downgrade/maintain/init

        **Scores Data:**
        - rating: Overall letter grade (A, B, C, D, F)
        - overallScore: Overall fundamental score
        - discountedCashFlowScore: DCF valuation score
        - returnOnEquityScore: ROE quality score
        - returnOnAssetsScore: ROA quality score
        - debtToEquityScore: Leverage score
        - priceToEarningsScore: P/E valuation score
        - priceToBookScore: P/B valuation score
    """
    # Validate inputs using ToolValidator
    v = ToolValidator()
    v.require_tickers('tickers', tickers)
    v.require_enum('data_type', data_type, ['summary', 'individual', 'scores', 'all'])
    v.require_numeric('days_back', days_back, min_val=1, max_val=730)
    v.require_numeric('row_limit', row_limit, min_val=1, max_val=200)

    if not v.is_valid():
        return v.error_response()

    # Get validated values (require_tickers already uppercases tickers)
    tickers = v.get('tickers')
    data_type = v.get('data_type')
    days_back = v.get('days_back')
    row_limit = v.get('row_limit')

    try:
        fmp = FMP_API_DATA()

        # Determine current date
        current_date = _simulation_date if _simulation_date else get_current_utc_time()
        cutoff_date = current_date - timedelta(days=days_back)

        # Structure to hold results: {ticker: {summary, individual, scores}}
        results_by_ticker = {ticker: {} for ticker in tickers}

        # Loop through each ticker and fetch data individually
        for ticker in tickers:
            # Fetch summary data (analyst rating counts)
            if data_type in ['summary', 'all']:
                summary_data = fmp.get_stock_grades_summary(ticker)
                if summary_data:
                    # Handle both list and dict responses
                    if isinstance(summary_data, list):
                        # Get the most recent summary
                        df = pd.DataFrame(summary_data)
                        if 'date' in df.columns:
                            df['date'] = pd.to_datetime(df['date'])

                            # Filter by simulation date if provided
                            if _simulation_date:
                                df = df[df['date'] <= _simulation_date]

                            if not df.empty:
                                # Sort by date and get most recent
                                df = df.sort_values('date', ascending=False)
                                summary_data = df.head(1).to_dict(orient='records')[0]
                                summary_data['date'] = str(summary_data['date'].date())
                            else:
                                summary_data = {}
                        else:
                            summary_data = summary_data[0] if summary_data else {}
                    results_by_ticker[ticker]['summary'] = summary_data
                else:
                    results_by_ticker[ticker]['summary'] = {}

            # Fetch individual analyst actions (upgrades/downgrades)
            if data_type in ['individual', 'all']:
                individual_data = fmp.get_stock_grades_individual(ticker, limit=10000)
                if individual_data:
                    df = pd.DataFrame(individual_data)

                    # Determine which date column is present
                    date_col = None
                    if 'date' in df.columns:
                        date_col = 'date'
                    elif 'publishedDate' in df.columns:
                        date_col = 'publishedDate'

                    if date_col:
                        # Parse dates and filter by date range
                        df[date_col] = pd.to_datetime(df[date_col])

                        # Filter by simulation date if provided
                        if _simulation_date:
                            df = df[df[date_col] <= _simulation_date]

                        # Filter by days_back
                        df = df[df[date_col] >= cutoff_date]

                        # Sort by date descending and limit
                        df = df.sort_values(date_col, ascending=False).head(row_limit)

                        # Convert dates to strings for JSON serialization
                        if not df.empty:
                            df[date_col] = df[date_col].dt.strftime('%Y-%m-%d')
                            results_by_ticker[ticker]['individual'] = df.to_dict(orient='records')
                        else:
                            results_by_ticker[ticker]['individual'] = []
                    else:
                        # No date column found, just limit rows
                        results_by_ticker[ticker]['individual'] = individual_data[:row_limit]
                else:
                    results_by_ticker[ticker]['individual'] = []

            # Fetch fundamental quality scores
            if data_type in ['scores', 'all']:
                scores_data = fmp.get_ratings_snapshot(ticker)
                if scores_data:
                    # Handle both list and dict responses
                    if isinstance(scores_data, list):
                        scores_data = scores_data[0] if scores_data else {}
                    results_by_ticker[ticker]['scores'] = scores_data
                else:
                    results_by_ticker[ticker]['scores'] = {}

        # Format final result based on data_type
        if len(tickers) == 1:
            # Single ticker - flatten structure for backward compatibility
            result = results_by_ticker[tickers[0]]

            # If only one type requested, flatten further
            if data_type == 'summary':
                result = result.get('summary', {})
            elif data_type == 'individual':
                result = result.get('individual', [])
            elif data_type == 'scores':
                result = result.get('scores', {})

            if not result or (isinstance(result, dict) and not result) or (isinstance(result, list) and len(result) == 0):
                return error_response(f"No rating data found for {tickers[0]}")
        else:
            # Multiple tickers - return dict keyed by ticker
            result = {}
            for ticker in tickers:
                ticker_result = results_by_ticker[ticker]

                # If only one type requested, flatten for each ticker
                if data_type == 'summary':
                    result[ticker] = ticker_result.get('summary', {})
                elif data_type == 'individual':
                    result[ticker] = ticker_result.get('individual', [])
                elif data_type == 'scores':
                    result[ticker] = ticker_result.get('scores', {})
                else:  # 'all'
                    result[ticker] = ticker_result

        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to retrieve rating data: {str(e)}")



# Tool Schema Constants
GET_STOCK_RATINGS_DESCRIPTION = (
    "Get comprehensive analyst ratings and stock grades for one or more tickers.\n\n"
    "This tool provides multiple perspectives on analyst sentiment and fundamental quality:\n"
    "- **Summary**: Current distribution of analyst ratings (buy/hold/sell counts)\n"
    "- **Individual**: Recent analyst actions (upgrades, downgrades, maintains)\n"
    "- **Scores**: Fundamental quality scores across multiple metrics\n\n"
    "**Data Types:**\n"
    "  - **summary**: Aggregate rating distribution (e.g., 15 Buy, 10 Hold, 2 Sell)\n"
    "  - **individual**: Recent analyst upgrade/downgrade actions with firm names\n"
    "  - **scores**: Fundamental scores (DCF, ROE, ROA, debt, P/E, P/B) + letter grade\n"
    "  - **all**: Complete dataset with all three data types\n\n"
    "**Summary Data:**\n"
    "  - Shows current analyst consensus (how many analysts rate it buy vs hold vs sell)\n"
    "  - Updated regularly as analysts revise ratings\n"
    "  - Useful for understanding overall Wall Street sentiment\n\n"
    "**Individual Data:**\n"
    "  - Recent analyst actions from specific firms\n"
    "  - Tracks upgrades (e.g., Hold → Buy), downgrades (Buy → Hold), maintains\n"
    "  - Shows which firms are bullish/bearish and why they changed\n"
    "  - Includes firm names (e.g., Morgan Stanley, Goldman Sachs)\n\n"
    "**Scores Data:**\n"
    "  - Overall letter grade: A (best) to F (worst)\n"
    "  - Component scores (1-5 scale) for:\n"
    "    • Valuation (DCF, P/E, P/B)\n"
    "    • Profitability (ROE, ROA)\n"
    "    • Financial health (Debt/Equity)\n"
    "  - Higher scores = better fundamental quality\n\n"
    "**Use Cases:**\n"
    "  - Analyst sentiment check: Is Wall Street bullish or bearish?\n"
    "  - Rating momentum: Are recent actions mostly upgrades or downgrades?\n"
    "  - Consensus strength: Wide agreement (all buy) vs divided (mixed ratings)\n"
    "  - Quality screening: Filter stocks by fundamental score\n"
    "  - Contrarian signals: Heavily sold stocks might be oversold\n"
    "  - Catalyst tracking: Identify which firms initiated coverage or changed ratings\n\n"
    "**Key Insights:**\n"
    "  - **High buy ratio**: Strong analyst confidence (potential tailwind)\n"
    "  - **Recent upgrades**: Improving sentiment (momentum building)\n"
    "  - **Recent downgrades**: Deteriorating outlook (caution)\n"
    "  - **High scores (A/B)**: Strong fundamentals (quality stock)\n"
    "  - **Low scores (D/F)**: Weak fundamentals (risky)\n"
    "  - **Mixed ratings**: Controversy/uncertainty (do more research)\n\n"
    "**Examples:**\n"
    "  get_stock_ratings(tickers=['AAPL'], data_type='summary')\n"
    "  get_stock_ratings(tickers=['TSLA'], data_type='individual', days_back=90)\n"
    "  get_stock_ratings(tickers=['NVDA'], data_type='scores')\n"
    "  get_stock_ratings(tickers=['MSFT'], data_type='all', days_back=180)\n"
    "  get_stock_ratings(tickers=['AAPL', 'MSFT', 'GOOGL'], data_type='summary')  # Multiple tickers"
)

GET_STOCK_RATINGS_PARAMETERS = {
    "type": "object",
    "properties": {
        "tickers": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "List of ticker symbols to get ratings for. Can be a single ticker or multiple tickers. "
                "For example: ['AAPL'], ['MSFT', 'GOOGL', 'NVDA'], etc."
            ),
            "minItems": 1,
            "maxItems": 50
        },
        "data_type": {
            "type": "string",
            "description": (
                "Type of rating data to retrieve:\n"
                "  - 'summary': Aggregate rating counts (buy/hold/sell distribution)\n"
                "  - 'individual': Recent analyst actions (upgrades/downgrades)\n"
                "  - 'scores': Fundamental quality scores and letter grade\n"
                "  - 'all': Complete dataset with all three types\n"
                "Default is 'summary'."
            ),
            "enum": ["summary", "individual", "scores", "all"],
            "default": "summary"
        },
        "days_back": {
            "type": "integer",
            "description": (
                "Number of days to look back for individual ratings. "
                "Only applies to 'individual' and 'all' data types. "
                "Default is 180 days (6 months). Max 730 days (2 years)."
            ),
            "default": 180,
            "minimum": 1,
            "maximum": 730
        },
        "row_limit": {
            "type": "integer",
            "description": (
                "Maximum number of individual rating records to return per ticker. "
                "Only applies to 'individual' and 'all' data types. "
                "Default is 15. Max 200."
            ),
            "default": 15,
            "minimum": 1,
            "maximum": 200
        },
    },
    "required": ["tickers"],
}

GET_STOCK_RATINGS_TOOL = {
    "name": "get_stock_ratings",
    "description": GET_STOCK_RATINGS_DESCRIPTION,
    "parameters": GET_STOCK_RATINGS_PARAMETERS,
    "function": get_stock_ratings,
}
