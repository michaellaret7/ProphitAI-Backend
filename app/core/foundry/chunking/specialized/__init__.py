"""
Specialized chunkers for domain-specific document types.

These chunkers exploit the predictable structure of specific document formats
to create more semantically coherent chunks than generic chunkers.

Available:
- chunk_earnings_call: LLM-based chunker for earnings call transcripts
"""

from app.core.foundry.chunking.specialized.earnings_calls import chunk_earnings_call

__all__ = ["chunk_earnings_call"]
