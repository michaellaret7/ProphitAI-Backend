"""Tax Research Search Tool - Search tax documents and IRS publications.

Uses hybrid search (semantic + keyword) over tax documents including
IRS forms, instructions, publications, and tax rule summaries.
"""

from typing import Annotated, Optional

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.core.foundry.retrieval import HybridSearch
from app.core.foundry.models.vector import QueryResult


# ================================
# --> Tools
# ================================

@agent_tool(name="tax_research_search")
def tax_research_search(
    query: str,
    top_k: Annotated[int, Param(min_val=3, max_val=25)] = 7,
    file_name: Optional[str] = None,
    _simulation_date: Optional[str] = None,
) -> str:
    """
    Search tax documents, IRS forms, instructions, and publications using hybrid semantic + keyword search.

    Use this tool to find information about federal income tax rules, IRS forms
    and instructions, tax brackets, deductions, credits, filing requirements,
    and tax regulations.

    CRITICAL - Query Formulation:
    Write detailed, specific natural language queries. The search uses semantic
    embeddings - detailed queries retrieve far better results than keywords.

    GOOD queries (detailed, specific, natural language):
    - "What are the 2025 federal income tax brackets and standard deduction amounts for single filers?"
    - "How do I report capital gains and losses on Form 1040 Schedule D?"
    - "What are the eligibility requirements and income limits for the Earned Income Tax Credit in 2025?"
    - "What are the rules for Required Minimum Distributions from traditional IRAs?"
    - "How does the Child Tax Credit phase out based on modified adjusted gross income?"

    BAD queries (too vague, keyword-style - DO NOT USE):
    - "tax brackets"
    - "1040 form"
    - "deductions"
    - "capital gains"
    - "IRA rules"

    Always cite the source document. Example: 'According to IRS Form 1040 Instructions, the standard deduction for single filers in 2025 is...'

    Args:
        query: A detailed natural language query about tax rules, forms, or
            regulations. Be specific: include the tax year, the form or topic,
            and what you need to know. Example: 'What are the 2025 income
            thresholds for each federal tax bracket?' NOT: 'tax brackets 2025'
        top_k: Number of results to return (default: 7, max: 25)
        file_name: Filter by document name (e.g., '1040' to match 1040-related documents)

    Returns:
        YAML-formatted search results with query, num_results, filters_applied,
        and results list containing id, score, text, file_name, doc_id,
        chunk_id, chunk_index, and total_chunks

    Examples:
        tax_research_search(query="What are the 2025 tax brackets for single filers?")
        >>> {"success": True, "data": {"query": "...", "num_results": 7, "results": [...]}}

        tax_research_search(query="Schedule D capital gains reporting", file_name="1040")
        >>> {"success": True, "data": {"query": "...", "filters_applied": {"file_name": "1040"}, "results": [...]}}

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
    if file_name:
        filters["file_name"] = file_name

    try:
        searcher = HybridSearch(use_rerank=True, enhanced=True)

        results: list[QueryResult] = searcher.search(
            query=query,
            top_k=top_k,
            namespace="tax_docs",
            **filters,
        )

        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "score": round(result.score, 4),
                "text": result.metadata.get("text", ""),
                "file_name": result.metadata.get("file_name"),
                "doc_id": result.metadata.get("doc_id"),
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
        return error_response(f"Error searching tax documents: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(tax_research_search.tool)
