"""Base class for search implementations with shared functionality."""

import os
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from dotenv import load_dotenv

from prophitai_foundry.embeddings.pinecone_manager import PineconeManager
from prophitai_foundry.models.vector import QueryResult
from prophitai_foundry.retrieval.postprocess.rerank import rerank as rerank_results
from prophitai_foundry.retrieval.utils import build_metadata_filter

load_dotenv()


class BaseSearch(ABC):
    """Abstract base class for search implementations.

    Provides shared functionality for connecting to Pinecone, caching metadata keys,
    preparing search parameters, and finalizing results with optional reranking.
    """

    def __init__(
        self,
        use_rerank: bool = False,
        validate_filters: bool = True,
        enhanced: bool = False,
    ):
        """
        Initialize base search with common configuration.

        Args:
            use_rerank: Whether to rerank results using a cross-encoder.
            validate_filters: Whether to validate filter keys against Pinecone metadata.
                Set to False to skip validation for performance.
            enhanced: Whether to use query decomposition for complex queries.
        """
        self.manager = PineconeManager()
        self.manager.connect_index(
            name=os.getenv("PINECONE_INDEX_NAME"),
            host=os.getenv("PINECONE_HOST"),
        )
        self.use_rerank = use_rerank
        self.validate_filters = validate_filters
        self.enhanced = enhanced

        # Reason: Cache metadata keys per namespace to avoid repeated lookups
        self._metadata_keys_cache: dict[str, set[str]] = {}

    def _get_valid_keys(self, namespace: str) -> set[str]:
        """Get valid metadata keys for a namespace, using cache if available."""
        if namespace not in self._metadata_keys_cache:
            self._metadata_keys_cache[namespace] = self.manager.get_metadata_keys(
                namespace=namespace
            )
        return self._metadata_keys_cache[namespace]

    def _prepare_search(
        self,
        top_k: int,
        namespace: str,
        **filters: Any,
    ) -> tuple[int, dict | None]:
        """
        Prepare common search parameters.

        Args:
            top_k: Number of results requested.
            namespace: Pinecone namespace to search in.
            **filters: Metadata filters to apply.

        Returns:
            Tuple of (retrieval_top_k, filter_dict) where retrieval_top_k is
            increased when reranking is enabled.
        """
        # Reason: Fetch more results for reranking to improve quality
        retrieval_top_k = 25 if self.use_rerank else top_k

        # Reason: Validate filter keys if enabled and filters are provided
        valid_keys = None
        if self.validate_filters and filters:
            valid_keys = self._get_valid_keys(namespace)

        filter_dict = build_metadata_filter(valid_keys=valid_keys, **filters)

        return retrieval_top_k, filter_dict

    def _finalize_results(
        self,
        query: str,
        results: list[QueryResult],
        top_k: int,
    ) -> list[QueryResult]:
        """
        Apply reranking if enabled, otherwise return results as-is.

        Args:
            query: The original search query.
            results: Search results from Pinecone.
            top_k: Number of results to return.

        Returns:
            Reranked results if use_rerank is True, otherwise original results.
        """
        if self.use_rerank:
            return rerank_results(
                query=query,
                results=results,
                top_k=top_k,
            )
        return results

    def _run_enhanced_search(
        self,
        query: str,
        top_k: int,
        namespace: str,
        **filters: Any,
    ) -> list[QueryResult]:
        """
        Execute enhanced search with query decomposition and parallel execution.

        Args:
            query: The original search query.
            top_k: Number of results to return after final reranking.
            namespace: Pinecone namespace to search in.
            **filters: Metadata filters passed to each sub-query search.

        Returns:
            List of QueryResult objects reranked against the original query.
        """
        # Reason: Lazy import to avoid circular dependency
        from prophitai_foundry.retrieval.query_enhancement.decomposer import (
            decompose_query,
        )

        sub_queries = decompose_query(query)
        max_workers = len(sub_queries.sub_queries)

        all_results: list[QueryResult] = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self._search_internal,
                    sq.sub_query,
                    top_k,
                    namespace,
                    filters,
                ): sq
                for sq in sub_queries.sub_queries
            }

            for future in as_completed(futures):
                results = future.result()
                all_results.extend(results)

        # Dedupe by ID
        seen_ids: set[str] = set()
        deduped: list[QueryResult] = []
        for r in all_results:
            if r.id not in seen_ids:
                seen_ids.add(r.id)
                deduped.append(r)

        # Rerank merged results against original query
        return rerank_results(query=query, results=deduped, top_k=top_k)

    @abstractmethod
    def _search_internal(
        self,
        query: str,
        top_k: int,
        namespace: str,
        filters: dict[str, Any],
    ) -> list[QueryResult]:
        """
        Internal search method for enhanced search parallelization.

        Subclasses must implement this to execute the actual search logic.
        """
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = 5,
        namespace: str = "earnings_calls",
        **filters: Any,
    ) -> list[QueryResult]:
        """
        Execute a search query.

        Args:
            query: The search query text.
            top_k: Number of results to return.
            namespace: Pinecone namespace to search in.
            **filters: Dynamic metadata filters.

        Returns:
            List of QueryResult objects sorted by relevance.
        """
        pass
