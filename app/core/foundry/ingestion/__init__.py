"""
Document ingestion submodule for RAG pipelines.

Provides a unified Ingestor for various document formats from S3 or local paths.
"""
from app.core.foundry.ingestion.ingest import Ingestor
from app.core.foundry.models.ingestion_output import Document

__all__ = ["Ingestor", "Document"]
