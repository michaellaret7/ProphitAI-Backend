"""
Macro Research Search Tool - Search macro/economic research reports.

Uses hybrid search (semantic + keyword) over research reports from providers
like JPMorgan, Goldman Sachs, etc. covering macro themes, interest rates,
central banks, and economic outlook.
"""

from typing import Optional

from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from app.core.foundry.retrieval.hybrid import HybridSearch
from app.core.foundry.models.vector import QueryResult


# ==============================================================================
# TOOL FUNCTION
# ==============================================================================

def macro_research_search(
    query: str,
    top_k: int = 5,
    research_provider: Optional[str] = None,
    filename: Optional[str] = None,
    _simulation_date: Optional[str] = None,
) -> str:
    """
    Search macro/economic research reports using hybrid search.

    Searches over research reports covering macro themes like interest rates,
    central bank policy, inflation, economic outlook, and market commentary.

    Args:
        query: Search query - natural language question or keywords about macro topics
        top_k: Number of results to return (default: 5, max: 25)
        research_provider: Filter by research provider (e.g., "JPMorgan", "Goldman", "Morgan Stanley")
        filename: Filter by filename pattern
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

    # Build filters
    filters: dict = {}
    if research_provider:
        filters["research_provider"] = research_provider
    if filename:
        filters["filename"] = filename

    try:
        searcher = HybridSearch(use_rerank=True)

        results: list[QueryResult] = searcher.search(
            query=query,
            top_k=top_k,
            namespace="macro_research",
            **filters,
        )

        # Format results for agent consumption
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "score": round(result.score, 4),
                "text": result.metadata.get("text", ""),
                "research_provider": result.metadata.get("research_provider"),
                "filename": result.metadata.get("filename"),
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
        return error_response(f"Error searching macro research: {str(e)}")


# ==============================================================================
# TOOL SCHEMA CONSTANTS
# ==============================================================================

MACRO_RESEARCH_SEARCH_DESCRIPTION = (
    "Search macro and economic research reports using hybrid semantic + keyword search. "
    "Use this tool to find information about interest rates, central bank policy (Fed, ECB, BOJ), "
    "inflation, economic outlook, market commentary, macro themes, and more. "
    "Returns relevant passages(chunks of text) from research reports with relevance scores. "
    "When synthesizing the results from this tool, always cite your source(s). Example: 'According to JPMorgan research, the Fed is expected to cut rates by 25 basis points in 2024.'[1 (You will then cite the research report as the number 1 at the bottom of your response)] "
    "Example: macro_research_search(query='What is the Fed outlook for rate cuts?') "
    "Example: macro_research_search(query='Japan central bank policy', research_provider='JPMorgan')"
)

MACRO_RESEARCH_SEARCH_PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search query - natural language question or keywords about macro/economic topics"
        },
        "top_k": {
            "type": "integer",
            "description": "Number of results to return (default: 5, max: 25)",
            "minimum": 1,
            "maximum": 10,
            "default": 5
        },
        "research_provider": {
            "type": "string",
            "description": "Filter by research provider name (e.g., 'JPMorgan', 'Goldman', 'Morgan Stanley')"
        },
        "filename": {
            "type": "string",
            "description": "Filter by filename pattern"
        }
    },
    "required": ["query"],
    "additionalProperties": False
}

MACRO_RESEARCH_SEARCH_TOOL = {
    "name": "macro_research_search",
    "description": MACRO_RESEARCH_SEARCH_DESCRIPTION,
    "parameters": MACRO_RESEARCH_SEARCH_PARAMETERS,
    "function": macro_research_search,
}




