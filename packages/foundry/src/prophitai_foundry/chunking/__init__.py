"""
Text chunking module for RAG pipelines.

Provides chunkers for splitting documents into retrievable segments.

Available chunkers:
- SemanticChunker: Splits text based on embedding similarity for semantic coherence
- RecursiveChunker: Splits text hierarchically using configurable delimiter rules
"""

from prophitai_foundry.chunking.recursive import RecursiveChunker
from prophitai_foundry.chunking.semantic import SemanticChunker

__all__ = ["RecursiveChunker", "SemanticChunker"]
