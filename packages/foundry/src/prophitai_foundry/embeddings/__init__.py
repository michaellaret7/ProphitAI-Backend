"""Embeddings module for RAG pipelines."""

from prophitai_foundry.embeddings.pinecone_manager import PineconeManager
from prophitai_foundry.embeddings.voyage_embeddings import embed_chunks
from prophitai_foundry.models.vector import IndexStats, QueryResult, VectorRecord

__all__ = [
    "embed_chunks",
    "IndexStats",
    "PineconeManager",
    "QueryResult",
    "VectorRecord",
]
