"""
Earnings Call Search Tool - Search earnings call transcripts.

Uses hybrid search (semantic + keyword) over earnings call transcripts
to find information about company guidance, revenue, margins, and outlook.
"""

import re
from typing import Optional

from app.core.atlas.tools.responses import success_response, error_response
from app.core.foundry.retrieval import HybridSearch
from app.core.foundry.models.vector import QueryResult


# Regex pattern for YYYYQ# format (e.g., "2025Q4")
FISCAL_QUARTER_FULL_PATTERN = re.compile(r"^\d{4}Q[1-4]$")


# ==============================================================================
# TOOL FUNCTION
# ==============================================================================

def earnings_call_search(
    query: str,
    top_k: int = 5,
    ticker: Optional[str] = None,
    tickers: Optional[list[str]] = None,
    fiscal_year: Optional[int] = None,
    fiscal_quarter: Optional[str] = None,
    _simulation_date: Optional[str] = None,
) -> str:
    """
    Search earnings call transcripts using hybrid search.

    Searches over earnings call transcripts to find information about company
    performance, revenue guidance, margins, outlook, and management commentary.

    Args:
        query: Search query - natural language question or keywords about earnings/company topics
        top_k: Number of results to return (default: 5, max: 25)
        ticker: Filter by single ticker symbol (e.g., "AAPL")
        tickers: Filter by multiple ticker symbols (e.g., ["AAPL", "MSFT", "GOOGL"])
        fiscal_year: Filter by fiscal year (e.g., 2024, 2025)
        fiscal_quarter: Filter by fiscal quarter. Accepts:
            - Short format: "Q1", "Q2", "Q3", "Q4" (requires fiscal_year to combine into YYYYQ#)
            - Full format: "2025Q4" (passed through as-is)
        _simulation_date: Injected by agent framework (not used)

    Returns:
        str: YAML-formatted search results with:
            - 'success' (bool): Whether search succeeded
            - 'data' (dict): Contains 'results' list with text and metadata
            - 'error' (str): Error message when unsuccessful
    """
    # Validate query
    if not query or not isinstance(query, str):
        return error_response("Query is required and must be a non-empty string")

    query = query.strip()
    if not query:
        return error_response("Query cannot be empty or whitespace only")

    # Validate top_k
    if not isinstance(top_k, int) or top_k < 1:
        return error_response("top_k must be a positive integer")
    top_k = min(top_k, 25)

    # Process and validate fiscal_quarter
    normalized_quarter: Optional[str] = None
    if fiscal_quarter:
        fiscal_quarter = fiscal_quarter.upper()

        # Check if already in full format (e.g., "2025Q4")
        if FISCAL_QUARTER_FULL_PATTERN.match(fiscal_quarter):
            normalized_quarter = fiscal_quarter
        # Check if in short format (e.g., "Q4")
        elif fiscal_quarter in ["Q1", "Q2", "Q3", "Q4"]:
            if fiscal_year:
                # Combine year and quarter into YYYYQ# format
                normalized_quarter = f"{fiscal_year}{fiscal_quarter}"
            else:
                return error_response(
                    f"fiscal_year is required when using short quarter format '{fiscal_quarter}'. "
                    "Either provide fiscal_year or use full format like '2025Q4'."
                )
        else:
            return error_response(
                f"Invalid fiscal_quarter '{fiscal_quarter}'. "
                "Must be Q1-Q4 (with fiscal_year) or full format like '2025Q4'."
            )

    # Build filters
    filters: dict = {}
    if ticker:
        filters["ticker"] = ticker.upper()
    elif tickers:  # Use tickers only if ticker not provided
        filters["ticker"] = [t.upper() for t in tickers]
    if normalized_quarter:
        filters["fiscal_quarter"] = normalized_quarter

    try:
        searcher = HybridSearch(use_rerank=True)

        results: list[QueryResult] = searcher.search(
            query=query,
            top_k=top_k,
            namespace="earnings_calls",
            **filters,
        )

        # Format results for agent consumption
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "score": round(result.score, 4),
                "text": result.metadata.get("text", ""),
                "ticker": result.metadata.get("ticker"),
                "fiscal_year": result.metadata.get("fiscal_year"),
                "fiscal_quarter": result.metadata.get("fiscal_quarter"),
                "chunk_id": result.metadata.get("chunk_id"),
            })

        return success_response({
            "query": query,
            "num_results": len(formatted_results),
            "filters_applied": filters if filters else None,
            "results": formatted_results,
        })

    except ValueError as e:
        return error_response(f"Invalid filter: {str(e)}")
    except RuntimeError as e:
        return error_response(f"Search engine error: {str(e)}")
    except Exception as e:
        return error_response(f"Error searching earnings calls: {str(e)}")


# ==============================================================================
# TOOL SCHEMA CONSTANTS
# ==============================================================================

EARNINGS_CALL_SEARCH_DESCRIPTION = """Search earnings call transcripts using hybrid semantic + keyword search.

Use this tool to find information about company earnings, revenue, margins, guidance, and management commentary.

CRITICAL - Query Formulation:
Write detailed, specific natural language queries. The search uses semantic embeddings - detailed queries retrieve far better results than keywords.

GOOD queries (detailed, specific, natural language):
- "What is Apple's revenue guidance and outlook for the services segment in fiscal 2025?"
- "How is Microsoft's management describing Azure cloud growth and AI infrastructure investments?"
- "What are the key drivers behind Tesla's gross margin improvements and cost reduction initiatives?"
- "How did Amazon's advertising business perform and what is the growth outlook for AWS?"
- "What challenges is Intel facing in the data center segment and how is management addressing them?"

BAD queries (too vague, keyword-style - DO NOT USE):
- "revenue guidance"
- "margins outlook"
- "AAPL growth"
- "cloud performance"
- "AI investments"

Always specify what aspect of the business you're asking about and what kind of information you need."""

EARNINGS_CALL_SEARCH_PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": (
                "A detailed natural language query describing exactly what earnings information you need. "
                "Be specific: include the business segment, metric, and context. "
                "Example: 'What is management's outlook for gross margin improvement and cost efficiency initiatives?' "
                "NOT: 'margin outlook'"
            )
        },
        "top_k": {
            "type": "integer",
            "description": "Number of results to return (default: 5, max: 25)",
            "minimum": 1,
            "maximum": 25,
            "default": 5
        },
        "ticker": {
            "type": "string",
            "description": "Filter by single ticker symbol (e.g., 'AAPL', 'MSFT')"
        },
        "tickers": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Filter by multiple ticker symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])"
        },
        "fiscal_year": {
            "type": "integer",
            "description": "Filter by fiscal year (e.g., 2024, 2025)"
        },
        "fiscal_quarter": {
            "type": "string",
            "description": "Filter by fiscal quarter. Use 'Q1'-'Q4' with fiscal_year, or full format '2025Q4'"
        }
    },
    "required": ["query"],
    "additionalProperties": False
}

EARNINGS_CALL_SEARCH_TOOL = {
    "name": "earnings_call_search",
    "description": EARNINGS_CALL_SEARCH_DESCRIPTION,
    "parameters": EARNINGS_CALL_SEARCH_PARAMETERS,
    "function": earnings_call_search,
}
