"""
Credit Research Search Tool - Search credit/fixed income research reports.

Uses hybrid search (semantic + keyword) over research reports covering
corporate bonds, credit spreads, high yield, investment grade, credit
derivatives, and leveraged loans.
"""

from typing import Optional

from app.core.atlas.tools.responses import success_response, error_response
from app.core.foundry.retrieval import HybridSearch
from app.core.foundry.models.vector import QueryResult


# ==============================================================================
# TOOL FUNCTION
# ==============================================================================

def credit_research_search(
    query: str,
    top_k: int = 7,
    research_provider: Optional[str] = None,
    filename: Optional[str] = None,
    _simulation_date: Optional[str] = None,
) -> str:
    """
    Search credit/fixed income research reports using hybrid search.

    Searches over research reports covering corporate bonds, credit spreads,
    high yield, investment grade, credit derivatives, and leveraged loans.

    Args:
        query: Search query - natural language question or keywords about credit topics
        top_k: Number of results to return (default: 7, max: 25)
        research_provider: Filter by research provider (e.g., "JPMorgan", "Goldman", "Morgan Stanley")
        filename: Filter by filename pattern
        _simulation_date: Injected by agent framework (not used)

    Returns:
        str: YAML-formatted search results with:
            - 'success' (bool): Whether search succeeded
            - 'data' (dict): Contains 'results' list with text and metadata
            - 'error' (str): Error message when unsuccessful
    """
    _ = _simulation_date  # Injected by framework, unused here

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
        searcher = HybridSearch(use_rerank=True, enhanced=True)

        results: list[QueryResult] = searcher.search(
            query=query,
            top_k=top_k,
            namespace="credit",
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
        return error_response(f"Error searching credit research: {str(e)}")


# ==============================================================================
# TOOL SCHEMA CONSTANTS
# ==============================================================================

CREDIT_RESEARCH_SEARCH_DESCRIPTION = """Search credit and fixed income research reports using hybrid semantic + keyword search.

Use this tool to find information about corporate bonds, credit spreads, high yield markets, investment grade credit, credit derivatives, leveraged loans, and credit ratings.

CRITICAL - Query Formulation:
Write detailed, specific natural language queries. The search uses semantic embeddings - detailed queries retrieve far better results than keywords.

GOOD queries (detailed, specific, natural language):
- "What is the outlook for US high yield credit spreads and default rates in 2026?"
- "How are investment grade corporate bond spreads expected to perform relative to Treasuries?"
- "What are the risks and opportunities in the leveraged loan market given current Fed policy?"
- "How do credit rating agencies view the telecommunications sector's leverage and refinancing risk?"
- "What is JPMorgan's view on CDS spreads and credit derivative positioning for financials?"

BAD queries (too vague, keyword-style - DO NOT USE):
- "HY spreads"
- "IG credit"
- "leveraged loans"
- "credit outlook"
- "bond spreads"

Always cite your sources. Example: 'According to Goldman Sachs research, high yield spreads are expected to tighten by 50 basis points.'[1]"""

CREDIT_RESEARCH_SEARCH_PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": (
                "A detailed natural language query describing exactly what credit/fixed income information you need. "
                "Be specific: include the credit segment (HY, IG, leveraged loans), the topic (spreads, defaults, ratings), "
                "and context (sector, timeline, relative value). Example: 'What is the outlook for US high yield "
                "default rates and credit spreads in 2026?' NOT: 'HY defaults 2026'"
            )
        },
        "top_k": {
            "type": "integer",
            "description": "Number of results to return (default: 7, max: 25)",
            "minimum": 3,
            "maximum": 15,
            "default": 7
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

CREDIT_RESEARCH_SEARCH_TOOL = {
    "name": "credit_research_search",
    "description": CREDIT_RESEARCH_SEARCH_DESCRIPTION,
    "parameters": CREDIT_RESEARCH_SEARCH_PARAMETERS,
    "function": credit_research_search,
}
