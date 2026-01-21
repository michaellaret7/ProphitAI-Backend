"""Dense vector search using Voyage AI embeddings."""

import os
from typing import Optional

from dotenv import load_dotenv

from app.core.foundry.embeddings.pinecone_manager import PineconeManager
from app.core.foundry.embeddings.voyage_embeddings import embed_query
from app.core.foundry.models.vector import QueryResult
from app.core.foundry.retrieval.utils import build_metadata_filter

load_dotenv()


class VectorSearch:
    """Dense vector search using semantic embeddings."""

    def __init__(self):
        index_name = os.getenv("PINECONE_INDEX_NAME")
        if not index_name:
            raise ValueError("PINECONE_INDEX_NAME environment variable not set")

        self.manager = PineconeManager()
        self.manager.connect_index(
            name=index_name,
            host=os.getenv("PINECONE_HOST"),
        )

    def search(
        self,
        query: str,
        top_k: int = 10,
        namespace: str = "earnings_calls",
        ticker: Optional[str] = None,
        fiscal_quarter: Optional[str] = None,
        fiscal_year: Optional[int] = None,
    ) -> list[QueryResult]:
        """Execute a dense vector search."""
        filters = build_metadata_filter(
            ticker=ticker,
            fiscal_quarter=fiscal_quarter,
            fiscal_year=fiscal_year,
        )

        embedding = embed_query(query)

        return self.manager.query(
            vector=embedding.dense,
            top_k=top_k,
            namespace=namespace,
            filter=filters,
        )

