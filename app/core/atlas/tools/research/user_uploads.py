"""User Upload Search Tool - Search user-uploaded documents.

Uses hybrid search (semantic + keyword) over documents uploaded by a specific user.
REQUIRES clerk_id to ensure users can only search their own documents.
"""

from typing import Annotated, Optional

from app.core.atlas.tools.decorator import agent_tool, Param
from app.core.atlas.tools.responses import success_response, error_response
from app.core.foundry.retrieval import HybridSearch
from app.core.foundry.models.vector import QueryResult


# ================================
# --> Tools
# ================================

@agent_tool(name="user_upload_search")
def user_upload_search(
    query: str,
    clerk_id: str,
    top_k: Annotated[int, Param(min_val=3, max_val=25)] = 7,
    file_name: Optional[str] = None,

) -> str:
    """
    Search the user's uploaded documents using hybrid semantic + keyword search.

    Use this tool when the user wants to search through documents they have
    uploaded (PDFs, reports, etc.).

    IMPORTANT: This tool requires the users clerk_id to ensure users can only search
    their own documents.

    Query Tips:
    - Write detailed, specific natural language queries for best results
    - The search uses semantic embeddings, so full sentences work better than keywords
    - You can filter by file_name if the user mentions a specific document

    Examples:
    - "What are the key findings in the quarterly report?"
    - "Find information about revenue projections"
    - "What does the document say about market risks?"

    Always cite your sources by mentioning the file_name in your response.

    Args:
        query: A detailed natural language query describing what information you
            need from the user's documents. Be specific about the topic or question.
            Example: 'What are the revenue projections for next quarter?' NOT: 'revenue'
        clerk_id: The user's Clerk ID. REQUIRED for security - ensures users can only
            search their own documents.
        top_k: Number of results to return (default: 7, max: 25)
        file_name: Filter by filename pattern (e.g., 'quarterly-report' to match
            files containing that name)

    Returns:
        YAML-formatted search results with query, user_id, num_results,
        filters_applied, and results list containing id, score, text,
        file_name, doc_id, chunk_id, chunk_index, and total_chunks

    Examples:
        user_upload_search(query="What are the key findings?", clerk_id="abc-123")
        >>> {"success": True, "data": {"query": "...", "num_results": 7, "results": [...]}}

    Raises:
        ValueError: If query or clerk_id is empty or filters are invalid
    """
    if not clerk_id or not isinstance(clerk_id, str):
        return error_response("clerk_id is required and must be a non-empty string")

    clerk_id = clerk_id.strip()
    if not clerk_id:
        return error_response("clerk_id cannot be empty or whitespace only")

    if not query or not isinstance(query, str):
        return error_response("Query is required and must be a non-empty string")

    query = query.strip()
    if not query:
        return error_response("Query cannot be empty or whitespace only")

    if not isinstance(top_k, int) or top_k < 1:
        return error_response("top_k must be a positive integer")
    top_k = min(top_k, 25)

    # Reason: clerk_id maps to user_id in Pinecone metadata for filtering
    filters: dict = {"user_id": clerk_id}
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
            "clerk_id": clerk_id,
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



