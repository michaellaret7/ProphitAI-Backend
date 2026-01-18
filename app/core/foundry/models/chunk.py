"""
Chunk model for text chunking output.

Represents a segment of text with position and token information.
"""

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """A chunk of text extracted from a document."""

    text: str = Field(..., description="The text content of the chunk")
    start_index: int = Field(..., description="Starting character position in original text")
    end_index: int = Field(..., description="Ending character position in original text")
    token_count: int = Field(..., description="Number of tokens in the chunk")
    metadata: dict = Field(default_factory=dict, description="Additional chunk metadata")

    @property
    def char_count(self) -> int:
        """Return the character count of the chunk."""
        return len(self.text)
