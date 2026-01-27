"""Hybrid search combining dense (semantic) and sparse (BM25) vectors."""

from typing import Any

from app.core.foundry.embeddings.voyage_embeddings import embed_query
from app.core.foundry.models.vector import QueryResult
from app.core.foundry.retrieval.search.base import BaseSearch


class HybridSearch(BaseSearch):
    """Hybrid search combining dense and sparse vectors with alpha weighting."""

    def __init__(
        self,
        alpha: float = 0.5,
        use_rerank: bool = False,
        validate_filters: bool = True,
        enhanced: bool = False,
    ):
        """
        Initialize hybrid search with a pre-fitted BM25 encoder.

        Args:
            alpha: Weighting factor between dense and sparse vectors (0-1).
            use_rerank: Whether to rerank results using a cross-encoder.
            validate_filters: Whether to validate filter keys against Pinecone metadata.
                Set to False to skip validation for performance.
            enhanced: Whether to use query decomposition for complex queries.
        """
        super().__init__(
            use_rerank=use_rerank,
            validate_filters=validate_filters,
            enhanced=enhanced,
        )
        self.alpha = alpha

        # Reason: Lazy import to avoid heavy imports when only using VectorSearch
        from app.core.foundry.embeddings.sparse_encoder import SparseEncoder

        self.sparse_encoder = SparseEncoder()
        self.sparse_encoder.load()

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

        embedding = embed_query(query, sparse_encoder=self.sparse_encoder)

        if embedding.sparse is None:
            raise RuntimeError("Sparse embedding not generated. Check encoder.")

        search_results = self.manager.hybrid_query(
            dense_vector=embedding.dense,
            sparse_vector=embedding.sparse,
            top_k=retrieval_top_k,
            namespace=namespace,
            filter=filter_dict,
            alpha=self.alpha,
        )

        return self._finalize_results(query, search_results, top_k)

    def search(
        self,
        query: str,
        top_k: int = 7,
        namespace: str = "earnings_calls",
        **filters: Any,
    ) -> list[QueryResult]:
        """
        Execute a hybrid search combining semantic and keyword matching.

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
            RuntimeError: If sparse embedding generation fails.

        Examples:
            # Earnings calls with specific filters
            search("revenue growth", ticker="AAPL", fiscal_year=2025)

            # Macro research with filename filter
            search("interest rates", namespace="macro_research", filename="JPM_Report")

            # Multiple values for a filter
            search("guidance", ticker=["AAPL", "GOOGL", "MSFT"])
        """
        if self.enhanced:
            return self._run_enhanced_search(query, top_k, namespace, **filters)

        return self._search_internal(query, top_k, namespace, filters)


if __name__ == "__main__":
    hybrid_search = HybridSearch(use_rerank=True, enhanced=True)

    results = hybrid_search.search(
        query="Scandanavia central bank and interest rates. Japanese central bank and interest rates.",
        namespace="macro_research",
        top_k=7,
    )
    for result in results:
        print(result.metadata["chunk_id"])
        print(result.metadata["text"])
        print(result.score)
        print("--------------------------------")

    print(len(results))
