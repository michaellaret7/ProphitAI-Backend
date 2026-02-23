"""Earnings Call Search Tool - Search earnings call transcripts.

Uses hybrid search (semantic + keyword) over earnings call transcripts
to find information about company guidance, revenue, margins, and outlook.
"""

import re
from typing import Annotated, Optional

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.core.foundry.retrieval import HybridSearch
from app.core.foundry.models.vector import QueryResult


# ================================
# --> Helper funcs
# ================================

FISCAL_QUARTER_FULL_PATTERN = re.compile(r"^\d{4}Q[1-4]$")


# ================================
# --> Tools
# ================================

@agent_tool(name="earnings_call_search")
def earnings_call_search(
    query: str,
    top_k: Annotated[int, Param(min_val=1, max_val=25)] = 5,
    ticker: Optional[str] = None,
    tickers: Optional[list[str]] = None,
    fiscal_year: Optional[int] = None,
    fiscal_quarter: Optional[str] = None,

) -> str:
    """
    Search earnings call transcripts using hybrid semantic + keyword search.

    Use this tool to find information about company earnings, revenue, margins,
    guidance, and management commentary.

    CRITICAL - Query Formulation:
    Write detailed, specific natural language queries. The search uses semantic
    embeddings - detailed queries retrieve far better results than keywords.

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

    Always specify what aspect of the business you're asking about and what kind of information you need.

    Args:
        query: A detailed natural language query describing exactly what earnings
            information you need. Be specific: include the business segment, metric,
            and context. Example: 'What is management's outlook for gross margin
            improvement and cost efficiency initiatives?' NOT: 'margin outlook'
        top_k: Number of results to return (default: 5, max: 25)
        ticker: Filter by single ticker symbol (e.g., 'AAPL', 'MSFT')
        tickers: Filter by multiple ticker symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])
        fiscal_year: Filter by fiscal year (e.g., 2024, 2025)
        fiscal_quarter: Filter by fiscal quarter. Use 'Q1'-'Q4' with fiscal_year,
            or full format '2025Q4'

    Returns:
        YAML-formatted search results with query, num_results, filters_applied,
        and results list containing id, score, text, ticker, fiscal_year,
        fiscal_quarter, and chunk_id for each match

    Examples:
        earnings_call_search(query="What is Apple's services revenue guidance?", ticker="AAPL")
        >>> {"success": True, "data": {"query": "...", "num_results": 5, "results": [...]}}

        earnings_call_search(query="Azure cloud growth outlook", tickers=["MSFT", "GOOGL"], fiscal_quarter="2025Q4")
        >>> {"success": True, "data": {"query": "...", "num_results": 5, "filters_applied": {...}, "results": [...]}}

    Raises:
        ValueError: If query is empty or filters are invalid
    """
    if not query or not isinstance(query, str):
        return error_response("Query is required and must be a non-empty string")

    query = query.strip()
    if not query:
        return error_response("Query cannot be empty or whitespace only")

    if not isinstance(top_k, int) or top_k < 1:
        return error_response("top_k must be a positive integer")
    top_k = min(top_k, 25)

    # Reason: normalize and validate fiscal_quarter into YYYYQ# format
    normalized_quarter: Optional[str] = None
    if fiscal_quarter:
        fiscal_quarter = fiscal_quarter.upper()

        if FISCAL_QUARTER_FULL_PATTERN.match(fiscal_quarter):
            normalized_quarter = fiscal_quarter
        elif fiscal_quarter in ["Q1", "Q2", "Q3", "Q4"]:
            if fiscal_year:
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

    # Reason: build metadata filters dict only with provided values
    filters: dict = {}
    if ticker:
        filters["ticker"] = ticker.upper()
    elif tickers:
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


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(earnings_call_search.tool)
