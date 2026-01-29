"""Mergers and acquisitions news tools."""

from app.core.atlas.tools.responses import success_response, error_response
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.tool_validator import ToolValidator
from app.utils.time_utils import get_current_utc_time
from app.db.core.pull_fmp_data import FMP_API_DATA
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
import tiktoken

def _count_tokens(text: str) -> int:
    """Count the number of tokens in a string using tiktoken."""
    return len(tiktoken.encoding_for_model("gpt-4o").encode(text))

def _deduplicate_ma_data(data: List[Dict]) -> List[Dict]:
    """
    Helper function to deduplicate M&A transaction data.

    FMP API returns duplicate records when a company has multiple ticker symbols
    (e.g., HBAN, HBANP, HBANN for different share classes). This function removes
    duplicates by keeping only one record per unique transaction, prioritizing
    the base ticker symbol (shortest symbol).

    Args:
        data: List of M&A transaction dictionaries from FMP API

    Returns:
        Deduplicated list of M&A transactions
    """
    if not data:
        return []

    df = pd.DataFrame(data)

    # Sort by symbol length to prioritize base ticker (e.g., HBAN over HBANP)
    df['_symbol_len'] = df['symbol'].str.len()
    df = df.sort_values('_symbol_len')

    # Drop duplicates based on unique transaction identifiers
    df = df.drop_duplicates(
        subset=['cik', 'targetedCik', 'transactionDate', 'acceptedDate'],
        keep='first'
    )

    # Remove temporary column
    df = df.drop(columns=['_symbol_len'])

    return df.to_dict('records')


@log_simulation_data_range()
def get_mergers_acquisitions(
    row_limit: int = 200,
    days_back: int = 365,
    _simulation_date: Optional[datetime] = None
):
    """
    Get latest mergers and acquisitions data from FMP with automatic deduplication.

    Args:
        row_limit: Maximum number of results to return (max 1000)
        days_back: Number of days to look back from today (or simulation date). Default 365 days.
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
        Success response with deduplicated M&A transactions or error response
    """
    # Validate inputs using ToolValidator
    v = ToolValidator()
    v.require_numeric('row_limit', row_limit, min_val=1, max_val=1000)
    v.require_numeric('days_back', days_back, min_val=1, max_val=3650)

    if not v.is_valid():
        return v.error_response()

    # Get validated values
    row_limit = v.get('row_limit')
    days_back = v.get('days_back')

    try:
        # Determine "today" - use simulation date if provided, otherwise current UTC time
        to_date = _simulation_date if _simulation_date else get_current_utc_time()

        # Calculate from_date as to_date minus days_back
        from_date = to_date - timedelta(days=days_back)

        fmp_api = FMP_API_DATA()
        data = fmp_api.get_mergers_acquisitions_latest(page=0, limit=1000)

        if data is None:
            return error_response("Failed to retrieve M&A data from FMP API")

        if not isinstance(data, list):
            return error_response("Invalid data format received from FMP API")

        # Reason: Deduplicate M&A records using helper function
        deduplicated_data = _deduplicate_ma_data(data)

        df = pd.DataFrame(deduplicated_data)

        # Convert transactionDate to datetime for filtering
        df['transactionDate'] = pd.to_datetime(df['transactionDate'])

        # Filter by date range (from_date to to_date)
        df = df[(df['transactionDate'] >= from_date) & (df['transactionDate'] <= to_date)]

        # Sort by date descending (most recent first)
        df = df.sort_values('transactionDate', ascending=False)
        df = df.reset_index(drop=True)

        df.drop(columns=['acceptedDate', 'link', 'cik', 'targetedCik'], inplace=True)
        df.rename(columns={'targetedCompanyName': 'acquiredCompanyName', 'targetedSymbol': 'acquiredCompanySymbol'}, inplace=True)
        df = df.head(row_limit)

        # Format date to string to avoid Timestamp object serialization issues
        df['transactionDate'] = df['transactionDate'].dt.strftime('%Y-%m-%d')

        results = df.to_dict(orient='records')

        return success_response(results)

    except Exception as e:
        return error_response(f"Error retrieving M&A data: {str(e)}")

# Tool Schema Constants
GET_MERGERS_ACQUISITIONS_DESCRIPTION = (
    "Fetch the latest mergers and acquisitions (M&A) transactions. "
    "Returns a list of M&A deals including acquired company, acquiring company, transaction date, "
    "and other details. Automatically deduplicates multiple share class entries. "
    "\n\n**Data Fields:**"
    "\n  - symbol: Acquiring company ticker"
    "\n  - name: Acquiring company name"
    "\n  - acquiredCompanySymbol: Target company ticker"
    "\n  - acquiredCompanyName: Target company name"
    "\n  - transactionDate: Date of the transaction"
    "\n  - price: Transaction price (if disclosed)"
    "\n\n**Use Cases:**"
    "\n  - Tracking recent M&A activity"
    "\n  - Identifying consolidation trends in sectors"
    "\n  - Finding details on specific recent deals"
    "\n\n**Examples:**"
    "\n  get_mergers_acquisitions(row_limit=50, days_back=180)"
    "\n  get_mergers_acquisitions(row_limit=100, days_back=730)  # Last 2 years"
)

GET_MERGERS_ACQUISITIONS_PARAMETERS = {
    "type": "object",
    "properties": {
        "row_limit": {
            "type": "integer",
            "description": (
                "Maximum number of M&A transactions to return (max 1000). "
                "Default is 200."
            ),
            "default": 200
        },
        "days_back": {
            "type": "integer",
            "description": (
                "Number of days to look back from today. "
                "Range: 1-3650 days. Default is 365 days (1 year)."
            ),
            "default": 365
        }
    },
    "additionalProperties": False
}

GET_MERGERS_ACQUISITIONS_TOOL = {
    "name": "get_mergers_acquisitions",
    "description": GET_MERGERS_ACQUISITIONS_DESCRIPTION,
    "parameters": GET_MERGERS_ACQUISITIONS_PARAMETERS,
    "function": get_mergers_acquisitions,
}
