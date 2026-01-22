"""Hybrid search combining dense (semantic) and sparse (BM25) vectors."""

import os
from typing import Any

from dotenv import load_dotenv

from app.core.foundry.embeddings.pinecone_manager import PineconeManager
from app.core.foundry.embeddings.voyage_embeddings import embed_query
from app.core.foundry.models.vector import QueryResult
from app.core.foundry.retrieval.rerank import rerank as rerank_results
from app.core.foundry.retrieval.utils import build_metadata_filter

load_dotenv()


class HybridSearch:
    """Hybrid search combining dense and sparse vectors with alpha weighting."""

    def __init__(
        self,
        alpha: float = 0.5,
        use_rerank: bool = False,
        validate_filters: bool = True,
    ):
        """
        Initialize hybrid search with a pre-fitted BM25 encoder.

        Args:
            alpha: Weighting factor between dense and sparse vectors (0-1).
            use_rerank: Whether to rerank results using a cross-encoder.
            validate_filters: Whether to validate filter keys against Pinecone metadata.
                Set to False to skip validation for performance.
        """

        self.alpha = alpha
        self.manager = PineconeManager()
        self.manager.connect_index(
            name=os.getenv("PINECONE_INDEX_NAME"),
            host=os.getenv("PINECONE_HOST"),
        )

        # Reason: Lazy import to avoid heavy imports when only using VectorSearch
        from app.core.foundry.embeddings.sparse_encoder import SparseEncoder

        self.sparse_encoder = SparseEncoder()
        self.sparse_encoder.load()

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
        # Reason: Fetch more results for reranking to improve quality
        retrieval_top_k = 25 if self.use_rerank else top_k

        # Reason: Validate filter keys if enabled and filters are provided
        valid_keys = None
        if self.validate_filters and filters:
            valid_keys = self._get_valid_keys(namespace)

        filter_dict = build_metadata_filter(valid_keys=valid_keys, **filters)

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

        if self.use_rerank:
            return rerank_results(
                query=query,
                results=search_results,
                top_k=top_k,
            )

        return search_results



