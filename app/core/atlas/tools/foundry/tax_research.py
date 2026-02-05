"""
Tax Research Search Tool - Search tax documents and IRS publications.

Uses hybrid search (semantic + keyword) over tax documents including
IRS forms, instructions, publications, and tax rule summaries.
"""

from typing import Optional

from app.core.atlas.tools.responses import success_response, error_response
from app.core.foundry.retrieval import HybridSearch
from app.core.foundry.models.vector import QueryResult


# ==============================================================================
# TOOL FUNCTION
# ==============================================================================

def tax_research_search(
    query: str,
    top_k: int = 7,
    file_name: Optional[str] = None,
    _simulation_date: Optional[str] = None,  # noqa: ARG001 - Injected by framework
) -> str:
    """
    Search tax documents using hybrid search.

    Searches over IRS forms, instructions, publications, and tax rule
    summaries stored in the tax_docs namespace.

    Args:
        query: Search query - natural language question about taxes
        top_k: Number of results to return (default: 7, max: 25)
        file_name: Filter by filename pattern (e.g., "1040" to match 1040-related docs)
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

        # Format results for agent consumption
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


# ==============================================================================
# TOOL SCHEMA CONSTANTS
# ==============================================================================

TAX_RESEARCH_SEARCH_DESCRIPTION = """Search tax documents, IRS forms, instructions, and publications using hybrid semantic + keyword search.

Use this tool to find information about federal income tax rules, IRS forms and instructions, tax brackets, deductions, credits, filing requirements, and tax regulations.

CRITICAL - Query Formulation:
Write detailed, specific natural language queries. The search uses semantic embeddings - detailed queries retrieve far better results than keywords.

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

Always cite the source document. Example: 'According to IRS Form 1040 Instructions, the standard deduction for single filers in 2025 is...'"""

TAX_RESEARCH_SEARCH_PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": (
                "A detailed natural language query about tax rules, forms, or regulations. "
                "Be specific: include the tax year, the form or topic, and what you need to know. "
                "Example: 'What are the 2025 income thresholds for each federal tax bracket?' "
                "NOT: 'tax brackets 2025'"
            )
        },
        "top_k": {
            "type": "integer",
            "description": "Number of results to return (default: 7, max: 25)",
            "minimum": 3,
            "maximum": 25,
            "default": 7
        },
        "file_name": {
            "type": "string",
            "description": "Filter by document name (e.g., '1040' to match 1040-related documents)"
        }
    },
    "required": ["query"],
    "additionalProperties": False
}

TAX_RESEARCH_SEARCH_TOOL = {
    "name": "tax_research_search",
    "description": TAX_RESEARCH_SEARCH_DESCRIPTION,
    "parameters": TAX_RESEARCH_SEARCH_PARAMETERS,
    "function": tax_research_search,
}
