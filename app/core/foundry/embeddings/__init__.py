"""Embeddings module for RAG pipelines."""

from app.core.foundry.embeddings.pinecone_manager import PineconeManager
from app.core.foundry.embeddings.voyage_embeddings import embed_chunks
from app.core.foundry.models.vector import IndexStats, QueryResult, VectorRecord
from app.core.foundry.embeddings.sparse_encoder import SparseEncoder

__all__ = [
    "embed_chunks",
    "IndexStats",
    "PineconeManager",
    "QueryResult",
    "VectorRecord",
    "SparseEncoder",
]
