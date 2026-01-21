"""Hybrid search combining dense (semantic) and sparse (BM25) vectors."""

import os
from typing import Optional

from dotenv import load_dotenv

from app.core.foundry.embeddings.pinecone_manager import PineconeManager
from app.core.foundry.embeddings.voyage_embeddings import embed_query
from app.core.foundry.models.vector import QueryResult
from app.core.foundry.retrieval.rerank import rerank as rerank_results
from app.core.foundry.retrieval.utils import build_metadata_filter

load_dotenv()


class HybridSearch:
    """Hybrid search combining dense and sparse vectors with alpha weighting."""

    def __init__(self, alpha: float = 0.5, use_rerank: bool = False):
        """Initialize hybrid search with a pre-fitted BM25 encoder."""

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

    def search(
        self,
        query: str,
        top_k: int = 5,
        namespace: str = "earnings_calls",
        ticker: Optional[str] = None,
        fiscal_quarter: Optional[str] = None,
        fiscal_year: Optional[int] = None,
    ) -> list[QueryResult]:
        """Execute a hybrid search combining semantic and keyword matching."""

        # Reason: Fetch more results for reranking to improve quality
        retrieval_top_k = 25 if self.use_rerank else top_k

        filters = build_metadata_filter(
            ticker=ticker,
            fiscal_quarter=fiscal_quarter,
            fiscal_year=fiscal_year,
        )

        embedding = embed_query(query, sparse_encoder=self.sparse_encoder)

        if embedding.sparse is None:
            raise RuntimeError("Sparse embedding not generated. Check encoder.")
        
        search_results = self.manager.hybrid_query(
            dense_vector=embedding.dense,
            sparse_vector=embedding.sparse,
            top_k=retrieval_top_k,
            namespace=namespace,
            filter=filters,
            alpha=self.alpha,
        )

        if self.use_rerank:
            return rerank_results(
                query=query,
                results=search_results,
                top_k=top_k,
            )

        return search_results


        



