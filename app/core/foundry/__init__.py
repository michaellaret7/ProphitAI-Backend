"""
Foundry module for RAG data ingestion and processing.

This module provides document ingestion capabilities for building
retrieval-augmented generation (RAG) pipelines.
"""
from app.core.foundry.ingestion import Ingestor, Document

__all__ = ["Ingestor", "Document"]
