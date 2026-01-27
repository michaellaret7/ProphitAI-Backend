"""Enhanced search with query decomposition and parallel execution."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.core.foundry.models.vector import QueryResult
from app.core.foundry.retrieval.base import BaseSearch
from app.core.foundry.retrieval.enhance_query.bd_query import SubQuery, decompose_query
from app.core.foundry.retrieval.rerank import rerank


def _execute_sub_query(
    searcher: BaseSearch,
    sub_query: SubQuery,
    namespace: str,
    filters: dict[str, Any],
) -> list[QueryResult]:
    """Execute a single sub-query search."""
    return searcher.search(
        query=sub_query.sub_query,
        top_k=sub_query.top_k,
        namespace=namespace,
        **filters,
    )


def enhanced_search(
    query: str,
    searcher: BaseSearch,
    namespace: str = "earnings_calls",
    dedupe: bool = True,
    final_top_k: int = 10,
    **filters: Any,
) -> list[QueryResult]:
    """
    Decompose a query into sub-queries and execute searches in parallel.

    Args:
        query: The user's original query.
        searcher: A BaseSearch instance (VectorSearch or HybridSearch).
        namespace: Pinecone namespace to search in.
        dedupe: Whether to deduplicate results by ID.
        max_workers: Maximum number of parallel search threads.
        final_top_k: Number of results to return after final reranking.
        **filters: Metadata filters passed to each search.

    Returns:
        List of QueryResult objects reranked against the original query.
    """
    sub_queries = decompose_query(query)

    print(sub_queries.model_dump_json(indent=4))
    print("-" * 50)

    max_workers = len(sub_queries.sub_queries)

    print(f"Broke down query into {len(sub_queries.sub_queries)} sub-queries")

    all_results: list[QueryResult] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _execute_sub_query,
                searcher,
                sq,
                namespace,
                filters,
            ): sq
            for sq in sub_queries.sub_queries
        }

        for future in as_completed(futures):
            results = future.result()
            all_results.extend(results)

    if dedupe:
        seen_ids: set[str] = set()
        deduped: list[QueryResult] = []
        for r in all_results:
            if r.id not in seen_ids:
                seen_ids.add(r.id)
                deduped.append(r)
        all_results = deduped

    # Reason: Rerank merged results against original query for best relevance
    return rerank(query=query, results=all_results, top_k=final_top_k)



