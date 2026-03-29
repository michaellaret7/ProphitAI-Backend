"""
Document ingestion submodule for RAG pipelines.

Provides a unified Ingestor for various document formats from S3 or local paths.
"""
from prophitai_foundry.ingestion.ingest import Ingestor
from prophitai_foundry.models.document import Document

__all__ = ["Ingestor", "Document"]
