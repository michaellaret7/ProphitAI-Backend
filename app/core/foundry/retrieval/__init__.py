"""
Retrieval module for semantic and hybrid search operations.

Provides search implementations for querying vector embeddings stored in Pinecone.
"""

from app.core.foundry.retrieval.base import BaseSearch
from app.core.foundry.retrieval.hybrid import HybridSearch
from app.core.foundry.retrieval.rerank import rerank
from app.core.foundry.retrieval.utils import build_metadata_filter
from app.core.foundry.retrieval.vector import VectorSearch

__all__ = [
    "BaseSearch",
    "VectorSearch",
    "HybridSearch",
    "rerank",
    "build_metadata_filter",
]
