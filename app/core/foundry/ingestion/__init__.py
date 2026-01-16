"""
Document ingestion submodule for RAG pipelines.

Provides loaders for various document formats including PDF, Excel, and plain text.
"""
from app.core.foundry.ingestion.pdf_loader import PDFIngestor
from app.core.foundry.ingestion.excel_loader import ExcelIngestor
from app.core.foundry.ingestion.docx_loader import DocsIngestor
from app.core.foundry.ingestion.text_loader import TextIngestor
from app.core.foundry.models.ingestion_output import Document

__all__ = ["PDFIngestor", "ExcelIngestor", "DocsIngestor", "TextIngestor", "Document"]
