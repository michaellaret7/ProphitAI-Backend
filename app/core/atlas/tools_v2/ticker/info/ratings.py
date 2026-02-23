"""Analyst ratings and stock grades tools.

Provides tools for fetching analyst ratings, upgrades/downgrades,
and fundamental quality scores for stocks.
"""

from typing import Annotated, Literal
from datetime import timedelta

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.time_utils import get_current_utc_time
import pandas as pd


# ================================
# --> Tools
# ================================

@agent_tool(name="get_stock_ratings")
def get_stock_ratings(
    tickers: list[str],
    data_type: Literal['summary', 'individual', 'scores', 'all'] = 'summary',
    days_back: Annotated[int, Param(min_val=1, max_val=730)] = 180,
    row_limit: Annotated[int, Param(min_val=1, max_val=200)] = 15,
) -> str:
    """
    Get comprehensive analyst ratings and stock grades for one or more tickers.

    Provides multiple perspectives on analyst sentiment and fundamental quality.

    **Data Types:**
    - summary: Current distribution of analyst ratings (buy/hold/sell counts)
    - individual: Recent analyst actions (upgrades, downgrades, maintains) with firm names
    - scores: Fundamental quality scores (DCF, ROE, ROA, debt, P/E, P/B) + letter grade
    - all: Complete dataset with all three data types

    **Use Cases:**
    - Analyst sentiment check: Is Wall Street bullish or bearish?
    - Rating momentum: Are recent actions mostly upgrades or downgrades?
    - Consensus strength: Wide agreement (all buy) vs divided (mixed ratings)
    - Quality screening: Filter stocks by fundamental score
    - Catalyst tracking: Identify which firms initiated coverage or changed ratings

    **Key Insights:**
    - High buy ratio: Strong analyst confidence (potential tailwind)
    - Recent upgrades: Improving sentiment (momentum building)
    - Recent downgrades: Deteriorating outlook (caution)
    - High scores (A/B): Strong fundamentals (quality stock)
    - Low scores (D/F): Weak fundamentals (risky)

    Args:
        tickers: List of stock ticker symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        data_type: Type of rating data to retrieve
        days_back: Number of days to look back for individual ratings.
            Only applies to 'individual' and 'all' data types.
        row_limit: Maximum number of individual rating records per ticker.
            Only applies to 'individual' and 'all' data types.

    Returns:
        Rating data structured by ticker. Single ticker returns flattened data,
        multiple tickers return a dict keyed by ticker symbol.

    Examples:
        get_stock_ratings(tickers=['AAPL'], data_type='summary')
        >>> {"success": True, "data": {"analystRatingsBuy": 15, "analystRatingsHold": 10, ...}}

        get_stock_ratings(tickers=['TSLA'], data_type='individual', days_back=90)
        >>> {"success": True, "data": [{"gradingCompany": "Morgan Stanley", "action": "upgrade", ...}]}

        get_stock_ratings(tickers=['AAPL', 'MSFT'], data_type='scores')
        >>> {"success": True, "data": {"AAPL": {"rating": "A", ...}, "MSFT": {"rating": "A", ...}}}

    Raises:
        Exception: If tickers list is empty or data retrieval fails
    """
    tickers = [t.upper() for t in tickers]
    current_date = get_current_utc_time()
    cutoff_date = current_date - timedelta(days=days_back)

    try:
        fmp = FMP_API_DATA()
        results_by_ticker = {ticker: {} for ticker in tickers}

        for ticker in tickers:
            # Reason: fetch summary data (analyst rating counts)
            if data_type in ['summary', 'all']:
                summary_data = fmp.get_stock_grades_summary(ticker)
                if summary_data:
                    if isinstance(summary_data, list):
                        df = pd.DataFrame(summary_data)
                        if 'date' in df.columns:
                            df['date'] = pd.to_datetime(df['date'])
                            if not df.empty:
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

            # Reason: fetch individual analyst actions (upgrades/downgrades)
            if data_type in ['individual', 'all']:
                individual_data = fmp.get_stock_grades_individual(ticker, limit=10000)
                if individual_data:
                    df = pd.DataFrame(individual_data)
                    date_col = None
                    if 'date' in df.columns:
                        date_col = 'date'
                    elif 'publishedDate' in df.columns:
                        date_col = 'publishedDate'

                    if date_col:
                        df[date_col] = pd.to_datetime(df[date_col])
                        df = df[df[date_col] >= cutoff_date]
                        df = df.sort_values(date_col, ascending=False).head(row_limit)
                        if not df.empty:
                            df[date_col] = df[date_col].dt.strftime('%Y-%m-%d')
                            results_by_ticker[ticker]['individual'] = df.to_dict(orient='records')
                        else:
                            results_by_ticker[ticker]['individual'] = []
                    else:
                        results_by_ticker[ticker]['individual'] = individual_data[:row_limit]
                else:
                    results_by_ticker[ticker]['individual'] = []

            # Reason: fetch fundamental quality scores
            if data_type in ['scores', 'all']:
                scores_data = fmp.get_ratings_snapshot(ticker)
                if scores_data:
                    if isinstance(scores_data, list):
                        scores_data = scores_data[0] if scores_data else {}
                    results_by_ticker[ticker]['scores'] = scores_data
                else:
                    results_by_ticker[ticker]['scores'] = {}

        # Reason: flatten structure for single ticker, dict for multiple
        if len(tickers) == 1:
            result = results_by_ticker[tickers[0]]
            if data_type == 'summary':
                result = result.get('summary', {})
            elif data_type == 'individual':
                result = result.get('individual', [])
            elif data_type == 'scores':
                result = result.get('scores', {})

            if not result or (isinstance(result, dict) and not result) or (isinstance(result, list) and len(result) == 0):
                return error_response(f"No rating data found for {tickers[0]}")
        else:
            result = {}
            for ticker in tickers:
                ticker_result = results_by_ticker[ticker]
                if data_type == 'summary':
                    result[ticker] = ticker_result.get('summary', {})
                elif data_type == 'individual':
                    result[ticker] = ticker_result.get('individual', [])
                elif data_type == 'scores':
                    result[ticker] = ticker_result.get('scores', {})
                else:
                    result[ticker] = ticker_result

        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to retrieve rating data: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(get_stock_ratings.tool)
