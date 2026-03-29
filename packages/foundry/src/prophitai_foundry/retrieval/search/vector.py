"""Dense vector search using Voyage AI embeddings."""

from typing import Any

from prophitai_foundry.embeddings.voyage_embeddings import embed_query
from prophitai_foundry.models.vector import QueryResult
from prophitai_foundry.retrieval.search.base import BaseSearch


class VectorSearch(BaseSearch):
    """Dense vector search using semantic embeddings."""

    def _search_internal(
        self,
        query: str,
        top_k: int,
        namespace: str,
        filters: dict[str, Any],
    ) -> list[QueryResult]:
        """Internal search method for enhanced search parallelization."""
        retrieval_top_k, filter_dict = self._prepare_search(
            top_k=top_k,
            namespace=namespace,
            **filters,
        )

        embedding = embed_query(query)

        search_results = self.manager.query(
            vector=embedding.dense,
            top_k=retrieval_top_k,
            namespace=namespace,
            filter=filter_dict,
        )

        return self._finalize_results(query, search_results, top_k)

    def search(
        self,
        query: str,
        top_k: int = 5,
        namespace: str = "earnings_calls",
        **filters: Any,
    ) -> list[QueryResult]:
        """
        Execute a dense vector search.

        Args:
            query: The search query text.
            top_k: Number of results to return.
            namespace: Pinecone namespace to search in.
            **filters: Dynamic metadata filters. Keys must match metadata fields
                in the namespace. Values can be single items or lists (for $in queries).

        Returns:
            List of QueryResult objects sorted by relevance.

        Raises:
            ValueError: If validate_filters is True and a filter key doesn't exist.

        Examples:
            # Earnings calls with specific filters
            search("revenue growth", ticker="AAPL", fiscal_year=2025)

            # Multiple values for a filter
            search("guidance", ticker=["AAPL", "GOOGL", "MSFT"])
        """
        if self.enhanced:
            return self._run_enhanced_search(query, top_k, namespace, **filters)

        return self._search_internal(query, top_k, namespace, filters)


if __name__ == "__main__":
    vector_search = VectorSearch(use_rerank=True)

    results = vector_search.search(
        query="What was the company's reported revenue for the last quarter?",
        ticker="AAL",
        fiscal_quarter="2025Q3",
        fiscal_year=2025,
        namespace="earnings_calls",
    )
    for result in results:
        print(result.metadata["chunk_id"])
        print(result.metadata["text"])
        print(result.score)
        print("--------------------------------")
