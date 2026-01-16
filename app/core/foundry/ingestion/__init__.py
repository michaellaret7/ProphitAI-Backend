"""
Document ingestion submodule for RAG pipelines.

Provides loaders for various document formats including PDF, Excel, etc.
"""
from app.core.foundry.ingestion.pdf_loader import PDFIngestor

__all__ = ["PDFIngestor"]
