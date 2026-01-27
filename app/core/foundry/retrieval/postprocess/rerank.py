"""Reranking using Voyage AI for improved retrieval quality."""

import os

import voyageai
from dotenv import load_dotenv

from app.core.foundry.models.vector import QueryResult

load_dotenv()


def rerank(
    query: str,
    results: list[QueryResult],
    model: str = "rerank-2.5",
    top_k: int = 5,
) -> list[QueryResult]:
    """
    Rerank QueryResult objects using Voyage AI.

    Args:
        query: The search query.
        results: List of QueryResult objects from initial retrieval.
        model: Voyage rerank model to use.
        top_k: Number of top results to return after reranking.

    Returns:
        List of QueryResult objects with updated scores, sorted by relevance.
    """
    if not results:
        return []

    # Extract text from metadata for reranking
    documents = [r.metadata.get("text", "") for r in results]

    client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))

    response = client.rerank(
        query=query,
        documents=documents,
        model=model,
        top_k=top_k,
    )

    # Build reranked QueryResult objects with updated scores
    reranked = []
    for item in response.results:
        original = results[item.index]
        reranked.append(
            QueryResult(
                id=original.id,
                score=item.relevance_score,
                values=original.values,
                metadata=original.metadata,
            )
        )

    return reranked
