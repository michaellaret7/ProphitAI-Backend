"""Controllers for analyst estimates and earnings endpoints."""

import asyncio
from typing import Dict, Any

from app.api.response_envelope import ok_envelope
from app.utils.decorators.api_decorators import handle_controller_errors
from app.db.core.pull_fmp_data import FMP_API_DATA


def _calculate_previous_quarters(year: int, quarter: int, quarters_back: int) -> list[tuple[int, int]]:
    """
    Calculate the previous N quarters from a given year and quarter.

    Args:
        year: Starting year
        quarter: Starting quarter (1-4)
        quarters_back: Number of quarters to go back (including current)

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


@handle_controller_errors
async def get_analyst_estimates_controller(
    ticker: str,
    periods_back: int = None,
    period: str = 'quarter',
) -> Dict[str, Any]:
    """
    Controller to handle analyst estimates data retrieval for a ticker
    """
    # Delegate to repository
    fmp = FMP_API_DATA()
    # Reason: Map periods_back to limit parameter for FMP API
    limit = periods_back if periods_back else 1000
    data = await asyncio.to_thread(fmp.get_analyst_estimates, ticker, period=period, page=0, limit=limit)

    # Handle None response
    if data is None:
        return ok_envelope(
            message=f"No analyst estimates data found for {ticker}",
            kind="fundamentals#analystEstimates",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/analyst-estimates",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload=[],
        )

    return ok_envelope(
        message="Analyst estimates retrieved successfully",
        kind="fundamentals#analystEstimates",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/analyst-estimates",
        counts={"totalItems": len(data) if isinstance(data, list) else 0, "currentItemCount": len(data) if isinstance(data, list) else 0},
        payload=data,
    )


@handle_controller_errors
async def get_earnings_calls_transcripts_controller(
    ticker: str,
    year: int,
    quarter: int,
    quarters_back: int = 1,
) -> Dict[str, Any]:
    """
    Controller to handle earnings calls transcripts data retrieval for a ticker

    Args:
        ticker: Stock ticker symbol
        year: Starting year
        quarter: Starting quarter (1-4)
        quarters_back: Number of quarters to fetch (default: 1, max: 20)

    Returns:
        Earnings transcripts for the specified quarters
    """
    fmp = FMP_API_DATA()

    # Calculate quarters to fetch
    quarters_to_fetch = _calculate_previous_quarters(year, quarter, quarters_back)

    # Fetch transcripts in parallel for multiple quarters
    async def fetch_transcript(y: int, q: int) -> dict:
        """Fetch a single transcript and add metadata"""
        data = await asyncio.to_thread(fmp.get_earnings_transcript, ticker, y, q)
        return {
            "year": y,
            "quarter": q,
            "data": data if data else None
        }

    # Fetch all transcripts concurrently
    transcripts = await asyncio.gather(*[
        fetch_transcript(y, q) for y, q in quarters_to_fetch
    ])

    # Filter out None results and structure the response
    valid_transcripts = [t for t in transcripts if t["data"] is not None]

    if not valid_transcripts:
        return ok_envelope(
            message=f"No earnings calls transcripts data found for {ticker}",
            kind="fundamentals#earningsCallsTranscripts",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/earnings-calls-transcripts?year={year}&quarter={quarter}&quarters_back={quarters_back}",
            counts={"totalItems": 0, "currentItemCount": 0},
            payload=[],
        )

    # If single quarter, return the data directly (backwards compatible)
    if quarters_back == 1:
        return ok_envelope(
            message="Earnings calls transcripts retrieved successfully",
            kind="fundamentals#earningsCallsTranscripts",
            resource_id=ticker,
            self_link=f"/api/fundamentals/{ticker}/earnings-calls-transcripts?year={year}&quarter={quarter}",
            counts={"totalItems": 1, "currentItemCount": 1},
            payload=valid_transcripts[0]["data"],
        )

    # For multiple quarters, return structured array
    return ok_envelope(
        message=f"Earnings calls transcripts retrieved successfully for {len(valid_transcripts)} quarters",
        kind="fundamentals#earningsCallsTranscripts",
        resource_id=ticker,
        self_link=f"/api/fundamentals/{ticker}/earnings-calls-transcripts?year={year}&quarter={quarter}&quarters_back={quarters_back}",
        counts={"totalItems": len(valid_transcripts), "currentItemCount": len(valid_transcripts)},
        payload=valid_transcripts,
    )
