"""
Chunk model for text chunking output.

Represents a segment of text with position and token information,
optionally including an embedding vector.
"""

from typing import Optional

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """A chunk of text extracted from a document."""

    text: str = Field(..., description="The text content of the chunk")
    start_index: int = Field(..., description="Starting character position in original text")
    end_index: int = Field(..., description="Ending character position in original text")
    token_count: int = Field(..., description="Number of tokens in the chunk")
    metadata: dict = Field(default_factory=dict, description="Additional chunk metadata")
    embedding: Optional[list[float]] = Field(default=None, description="Dense vector embedding from Voyage AI")
    sparse_embedding: Optional[dict] = Field(default=None, description="Sparse vector with 'indices' and 'values' keys")

    @property
    def char_count(self) -> int:
        """Return the character count of the chunk."""
        return len(self.text)

    @property
    def has_embedding(self) -> bool:
        """Check if this chunk has a dense embedding."""
        return self.embedding is not None

    @property
    def has_sparse_embedding(self) -> bool:
        """Check if this chunk has a sparse embedding."""
        return self.sparse_embedding is not None
