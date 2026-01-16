"""
Foundry module for RAG data ingestion and processing.

This module provides document ingestion capabilities for building
retrieval-augmented generation (RAG) pipelines.
"""
from app.core.foundry.ingestion import PDFIngestor, ExcelIngestor, DocsIngestor, TextIngestor, Document

__all__ = ["PDFIngestor", "ExcelIngestor", "DocsIngestor", "TextIngestor", "Document"]
