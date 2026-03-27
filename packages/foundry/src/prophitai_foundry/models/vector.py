"""
Vector models for Pinecone operations.

Pydantic models for vector records, query results, and index statistics.
"""

from typing import Optional

from pydantic import BaseModel, Field


class VectorRecord(BaseModel):
    """A vector record for Pinecone operations."""

    id: str = Field(..., description="Unique vector ID")
    values: list[float] = Field(..., description="Dense vector values")
    metadata: dict = Field(default_factory=dict, description="Vector metadata")
    sparse_values: Optional[dict] = Field(default=None, description="Sparse vector for hybrid search")


class QueryResult(BaseModel):
    """A single query result from Pinecone."""

    id: str = Field(..., description="Vector ID")
    score: float = Field(..., description="Similarity score")
    values: Optional[list[float]] = Field(default=None, description="Vector values if requested")
    metadata: dict = Field(default_factory=dict, description="Vector metadata")


class IndexStats(BaseModel):
    """Statistics for a Pinecone index."""

    dimension: int = Field(..., description="Vector dimension")
    total_vector_count: int = Field(..., description="Total vectors in index")
    namespaces: dict[str, int] = Field(default_factory=dict, description="Vector count per namespace")
