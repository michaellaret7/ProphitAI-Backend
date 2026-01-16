from pydantic import BaseModel, Field

class Document(BaseModel):
    """A document with text content and metadata."""

    content: str = Field(..., description="The text content of the document")
    metadata: dict = Field(default_factory=dict, description="Document metadata")
    source: str = Field(..., description="Source path or identifier")
