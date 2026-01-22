"""Dense vector search using Voyage AI embeddings."""

import os
from typing import Any

from dotenv import load_dotenv

from app.core.foundry.embeddings.pinecone_manager import PineconeManager
from app.core.foundry.embeddings.voyage_embeddings import embed_query
from app.core.foundry.models.vector import QueryResult
from app.core.foundry.retrieval.rerank import rerank as rerank_results
from app.core.foundry.retrieval.utils import build_metadata_filter

load_dotenv()


class VectorSearch:
    """Dense vector search using semantic embeddings."""

    def __init__(self, use_rerank: bool = False, validate_filters: bool = True):
        """
        Initialize dense vector search.

        Args:
            use_rerank: Whether to rerank results using a cross-encoder.
            validate_filters: Whether to validate filter keys against Pinecone metadata.
                Set to False to skip validation for performance.
        """
        self.manager = PineconeManager()
        self.manager.connect_index(
            name=os.getenv("PINECONE_INDEX_NAME"),
            host=os.getenv("PINECONE_HOST"),
        )
        self.use_rerank = use_rerank
        self.validate_filters = validate_filters

        # Reason: Cache metadata keys per namespace to avoid repeated lookups
        self._metadata_keys_cache: dict[str, set[str]] = {}

    def _get_valid_keys(self, namespace: str) -> set[str]:
        """Get valid metadata keys for a namespace, using cache if available."""
        if namespace not in self._metadata_keys_cache:
            self._metadata_keys_cache[namespace] = self.manager.get_metadata_keys(
                namespace=namespace
            )
        return self._metadata_keys_cache[namespace]

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
        # Reason: Fetch more results for reranking to improve quality
        retrieval_top_k = 25 if self.use_rerank else top_k

        # Reason: Validate filter keys if enabled and filters are provided
        valid_keys = None
        if self.validate_filters and filters:
            valid_keys = self._get_valid_keys(namespace)

        filter_dict = build_metadata_filter(valid_keys=valid_keys, **filters)

        embedding = embed_query(query)

        search_results = self.manager.query(
            vector=embedding.dense,
            top_k=retrieval_top_k,
            namespace=namespace,
            filter=filter_dict,
        )

        if self.use_rerank:
            return rerank_results(
                query=query,
                results=search_results,
                top_k=top_k,
            )

        return search_results


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
