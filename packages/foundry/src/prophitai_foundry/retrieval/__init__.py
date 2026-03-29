"""
Retrieval module for semantic and hybrid search operations.

Provides search implementations for querying vector embeddings stored in Pinecone.
"""

from prophitai_foundry.retrieval.postprocess.rerank import rerank
from prophitai_foundry.retrieval.search.base import BaseSearch
from prophitai_foundry.retrieval.search.hybrid import HybridSearch
from prophitai_foundry.retrieval.search.vector import VectorSearch
from prophitai_foundry.retrieval.utils import build_metadata_filter

__all__ = [
    "BaseSearch",
    "VectorSearch",
    "HybridSearch",
    "rerank",
    "build_metadata_filter",
]
