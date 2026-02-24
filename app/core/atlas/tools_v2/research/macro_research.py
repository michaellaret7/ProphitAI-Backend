"""Macro Research Search Tool - Search macro/economic research reports.

Uses hybrid search (semantic + keyword) over research reports from providers
like JPMorgan, Goldman Sachs, etc. covering macro themes, interest rates,
central banks, and economic outlook.
"""

from typing import Annotated, Optional

from app.core.atlas.tools_v2.decorator import agent_tool, Param
from app.core.atlas.tools_v2.responses import success_response, error_response
from app.core.foundry.retrieval import HybridSearch
from app.core.foundry.models.vector import QueryResult


# ================================
# --> Tools
# ================================

@agent_tool(name="macro_research")
def macro_research(
    query: str,
    top_k: Annotated[int, Param(min_val=3, max_val=15)] = 7,
    research_provider: Optional[str] = None,
    filename: Optional[str] = None,

) -> str:
    """
    Search macro and economic research reports using hybrid semantic + keyword search.

    Use this tool to find information about interest rates, central bank policy,
    inflation, economic outlook, and market commentary.

    CRITICAL - Query Formulation:
    Write detailed, specific natural language queries. The search uses semantic
    embeddings - detailed queries retrieve far better results than keywords.

    GOOD queries (detailed, specific, natural language):
    - "What is the Federal Reserve's interest rate outlook and expected policy path for 2026?"
    - "How is the Bank of Japan approaching monetary policy normalization and yield curve control adjustments?"
    - "What are JPMorgan's expectations for Riksbank and Norges Bank rate decisions in Scandinavia?"
    - "European Central Bank inflation expectations and timeline for potential rate cuts in the eurozone"
    - "Impact of US Treasury yields on emerging market fixed income and currency markets"

    BAD queries (too vague, keyword-style - DO NOT USE):
    - "Fed rates"
    - "Japan policy"
    - "Scandinavian rates Sweden Norway"
    - "inflation outlook"
    - "ECB cuts"

    Always cite your sources. Example: 'According to JPMorgan research, the Fed is expected to cut rates by 25 basis points.'[1]

    Args:
        query: A detailed natural language query describing exactly what macro/economic
            information you need. Be specific: include the entity (Fed, ECB, BOJ),
            the topic (rate outlook, inflation), and context (timeline, region).
            Example: 'What is the Federal Reserve's expected rate path and inflation
            outlook for 2026?' NOT: 'Fed rates 2026'
        top_k: Number of results to return (default: 7, max: 15)
        research_provider: Filter by research provider name (e.g., 'JPMorgan', 'Goldman', 'Morgan Stanley')
        filename: Filter by filename pattern

    Returns:
        YAML-formatted search results with query, num_results, filters_applied,
        and results list containing id, score, text, research_provider, filename,
        and chunk_id for each match

    Examples:
        macro_research_search(query="What is the Fed's rate outlook for 2026?")
        >>> {"success": True, "data": {"query": "...", "num_results": 7, "results": [...]}}

        macro_research_search(query="ECB inflation expectations", research_provider="Goldman")
        >>> {"success": True, "data": {"query": "...", "num_results": 5, "filters_applied": {"research_provider": "Goldman"}, "results": [...]}}

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
    if filename:
        filters["filename"] = filename

    try:
        searcher = HybridSearch(use_rerank=True, enhanced=True)

        results: list[QueryResult] = searcher.search(
            query=query,
            top_k=top_k,
            namespace="macro_research",
            **filters,
        )

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



