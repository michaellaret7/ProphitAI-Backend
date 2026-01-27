"""
Retrieval module for semantic and hybrid search operations.

Provides search implementations for querying vector embeddings stored in Pinecone.
"""

from app.core.foundry.retrieval.postprocess.rerank import rerank
from app.core.foundry.retrieval.search.base import BaseSearch
from app.core.foundry.retrieval.search.hybrid import HybridSearch
from app.core.foundry.retrieval.search.vector import VectorSearch
from app.core.foundry.retrieval.utils import build_metadata_filter

__all__ = [
    "BaseSearch",
    "VectorSearch",
    "HybridSearch",
    "rerank",
    "build_metadata_filter",
]
