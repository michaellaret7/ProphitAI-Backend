from typing import Literal
from pydantic import BaseModel, model_validator

class IngestionItem(BaseModel):
    """
    A single item to ingest into the RAG pipeline.
    
    Examples:
        # Raw text input (e.g., from API)
        IngestionItem(
            source_type="text",
            content="Operator: Good afternoon...",
            metadata={"doc_type": "earnings_call", "ticker": "AAPL", "fiscal_year": 2025}
        )
        
        # S3 document input
        IngestionItem(
            source_type="s3",
            s3_uri="s3://prophitai-documents/earnings/AAPL_Q4_2025.pdf",
            metadata={"doc_type": "earnings_call", "ticker": "AAPL", "fiscal_year": 2025}
        )
    """
    source_type: Literal["text", "s3"]
    content: str | None = None      # The actual text (required if source_type="text")
    s3_uri: str | None = None       # S3 path (required if source_type="s3")
    metadata: dict                  # MUST include "doc_type", should include ticker, fiscal_year, etc.

    @model_validator(mode="after")
    def validate_source(self):
        if self.source_type == "text" and not self.content:
            raise ValueError("content is required when source_type is 'text'")
        if self.source_type == "s3" and not self.s3_uri:
            raise ValueError("s3_uri is required when source_type is 's3'")
        return self

class BatchResult(BaseModel):
    """
    Result of processing one micro-batch.
    
    If success=True, all items in the batch were processed.
    If success=False, the entire batch failed (error contains details).
    """
    batch_index: int              # Which batch (0, 1, 2, ...)
    items_processed: int = 0      # How many items were in this batch
    chunks_created: int = 0       # Total chunks generated from all items
    vectors_upserted: int = 0     # How many vectors went into Pinecone
    success: bool                 # Did this batch complete without errors?
    error: str | None = None      # Error message if success=False

class IngestionError(BaseModel):
    """
    Describes why a specific item failed validation.
    
    Example:
        IngestionError(index=5, error="doc_type required in metadata")
    """
    index: int      # Which item in the input list (0-indexed)
    error: str      # Human-readable error message

class IngestionResult(BaseModel):
    """
    Final result returned by IngestionPipeline.run().
    
    Example output:
        IngestionResult(
            total_items=30,
            successful=28,
            failed=2,
            total_chunks=1450,
            total_vectors_upserted=1450,
            errors=[IngestionError(index=5, error="S3 file not found"), ...],
            batch_results=[BatchResult(...), BatchResult(...), ...]
        )
    """
    total_items: int                    # How many items were passed in
    successful: int                     # How many items succeeded
    failed: int                         # How many items failed
    total_chunks: int                   # Total chunks created across all items
    total_vectors_upserted: int         # Total vectors stored in Pinecone
    errors: list[IngestionError]        # Details on each failure
    batch_results: list[BatchResult]    # Per-batch breakdown