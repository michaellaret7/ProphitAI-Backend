"""Dense vector search using Voyage AI embeddings."""

import os
from typing import Optional

from dotenv import load_dotenv

from app.core.foundry.embeddings.pinecone_manager import PineconeManager
from app.core.foundry.embeddings.voyage_embeddings import embed_query
from app.core.foundry.models.vector import QueryResult
from app.core.foundry.retrieval.rerank import rerank as rerank_results
from app.core.foundry.retrieval.utils import build_metadata_filter

load_dotenv()


class VectorSearch:
    """Dense vector search using semantic embeddings."""
    def __init__(self, use_rerank: bool = False):
        self.manager = PineconeManager()
        self.manager.connect_index(
            name=os.getenv("PINECONE_INDEX_NAME"),
            host=os.getenv("PINECONE_HOST"),
        )
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
        """Execute a dense vector search."""
        # Reason: Fetch more results for reranking to improve quality
        retrieval_top_k = 25 if self.use_rerank else top_k

        filters = build_metadata_filter(
            ticker=ticker,
            fiscal_quarter=fiscal_quarter,
            fiscal_year=fiscal_year,
        )

        embedding = embed_query(query)

        search_results = self.manager.query(
            vector=embedding.dense,
            top_k=retrieval_top_k,
            namespace=namespace,
            filter=filters,
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
        print(result.metadata['chunk_id'])
        print(result.metadata['text'])
        print(result.score)
        print("--------------------------------")