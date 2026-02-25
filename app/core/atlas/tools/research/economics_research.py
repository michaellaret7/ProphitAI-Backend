"""Economics Research Search Tool - Search economics reports and indicators.

Uses hybrid search (semantic + keyword) over economics documents including
ISM PMI reports, employment data, GDP releases, CPI/PPI reports, and other
key economic indicator publications.
"""

from typing import Annotated, Optional

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.core.foundry.retrieval import HybridSearch
from app.core.foundry.models.vector import QueryResult


# ================================
# --> Tools
# ================================

@agent_tool(name="economics_research_search")
def economics_research_search(
    query: str,
    top_k: Annotated[int, Param(min_val=3, max_val=25)] = 7,
    doc_id: Optional[str] = None,

) -> str:
    """
    Search economics reports and indicator publications using hybrid semantic + keyword search.

    Use this tool to find information about economic indicators such as ISM
    Manufacturing/Services PMI, employment reports, GDP releases, CPI/PPI
    inflation data, consumer confidence, retail sales, housing data, and
    other key economic publications.

    CRITICAL - Query Formulation:
    Write detailed, specific natural language queries. The search uses semantic
    embeddings - detailed queries retrieve far better results than keywords.

    GOOD queries (detailed, specific, natural language):
    - "What did the latest ISM Manufacturing PMI report say about new orders and production activity?"
    - "How is the employment situation evolving according to the most recent jobs report and labor market indicators?"
    - "What are the latest CPI readings showing about core inflation trends and shelter costs?"
    - "What does the GDP report indicate about consumer spending and business investment growth?"
    - "How are ISM supplier deliveries and inventory levels signaling supply chain conditions?"

    BAD queries (too vague, keyword-style - DO NOT USE):
    - "PMI data"
    - "jobs report"
    - "inflation"
    - "GDP growth"
    - "economic indicators"

    Always cite the source report. Example: 'According to the ISM Manufacturing PMI Report, the Manufacturing PMI registered 47.9 percent, indicating contraction.'

    Args:
        query: A detailed natural language query describing what economic data
            or indicator information you need. Be specific: include the indicator
            name, the component or metric, and what aspect you're asking about.
            Example: 'What did the ISM Manufacturing PMI report say about new
            orders and employment trends?' NOT: 'ISM PMI'
        top_k: Number of results to return (default: 7, max: 25)
        doc_id: Filter by specific document ID to search within a single report

    Returns:
        YAML-formatted search results with query, num_results, filters_applied,
        and results list containing id, score, text, doc_id, doc_type,
        chunk_id, chunk_index, and total_chunks for each match

    Examples:
        economics_research_search(query="What is the latest ISM Manufacturing PMI and new orders index?")
        >>> {"success": True, "data": {"query": "...", "num_results": 7, "results": [...]}}

        economics_research_search(query="Employment and labor market trends", doc_id="065c9e150c1a43738d10a3785a15857a")
        >>> {"success": True, "data": {"query": "...", "filters_applied": {"doc_id": "..."}, "results": [...]}}

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
    if doc_id:
        filters["doc_id"] = doc_id

    try:
        searcher = HybridSearch(use_rerank=True, enhanced=True)

        results: list[QueryResult] = searcher.search(
            query=query,
            top_k=top_k,
            namespace="economics",
            **filters,
        )

        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "score": round(result.score, 4),
                "text": result.metadata.get("text", ""),
                "doc_id": result.metadata.get("doc_id"),
                "doc_type": result.metadata.get("doc_type"),
                "chunk_id": result.metadata.get("chunk_id"),
                "chunk_index": result.metadata.get("chunk_index"),
                "total_chunks": result.metadata.get("total_chunks"),
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
        return error_response(f"Error searching economics research: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(economics_research_search.tool)
