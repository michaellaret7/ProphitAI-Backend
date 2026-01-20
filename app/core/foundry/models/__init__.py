"""
Foundry models submodule.

Provides data models for document ingestion and processing.
"""

from app.core.foundry.models.chunk import Chunk
from app.core.foundry.models.document import Document
from app.core.foundry.models.metadata import EarningsCallMetadata
from app.core.foundry.models.vector import IndexStats, QueryResult, VectorRecord

__all__ = [
    "Chunk",
    "Document",
    "EarningsCallMetadata",
    "IndexStats",
    "QueryResult",
    "VectorRecord",
]
