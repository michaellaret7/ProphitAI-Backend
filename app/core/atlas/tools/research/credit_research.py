"""Credit Research Search Tool - Search credit/fixed income research reports.

Uses hybrid search (semantic + keyword) over research reports covering
corporate bonds, credit spreads, high yield, investment grade, credit
derivatives, and leveraged loans.
"""

from typing import Annotated, Optional

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.core.foundry.retrieval import HybridSearch
from app.core.foundry.models.vector import QueryResult


# ================================
# --> Tools
# ================================

@agent_tool(name="credit_research_search")
def credit_research_search(
    query: str,
    top_k: Annotated[int, Param(min_val=3, max_val=15)] = 7,
    research_provider: Optional[str] = None,
    file_name: Optional[str] = None,

) -> str:
    """
    Search credit and fixed income research reports using hybrid semantic + keyword search.

    Use this tool to find information about corporate bonds, credit spreads,
    high yield markets, investment grade credit, credit derivatives, leveraged
    loans, and credit ratings.

    CRITICAL - Query Formulation:
    Write detailed, specific natural language queries. The search uses semantic
    embeddings - detailed queries retrieve far better results than keywords.

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

    Always cite your sources. Example: 'According to Goldman Sachs research, high yield spreads are expected to tighten by 50 basis points.'[1]

    Args:
        query: A detailed natural language query describing exactly what credit/fixed
            income information you need. Be specific: include the credit segment
            (HY, IG, leveraged loans), the topic (spreads, defaults, ratings),
            and context (sector, timeline, relative value). Example: 'What is the
            outlook for US high yield default rates and credit spreads in 2026?'
            NOT: 'HY defaults 2026'
        top_k: Number of results to return (default: 7, max: 15)
        research_provider: Filter by research provider name (e.g., 'JPMorgan', 'Goldman', 'Morgan Stanley')
        file_name: Filter by file name pattern

    Returns:
        YAML-formatted search results with query, num_results, filters_applied,
        and results list containing id, score, text, research_provider, file_name,
        and chunk_id for each match

    Examples:
        credit_research_search(query="What is the HY default rate outlook for 2026?")
        >>> {"success": True, "data": {"query": "...", "num_results": 7, "results": [...]}}

        credit_research_search(query="IG corporate spreads vs Treasuries", research_provider="Goldman")
        >>> {"success": True, "data": {"query": "...", "filters_applied": {"research_provider": "Goldman"}, "results": [...]}}

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

    # Reason: build metadata filters dict only with provided values
    filters: dict = {}
    if research_provider:
        filters["research_provider"] = research_provider
    if file_name:
        filters["file_name"] = file_name

    try:
        searcher = HybridSearch(use_rerank=True, enhanced=True)

        results: list[QueryResult] = searcher.search(
            query=query,
            top_k=top_k,
            namespace="credit",
            **filters,
        )

        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "score": round(result.score, 4),
                "text": result.metadata.get("text", ""),
                "research_provider": result.metadata.get("research_provider"),
                "file_name": result.metadata.get("file_name"),
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


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(credit_research_search.tool)
