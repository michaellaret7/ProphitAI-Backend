"""Earnings transcript tools for corporate disclosures analysis."""

from typing import Optional
from datetime import datetime
from app.repositories.transcripts_data import get_earnings_transcripts
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from app.utils.decorators.tool_validation import validate_ticker_arg, validate_numeric_arg
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.time_utils import get_current_utc_time
from app.db.core.pull_fmp_data import FMP_API_DATA


def calculate_quarter(month: int) -> int:
    """Calculate quarter from month.

    Args:
        month: Month number (1-12)

    Returns:
        Quarter number (1-4)
    """
    # Reason: Convert month to quarter (Q1: Jan-Mar, Q2: Apr-Jun, Q3: Jul-Sep, Q4: Oct-Dec)
    return (month - 1) // 3 + 1


def generate_quarters_back(year: int, quarter: int, quarters_back: int) -> list[tuple[int, int]]:
    """Generate list of (year, quarter) tuples going back from current quarter.

    Args:
        year: Starting year
        quarter: Starting quarter (1-4)
        quarters_back: Number of quarters to go back

    Returns:
        List of (year, quarter) tuples in reverse chronological order
    """
    quarters = []
    current_year = year
    current_quarter = quarter

    for _ in range(quarters_back):
        quarters.append((current_year, current_quarter))

        # Move to previous quarter
        current_quarter -= 1
        if current_quarter < 1:
            current_quarter = 4
            current_year -= 1

    return quarters


@validate_ticker_arg()
@validate_numeric_arg("quarters_back", min_value=1, max_value=40)
@log_simulation_data_range()
def get_earnings_call_transcripts(
    ticker: str,
    quarters_back: int = 4,
    _simulation_date: Optional[datetime] = None
) -> str:
    """Get earnings call transcripts for a ticker on a quarterly basis.

    Args:
        ticker: Stock ticker symbol
        quarters_back: Number of quarters back to fetch transcripts (default: 4, max: 40)
                      quarters_back=1 returns only the latest transcript
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
        JSON formatted string with earnings transcript data including:
        - Quarter and year information
        - Transcript content
        - Date of earnings call
    """
    try:
        # Use simulation date if provided, otherwise current UTC time
        current_date = _simulation_date if _simulation_date else get_current_utc_time()
        current_year = current_date.year
        current_month = current_date.month

        # Calculate current quarter from month
        current_quarter = calculate_quarter(current_month)

        # Generate list of (year, quarter) tuples going back
        quarters_to_fetch = generate_quarters_back(current_year, current_quarter, quarters_back)

        # Fetch transcripts for each quarter
        fmp = FMP_API_DATA()
        transcripts = []

        for year, quarter in quarters_to_fetch:
            transcript_data = fmp.get_earnings_transcript(ticker, year, quarter)

            if transcript_data:  # Only add if transcript exists
                transcripts.append({
                    "year": year,
                    "quarter": quarter,
                    "data": transcript_data
                })

        result = {
            "ticker": ticker.upper(),
            "quarters_requested": quarters_back,
            "transcripts_found": len(transcripts),
            "transcripts": transcripts
        }

        return success_response(result)
    except Exception as e:
        return error_response(e)


# Tool Schema Constants
GET_EARNINGS_TRANSCRIPTS_DESCRIPTION = (
    "Fetch earnings call transcripts for a stock ticker on a quarterly basis. "
    "Returns complete transcripts from quarterly earnings calls including management discussion, "
    "Q&A sessions, and forward guidance. "
    "\n\n**IMPORTANT: quarters_back=1 returns ONLY the latest/most recent earnings transcript**"
    "\n\n**Use Cases:**"
    "\n  - Analyze management commentary and strategic direction"
    "\n  - Track guidance changes over time"
    "\n  - Identify recurring themes in Q&A sessions"
    "\n  - Assess management confidence and tone"
    "\n  - Extract forward-looking statements"
    "\n  - Compare management commentary to actual results"
    "\n  - Get latest transcript only: quarters_back=1"
    "\n\n**Data Returned:**"
    "\n  - Quarter and fiscal year information"
    "\n  - Full transcript content (prepared remarks + Q&A)"
    "\n  - Earnings call date"
    "\n  - Participant information (executives, analysts)"
    "\n\n**Quarterly Basis:**"
    "\n  - quarters_back=1: Latest transcript only (most recent earnings call)"
    "\n  - quarters_back=4: Last 4 quarters (1 year)"
    "\n  - quarters_back=8: Last 8 quarters (2 years)"
    "\n  - quarters_back=12: Last 12 quarters (3 years)"
    "\n\n**Examples:**"
    "\n  get_earnings_call_transcripts(ticker='AAPL', quarters_back=1)  # Latest only"
    "\n  get_earnings_call_transcripts(ticker='MSFT', quarters_back=4)  # Last year"
    "\n  get_earnings_call_transcripts(ticker='GOOGL', quarters_back=8)  # Last 2 years"
)

GET_EARNINGS_TRANSCRIPTS_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')",
        },
        "quarters_back": {
            "type": "integer",
            "description": (
                "Number of quarters of transcripts to retrieve. "
                "quarters_back=1 returns ONLY the latest transcript. "
                "Default is 4 quarters (1 year). Maximum is 40 quarters (10 years)."
            ),
            "default": 4,
            "minimum": 1,
            "maximum": 40
        }
    },
    "required": ["ticker"],
    "additionalProperties": False
}

GET_EARNINGS_TRANSCRIPTS_TOOL = {
    "name": "get_earnings_call_transcripts",
    "description": GET_EARNINGS_TRANSCRIPTS_DESCRIPTION,
    "parameters": GET_EARNINGS_TRANSCRIPTS_PARAMETERS,
    "function": get_earnings_call_transcripts,
}