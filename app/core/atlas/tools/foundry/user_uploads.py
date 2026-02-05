"""
User Upload Search Tool - Search user-uploaded documents.

Uses hybrid search (semantic + keyword) over documents uploaded by a specific user.
REQUIRES user_id to ensure users can only search their own documents.
"""

from typing import Optional

from app.core.atlas.tools.responses import success_response, error_response
from app.core.foundry.retrieval import HybridSearch
from app.core.foundry.models.vector import QueryResult


# ==============================================================================
# TOOL FUNCTION
# ==============================================================================

def user_upload_search(
    query: str,
    user_id: str,
    top_k: int = 7,
    file_name: Optional[str] = None,
    _simulation_date: Optional[str] = None,  # noqa: ARG001 - Injected by framework
) -> str:
    """
    Search user-uploaded documents using hybrid search.

    Searches over documents that a specific user has uploaded. Requires user_id
    to ensure users can only access their own documents.

    Args:
        query: Search query - natural language question or keywords
        user_id: User ID to filter documents by (REQUIRED for security)
        top_k: Number of results to return (default: 7, max: 25)
        file_name: Filter by filename pattern
        _simulation_date: Injected by agent framework (not used)

    Returns:
        str: YAML-formatted search results with:
            - 'success' (bool): Whether search succeeded
            - 'data' (dict): Contains 'results' list with text and metadata
            - 'error' (str): Error message when unsuccessful
    """
    # Validate user_id (REQUIRED)
    if not user_id or not isinstance(user_id, str):
        return error_response("user_id is required and must be a non-empty string")

    user_id = user_id.strip()
    if not user_id:
        return error_response("user_id cannot be empty or whitespace only")

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

    # Build filters - user_id is always required
    filters: dict = {"user_id": user_id}
    if file_name:
        filters["file_name"] = file_name

    try:
        searcher = HybridSearch(use_rerank=True, enhanced=True)

        results: list[QueryResult] = searcher.search(
            query=query,
            top_k=top_k,
            namespace="user_uploads",
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
            "user_id": user_id,
            "num_results": len(formatted_results),
            "filters_applied": filters,
            "results": formatted_results,
        })

    except ValueError as e:
        return error_response(f"Invalid filter: {str(e)}")
    except RuntimeError as e:
        return error_response(f"Search engine error: {str(e)}")
    except Exception as e:
        return error_response(f"Error searching user uploads: {str(e)}")


# ==============================================================================
# TOOL SCHEMA CONSTANTS
# ==============================================================================

USER_UPLOAD_SEARCH_DESCRIPTION = """Search the user's uploaded documents using hybrid semantic + keyword search.

Use this tool when the user wants to search through documents they have uploaded (PDFs, reports, etc.).

IMPORTANT: This tool requires user_id to ensure users can only search their own documents.

Query Tips:
- Write detailed, specific natural language queries for best results
- The search uses semantic embeddings, so full sentences work better than keywords
- You can filter by file_name if the user mentions a specific document

Examples:
- "What are the key findings in the quarterly report?"
- "Find information about revenue projections"
- "What does the document say about market risks?"

Always cite your sources by mentioning the file_name in your response."""

USER_UPLOAD_SEARCH_PARAMETERS = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": (
                "A detailed natural language query describing what information you need from the user's documents. "
                "Be specific about the topic or question. "
                "Example: 'What are the revenue projections for next quarter?' NOT: 'revenue'"
            )
        },
        "user_id": {
            "type": "string",
            "description": "The user's ID. REQUIRED for security - ensures users can only search their own documents."
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
            "description": "Filter by filename pattern (e.g., 'quarterly-report' to match files containing that name)"
        }
    },
    "required": ["query", "user_id"],
    "additionalProperties": False
}

USER_UPLOAD_SEARCH_TOOL = {
    "name": "user_upload_search",
    "description": USER_UPLOAD_SEARCH_DESCRIPTION,
    "parameters": USER_UPLOAD_SEARCH_PARAMETERS,
    "function": user_upload_search,
}
