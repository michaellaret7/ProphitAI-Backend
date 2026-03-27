"""
Foundry models submodule.

Provides data models for document ingestion and processing.
"""

from prophitai_foundry.models.chunk import Chunk
from prophitai_foundry.models.document import Document
from prophitai_foundry.models.metadata import EarningsCallMetadata
from prophitai_foundry.models.vector import IndexStats, QueryResult, VectorRecord
from prophitai_foundry.models.pipeline import IngestionItem, BatchResult, IngestionResult

__all__ = [
    "Chunk",
    "Document",
    "EarningsCallMetadata",
    "IndexStats",
    "QueryResult",
    "VectorRecord",
    "IngestionItem",
    "BatchResult",
    "IngestionResult",
]
