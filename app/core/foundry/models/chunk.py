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
    embedding: Optional[list[float]] = Field(default=None, description="Vector embedding from Voyage AI")

    @property
    def char_count(self) -> int:
        """Return the character count of the chunk."""
        return len(self.text)

    @property
    def has_embedding(self) -> bool:
        """Check if this chunk has been embedded."""
        return self.embedding is not None
